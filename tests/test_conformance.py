from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance"
MANIFEST = CONFORMANCE / "ECV_CONFORMANCE_V1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_conformance_manifest_replays_exact_cli_bytes() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
    assert set(manifest) == {"cases", "format", "specs"}
    assert manifest["format"] == "ECV_CONFORMANCE_V1"
    assert manifest["specs"] == ["ECV/1", "ECV/2"]
    assert len(manifest["cases"]) >= 9

    seen_ids: set[str] = set()
    seen_verdicts: set[str] = set()
    for case in manifest["cases"]:
        assert set(case) == {
            "expected_exit",
            "expected_result",
            "expected_result_sha256",
            "expected_verdict",
            "id",
            "input",
            "input_sha256",
        }
        assert case["id"] not in seen_ids
        seen_ids.add(case["id"])
        input_path = CONFORMANCE / case["input"]
        expected_path = CONFORMANCE / case["expected_result"]
        assert _sha256(input_path) == case["input_sha256"]
        assert _sha256(expected_path) == case["expected_result_sha256"]
        expected_bytes = expected_path.read_bytes()
        assert expected_bytes.endswith(b"\n") and expected_bytes.count(b"\n") == 1
        expected = json.loads(expected_bytes)
        assert expected["verdict"] == case["expected_verdict"]
        seen_verdicts.add(case["expected_verdict"])

        completed = subprocess.run(
            [sys.executable, "-m", "exact_claim_verifier.cli", "verify", str(input_path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        assert completed.stderr == b""
        assert completed.returncode == case["expected_exit"]
        assert completed.stdout == expected_bytes

    assert seen_verdicts == {
        "EXACTLY_VERIFIED_IN_DOMAIN",
        "REFUTED_IN_DOMAIN",
        "ABSTAIN_OUT_OF_DOMAIN",
        "RESOURCE_LIMIT",
        "INVALID_INPUT",
    }
