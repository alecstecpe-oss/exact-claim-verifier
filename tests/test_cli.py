from __future__ import annotations

import json
from pathlib import Path

from exact_claim_verifier.cli import main


def test_cli_reports_missing_argument_as_json(capsys) -> None:
    exit_code = main(["verify"])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "COMMAND_INPUT_ERROR"
    assert captured.err == ""


def test_cli_reports_unknown_command_as_json(capsys) -> None:
    exit_code = main(["não-🔒"])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "COMMAND_INPUT_ERROR"
    assert captured.out.isascii()
    assert captured.err == ""


def test_cli_verifies_document_and_emits_canonical_json(tmp_path, capsys) -> None:
    claim_path = tmp_path / "claim.json"
    claim_path.write_text(
        json.dumps(
            {
                "spec": "ECV/1",
                "domain": "modular-arithmetic",
                "claim": {
                    "kind": "crt-solution",
                    "congruences": [
                        {"residue": "2", "modulus": "3"},
                        {"residue": "3", "modulus": "5"},
                    ],
                    "solution": "8",
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["verify", str(claim_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert json.loads(output)["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
    assert output == json.dumps(json.loads(output), sort_keys=True, separators=(",", ":")) + "\n"


def test_cli_rejects_duplicate_json_key(tmp_path, capsys) -> None:
    claim_path = tmp_path / "duplicate.json"
    claim_path.write_text(
        '{"spec":"ECV/1","domain":"x","domain":"y","claim":{"kind":"z"}}',
        encoding="utf-8",
    )

    exit_code = main(["verify", str(claim_path)])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "DUPLICATE_JSON_KEY"


def test_cli_rejects_nonstandard_nan_constant(tmp_path, capsys) -> None:
    claim_path = tmp_path / "nan.json"
    claim_path.write_text(
        '{"spec":"ECV/1","domain":"x","claim":{"kind":"z","value":NaN}}',
        encoding="utf-8",
    )

    exit_code = main(["verify", str(claim_path)])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "INVALID_JSON_CONSTANT"


def test_cli_rejects_directory_path_without_traceback(tmp_path, capsys) -> None:
    exit_code = main(["verify", str(tmp_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "NOT_A_REGULAR_FILE"
    assert captured.err == ""


def test_cli_reports_missing_file_distinctly(tmp_path, capsys) -> None:
    exit_code = main(["verify", str(tmp_path / "missing.json")])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "FILE_NOT_FOUND"
    assert captured.err == ""


def test_cli_rejects_excessive_json_nesting_without_traceback(tmp_path, capsys) -> None:
    claim_path = tmp_path / "deep.json"
    claim_path.write_bytes((b"[" * 2000) + b"0" + (b"]" * 2000))

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "JSON_NESTING_LIMIT"
    assert captured.err == ""


def test_cli_does_not_count_brackets_inside_json_strings(tmp_path, capsys) -> None:
    claim_path = tmp_path / "brackets-in-string.json"
    claim_path.write_text(
        json.dumps(
            {
                "spec": "ECV/1",
                "domain": "future-domain",
                "claim": {"kind": "future-claim", "text": "[" * 1000},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 1
    assert result["verdict"] == "ABSTAIN_OUT_OF_DOMAIN"
    assert captured.err == ""


def test_cli_rejects_json_number_where_domain_requires_string(tmp_path, capsys) -> None:
    claim_path = tmp_path / "numeric-domain.json"
    claim_path.write_text(
        '{"spec":"ECV/1","domain":1.5,"claim":{"kind":"future-claim"}}',
        encoding="utf-8",
    )

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "DOMAIN_NOT_STRING"
    assert captured.err == ""


def test_cli_escapes_unpaired_surrogate_in_result(tmp_path, capsys) -> None:
    claim_path = tmp_path / "surrogate.json"
    claim_path.write_text(
        '{"spec":"ECV/1","domain":"\\ud800","claim":{"kind":"future-claim"}}',
        encoding="ascii",
    )

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 1
    assert result["verdict"] == "ABSTAIN_OUT_OF_DOMAIN"
    assert "\\ud800" in captured.out
    assert captured.err == ""


def test_cli_applies_byte_limit_to_content_read(tmp_path, capsys) -> None:
    claim_path = tmp_path / "oversized.json"
    claim_path.write_bytes(b" " * 1_048_577)

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 1
    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "INPUT_BYTE_LIMIT"
    assert captured.err == ""


def test_cli_rejects_invalid_utf8_and_malformed_json(tmp_path, capsys) -> None:
    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")

    first_exit = main(["verify", str(invalid_utf8)])
    first = json.loads(capsys.readouterr().out)
    second_exit = main(["verify", str(malformed)])
    second = json.loads(capsys.readouterr().out)

    assert (first_exit, first["errors"][0]["code"]) == (2, "INVALID_UTF8")
    assert (second_exit, second["errors"][0]["code"]) == (2, "INVALID_JSON")


def test_cli_rejects_oversized_json_number_without_traceback(tmp_path, capsys) -> None:
    claim_path = tmp_path / "huge-number.json"
    claim_path.write_text(
        '{"spec":"ECV/1","domain":"integer-polynomial-identity",'
        '"claim":{"kind":"identity","variables":["x"],'
        '"left":{"op":"pow","arg":{"op":"var","name":"x"},"exponent":'
        + ("9" * 5000)
        + '},"right":{"op":"const","value":"0"}}}',
        encoding="utf-8",
    )

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "INVALID_JSON_NUMBER"
    assert captured.err == ""


def test_cli_converts_file_read_error_to_json(tmp_path, capsys, monkeypatch) -> None:
    claim_path = tmp_path / "claim.json"
    claim_path.write_text("{}", encoding="utf-8")
    original_open = Path.open

    def denied(path: Path, *args, **kwargs):
        if path == claim_path:
            raise OSError("simulated read failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)

    exit_code = main(["verify", str(claim_path)])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 2
    assert result["errors"][0]["code"] == "FILE_READ_ERROR"
    assert captured.err == ""
