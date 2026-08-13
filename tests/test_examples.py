from __future__ import annotations

import json
from pathlib import Path

import pytest

from exact_claim_verifier import verify_document

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("name", "verdict"),
    [
        ("linear-valid.json", "EXACTLY_VERIFIED_IN_DOMAIN"),
        ("linear-program-valid.json", "EXACTLY_VERIFIED_IN_DOMAIN"),
        ("linear-program-refuted.json", "REFUTED_IN_DOMAIN"),
        ("polynomial-valid.json", "EXACTLY_VERIFIED_IN_DOMAIN"),
        ("modular-valid.json", "EXACTLY_VERIFIED_IN_DOMAIN"),
        ("polynomial-refuted.json", "REFUTED_IN_DOMAIN"),
        ("modular-abstain.json", "ABSTAIN_OUT_OF_DOMAIN"),
        ("linear-invalid.json", "INVALID_INPUT"),
    ],
)
def test_committed_example(name: str, verdict: str) -> None:
    document = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    result = verify_document(document)

    assert result["verdict"] == verdict
