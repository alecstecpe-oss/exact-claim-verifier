from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_conformance(root: Path, command: list[str]) -> dict[str, object]:
    manifest = json.loads((root / "ECV_CONFORMANCE_V1.json").read_text(encoding="ascii"))
    if manifest.get("format") != "ECV_CONFORMANCE_V1" or not isinstance(
        manifest.get("cases"), list
    ):
        raise ValueError("invalid ECV conformance manifest")
    for case in manifest["cases"]:
        input_path = root / case["input"]
        expected_path = root / case["expected_result"]
        if _sha256(input_path) != case["input_sha256"]:
            raise ValueError(f"input hash mismatch: {case['id']}")
        if _sha256(expected_path) != case["expected_result_sha256"]:
            raise ValueError(f"expected-result hash mismatch: {case['id']}")
        completed = subprocess.run(
            [*command, str(input_path)],
            check=False,
            capture_output=True,
        )
        if completed.stderr:
            raise ValueError(f"candidate emitted stderr: {case['id']}")
        if completed.returncode != case["expected_exit"]:
            raise ValueError(f"exit mismatch: {case['id']}")
        if completed.stdout != expected_path.read_bytes():
            raise ValueError(f"result bytes mismatch: {case['id']}")
    return {
        "cases": len(manifest["cases"]),
        "command": command,
        "format": "ECV_CONFORMANCE_RUN_V1",
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the byte-exact ECV conformance corpus.")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    command = arguments.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a candidate command is required after --")
    try:
        result = run_conformance(arguments.root, command)
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {
                    "format": "ECV_CONFORMANCE_RUN_V1",
                    "status": "FAIL",
                    "error": str(error),
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
