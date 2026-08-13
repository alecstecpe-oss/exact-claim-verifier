from __future__ import annotations

import json

import pytest

from exact_claim_verifier import verify_document
from exact_claim_verifier.cli import _InvalidJsonNumber, _parse_json_integer

MAX_DECIMAL_DIGITS = 640


def _polynomial_constant(value: str) -> dict[str, object]:
    return {
        "spec": "ECV/1",
        "domain": "integer-polynomial-identity",
        "claim": {
            "kind": "identity",
            "variables": ["x"],
            "left": {"op": "const", "value": value},
            "right": {"op": "const", "value": value},
        },
    }


def test_json_integer_boundary_is_host_independent() -> None:
    accepted = "9" * MAX_DECIMAL_DIGITS
    rejected = "9" * (MAX_DECIMAL_DIGITS + 1)

    assert _parse_json_integer(accepted) == int(accepted)
    with pytest.raises(_InvalidJsonNumber, match="exceeds 640 digits"):
        _parse_json_integer(rejected)


def test_maximum_decimal_component_is_verified_and_serializable() -> None:
    maximum = "9" * MAX_DECIMAL_DIGITS

    result = verify_document(_polynomial_constant(maximum))
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"))

    assert result["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
    assert result["derived"]["left_normal_form"][0]["coefficient"] == maximum
    assert json.loads(encoded) == result


def test_component_above_decimal_limit_is_a_resource_limit() -> None:
    oversized = "9" * (MAX_DECIMAL_DIGITS + 1)

    result = verify_document(_polynomial_constant(oversized))

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "INTEGER_DIGIT_LIMIT"


def test_serialization_boundary_is_enforced_before_rendering() -> None:
    large = "9" * 400
    node = {
        "op": "pow",
        "arg": {"op": "const", "value": large},
        "exponent": 2,
    }
    document = {
        "spec": "ECV/1",
        "domain": "integer-polynomial-identity",
        "claim": {
            "kind": "identity",
            "variables": ["x"],
            "left": node,
            "right": node,
        },
    }

    result = verify_document(document)

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "INTEGER_RESULT_LIMIT"
