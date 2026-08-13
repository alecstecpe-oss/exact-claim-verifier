from __future__ import annotations

import random
from typing import Any

from exact_claim_verifier import verify_document

_ALLOWED_VERDICTS = {
    "EXACTLY_VERIFIED_IN_DOMAIN",
    "REFUTED_IN_DOMAIN",
    "ABSTAIN_OUT_OF_DOMAIN",
    "RESOURCE_LIMIT",
    "INVALID_INPUT",
}


def _generator(seed: int = 20260813) -> Any:
    rng = random.Random(seed)
    scalars: list[Any] = [
        None,
        True,
        False,
        0,
        1,
        -1,
        0.0,
        1.5,
        "",
        "0",
        "x",
        "ECV/1",
    ]
    keys = [
        "spec",
        "domain",
        "claim",
        "kind",
        "matrix",
        "rhs",
        "solution",
        "variables",
        "left",
        "right",
        "op",
        "args",
        "arg",
        "exponent",
        "congruences",
        "residue",
        "modulus",
        "value",
    ]

    def generate(depth: int = 0) -> Any:
        if depth >= 4 or rng.random() < 0.42:
            return rng.choice(scalars)
        if rng.random() < 0.45:
            return [generate(depth + 1) for _ in range(rng.randrange(5))]
        result: dict[str, Any] = {}
        for _ in range(rng.randrange(6)):
            result[rng.choice(keys)] = generate(depth + 1)
        return result

    return generate


def test_5000_small_json_values_never_escape_the_result_contract() -> None:
    generate = _generator()
    for _ in range(5_000):
        result = verify_document(generate())
        assert set(result) == {
            "format",
            "spec",
            "domain",
            "claim_kind",
            "verdict",
            "derived",
            "errors",
        }
        assert result["format"] == "ECV_RESULT_V1"
        assert result["verdict"] in _ALLOWED_VERDICTS
        assert isinstance(result["derived"], dict)
        assert isinstance(result["errors"], list)
