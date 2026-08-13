from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

EXIT_BY_VERDICT = {
    "EXACTLY_VERIFIED_IN_DOMAIN": 0,
    "REFUTED_IN_DOMAIN": 1,
    "ABSTAIN_OUT_OF_DOMAIN": 1,
    "RESOURCE_LIMIT": 1,
    "INVALID_INPUT": 2,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_corpus(root: Path, command: list[str]) -> Path:
    inputs = root / "inputs"
    expected = root / "expected"
    expected.mkdir(parents=True, exist_ok=True)
    cases = []
    for input_path in sorted(inputs.glob("*.json")):
        completed = subprocess.run(
            [*command, str(input_path)],
            check=False,
            capture_output=True,
        )
        if completed.stderr:
            raise ValueError(f"checker emitted stderr for {input_path.name}")
        result = json.loads(completed.stdout)
        verdict = result["verdict"]
        if completed.returncode != EXIT_BY_VERDICT[verdict]:
            raise ValueError(f"unexpected exit for {input_path.name}")
        canonical = (
            json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")
        if completed.stdout != canonical:
            raise ValueError(f"checker output is not canonical for {input_path.name}")
        expected_path = expected / input_path.name
        expected_path.write_bytes(canonical)
        cases.append(
            {
                "expected_exit": completed.returncode,
                "expected_result": expected_path.relative_to(root).as_posix(),
                "expected_result_sha256": _sha256(expected_path),
                "expected_verdict": verdict,
                "id": input_path.stem,
                "input": input_path.relative_to(root).as_posix(),
                "input_sha256": _sha256(input_path),
            }
        )
    manifest = root / "ECV_CONFORMANCE_V1.json"
    manifest.write_text(
        json.dumps(
            {"cases": cases, "format": "ECV_CONFORMANCE_V1", "specs": ["ECV/1", "ECV/2"]},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="ascii",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze canonical ECV conformance vectors.")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", nargs="+")
    arguments = parser.parse_args()
    print(build_corpus(arguments.root, arguments.command))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
