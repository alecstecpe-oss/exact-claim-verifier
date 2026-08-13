from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_conformance.py"


def test_external_conformance_runner_checks_all_vectors() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(ROOT / "conformance"),
            "--",
            sys.executable,
            "-m",
            "exact_claim_verifier.cli",
            "verify",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    summary = json.loads(completed.stdout)
    assert summary == {
        "cases": 9,
        "command": [sys.executable, "-m", "exact_claim_verifier.cli", "verify"],
        "format": "ECV_CONFORMANCE_RUN_V1",
        "status": "PASS",
    }
