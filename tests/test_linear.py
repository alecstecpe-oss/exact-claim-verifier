from __future__ import annotations

import exact_claim_verifier


def test_verifies_unique_rational_solution() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [["2", "1"], ["1", "-1"]],
                "rhs": ["5", "1"],
                "solution": ["2", "1"],
            },
        }
    )

    assert result == {
        "format": "ECV_RESULT_V1",
        "spec": "ECV/1",
        "domain": "rational-linear-system",
        "claim_kind": "unique-solution",
        "verdict": "EXACTLY_VERIFIED_IN_DOMAIN",
        "derived": {
            "equations": 2,
            "variables": 2,
            "rank_matrix": 2,
            "rank_augmented": 2,
            "residual_matches": True,
            "solution": ["2", "1"],
        },
        "errors": [],
    }


def test_rejects_noncanonical_rational_before_calculation() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [["1"]],
                "rhs": ["2/4"],
                "solution": ["1/2"],
            },
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"] == [
        {
            "code": "NONCANONICAL_RATIONAL",
            "path": "$.claim.rhs[0]",
            "message": "rational must use its reduced canonical form",
        }
    ]


def test_rejects_ragged_matrix_without_throwing() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [["1", "0"], ["1"]],
                "rhs": ["1", "1"],
                "solution": ["1", "0"],
            },
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "RAGGED_MATRIX"


def test_refutes_wrong_solution_exactly() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [["2", "1"], ["1", "-1"]],
                "rhs": ["5", "1"],
                "solution": ["2", "2"],
            },
        }
    )

    assert result["verdict"] == "REFUTED_IN_DOMAIN"
    assert result["derived"]["residual_matches"] is False


def test_rejects_unknown_linear_claim_kind() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "trust-me",
                "matrix": [["1"]],
                "rhs": ["1"],
                "solution": ["1"],
            },
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "UNSUPPORTED_CLAIM_KIND"


def test_reports_resource_limit_before_large_matrix_elimination() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [["0"] * 65],
                "rhs": ["0"],
                "solution": ["0"] * 65,
            },
        }
    )

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "MATRIX_DIMENSION_LIMIT"


def test_reports_resource_limit_for_fraction_growth_during_elimination() -> None:
    large = "9" * 400
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [[large, "1"], ["1", large]],
                "rhs": ["1", "1"],
                "solution": ["0", "0"],
            },
        }
    )

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "RATIONAL_RESULT_LIMIT"
