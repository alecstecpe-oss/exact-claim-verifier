from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__, verify_document

_MAX_INPUT_BYTES = 1_048_576
_MAX_JSON_NESTING = 256
_MAX_JSON_INTEGER_DIGITS = 640


class _CommandInputError(ValueError):
    pass


class _MachineReadableArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CommandInputError(message)


class _DuplicateKey(ValueError):
    pass


class _InvalidJsonConstant(ValueError):
    pass


class _InvalidJsonNumber(ValueError):
    pass


class _JsonNestingLimit(ValueError):
    pass


class _JsonFloatToken:
    __slots__ = ("raw",)

    def __init__(self, raw: str) -> None:
        self.raw = raw


class _NotRegularFile(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise _InvalidJsonConstant(value)


def _parse_json_integer(value: str) -> int:
    if len(value.removeprefix("-")) > _MAX_JSON_INTEGER_DIGITS:
        raise _InvalidJsonNumber(f"integer token exceeds {_MAX_JSON_INTEGER_DIGITS} digits")
    return int(value)


def _parse_json_float(value: str) -> _JsonFloatToken:
    if len(value) > 1_024:
        raise _InvalidJsonNumber("number token exceeds 1024 characters")
    return _JsonFloatToken(value)


def _check_json_nesting(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > _MAX_JSON_NESTING:
                raise _JsonNestingLimit
        elif character in "]}":
            depth -= 1


def _emit(result: dict[str, Any]) -> None:
    encoded = (
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        + b"\n"
    )
    output = getattr(sys.stdout, "buffer", None)
    if output is None:
        sys.stdout.write(encoded.decode("ascii"))
    else:
        output.write(encoded)
        output.flush()


def _invalid_result(code: str, path: str, message: str) -> dict[str, Any]:
    return {
        "format": "ECV_RESULT_V1",
        "spec": None,
        "domain": None,
        "claim_kind": None,
        "verdict": "INVALID_INPUT",
        "derived": {},
        "errors": [{"code": code, "path": path, "message": message}],
    }


def _read_document(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise _NotRegularFile(str(path))
    with path.open("rb") as handle:
        raw = handle.read(_MAX_INPUT_BYTES + 1)
    if len(raw) > _MAX_INPUT_BYTES:
        raise ValueError("INPUT_BYTE_LIMIT")
    text = raw.decode("utf-8")
    _check_json_nesting(text)
    document = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_json_constant,
        parse_int=_parse_json_integer,
        parse_float=_parse_json_float,
    )
    if not isinstance(document, dict):
        return document
    return document


def _parser() -> _MachineReadableArgumentParser:
    parser = _MachineReadableArgumentParser(
        prog="ecv",
        description="Verify structured exact claims in declared mathematical domains.",
    )
    parser.add_argument("--version", action="version", version=f"ecv {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="verify one ECV/1 JSON document")
    verify.add_argument("document", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
    except _CommandInputError as error:
        result = _invalid_result(
            "COMMAND_INPUT_ERROR",
            "$",
            f"invalid command arguments: {error}",
        )
        _emit(result)
        return 2
    try:
        document = _read_document(arguments.document)
    except FileNotFoundError:
        result = _invalid_result("FILE_NOT_FOUND", "$", "input file does not exist")
    except _NotRegularFile:
        result = _invalid_result("NOT_A_REGULAR_FILE", "$", "input path must name a regular file")
    except UnicodeDecodeError:
        result = _invalid_result("INVALID_UTF8", "$", "input must be UTF-8")
    except _DuplicateKey as error:
        result = _invalid_result("DUPLICATE_JSON_KEY", "$", f"duplicate JSON object key: {error}")
    except _InvalidJsonConstant as error:
        result = _invalid_result(
            "INVALID_JSON_CONSTANT",
            "$",
            f"nonstandard JSON constant is forbidden: {error}",
        )
    except _InvalidJsonNumber as error:
        result = _invalid_result("INVALID_JSON_NUMBER", "$", str(error))
    except _JsonNestingLimit:
        result = _invalid_result(
            "JSON_NESTING_LIMIT",
            "$",
            f"JSON nesting is limited to {_MAX_JSON_NESTING}",
        )
    except json.JSONDecodeError:
        result = _invalid_result("INVALID_JSON", "$", "input must be strict JSON")
    except RecursionError:
        result = _invalid_result(
            "JSON_NESTING_LIMIT",
            "$",
            f"JSON nesting is limited to {_MAX_JSON_NESTING}",
        )
    except ValueError as error:
        if str(error) != "INPUT_BYTE_LIMIT":
            raise
        result = {
            **_invalid_result(
                "INPUT_BYTE_LIMIT", "$", f"input is limited to {_MAX_INPUT_BYTES} bytes"
            ),
            "verdict": "RESOURCE_LIMIT",
        }
    except OSError:
        result = _invalid_result("FILE_READ_ERROR", "$", "input file could not be read")
    else:
        result = verify_document(document)
    _emit(result)
    if result["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN":
        return 0
    if result["verdict"] == "INVALID_INPUT":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
