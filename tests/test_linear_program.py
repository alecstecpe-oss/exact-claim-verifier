from __future__ import annotations

from copy import deepcopy

from exact_claim_verifier import verify_document


def _optimal_certificate() -> dict[str, object]:
    return {
        "spec": "ECV/2",
        "domain": "rational-linear-program",
        "claim": {
            "kind": "optimal-solution-certificate",
            "matrix": [["1", "1"], ["1", "0"], ["0", "1"]],
            "rhs": ["4", "2", "3"],
            "objective": ["3", "2"],
            "primal_solution": ["2", "2"],
            "dual_solution": ["2", "1", "0"],
            "optimum": "10",
        },
    }


def test_exact_primal_dual_certificate_verifies_optimality() -> None:
    result = verify_document(_optimal_certificate())

    assert result["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
    assert result["errors"] == []
    assert result["derived"] == {
        "constraints": 3,
        "variables": 2,
        "primal_feasible": True,
        "dual_feasible": True,
        "objective_agreement": True,
        "primal_objective": "10",
        "dual_objective": "10",
        "optimum": "10",
        "primal_solution": ["2", "2"],
        "dual_solution": ["2", "1", "0"],
    }


def test_ecv1_abstains_from_the_ecv2_linear_program_domain() -> None:
    document = _optimal_certificate()
    document["spec"] = "ECV/1"

    result = verify_document(document)

    assert result["verdict"] == "ABSTAIN_OUT_OF_DOMAIN"
    assert result["errors"][0]["code"] == "UNSUPPORTED_DOMAIN_FOR_SPEC"


def test_infeasible_primal_certificate_is_refuted() -> None:
    document = _optimal_certificate()
    document["claim"]["primal_solution"] = ["3", "2"]

    result = verify_document(document)

    assert result["verdict"] == "REFUTED_IN_DOMAIN"
    assert result["derived"]["primal_feasible"] is False


def test_infeasible_dual_certificate_is_refuted() -> None:
    document = _optimal_certificate()
    document["claim"]["dual_solution"] = ["0", "0", "0"]

    result = verify_document(document)

    assert result["verdict"] == "REFUTED_IN_DOMAIN"
    assert result["derived"]["dual_feasible"] is False


def test_wrong_optimum_is_refuted_even_when_primal_and_dual_are_feasible() -> None:
    document = _optimal_certificate()
    document["claim"]["optimum"] = "9"

    result = verify_document(document)

    assert result["verdict"] == "REFUTED_IN_DOMAIN"
    assert result["derived"]["primal_feasible"] is True
    assert result["derived"]["dual_feasible"] is True
    assert result["derived"]["objective_agreement"] is False


def test_linear_program_rejects_noncanonical_and_mismatched_values() -> None:
    noncanonical = _optimal_certificate()
    noncanonical["claim"]["optimum"] = "20/2"
    result = verify_document(noncanonical)
    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "NONCANONICAL_RATIONAL"

    mismatched = _optimal_certificate()
    mismatched["claim"]["dual_solution"] = ["2"]
    result = verify_document(mismatched)
    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "VECTOR_LENGTH_MISMATCH"


def test_linear_program_matrix_limit_is_not_refutation() -> None:
    document = _optimal_certificate()
    document["claim"] = {
        "kind": "optimal-solution-certificate",
        "matrix": [["1"] for _ in range(65)],
        "rhs": ["1"] * 65,
        "objective": ["1"],
        "primal_solution": ["1"],
        "dual_solution": ["1"] + ["0"] * 64,
        "optimum": "1",
    }

    result = verify_document(document)

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "MATRIX_DIMENSION_LIMIT"


def test_diagonal_linear_programs_match_direct_optimality_oracle() -> None:
    for dimension in range(1, 6):
        bounds = [index + 2 for index in range(dimension)]
        objective = [2 * index + 1 for index in range(dimension)]
        optimum = sum(
            bound * coefficient for bound, coefficient in zip(bounds, objective, strict=True)
        )
        document = {
            "spec": "ECV/2",
            "domain": "rational-linear-program",
            "claim": {
                "kind": "optimal-solution-certificate",
                "matrix": [
                    ["1" if row == column else "0" for column in range(dimension)]
                    for row in range(dimension)
                ],
                "rhs": [str(value) for value in bounds],
                "objective": [str(value) for value in objective],
                "primal_solution": [str(value) for value in bounds],
                "dual_solution": [str(value) for value in objective],
                "optimum": str(optimum),
            },
        }

        assert verify_document(document)["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"

        tampered = deepcopy(document)
        tampered["claim"]["optimum"] = str(optimum + 1)
        assert verify_document(tampered)["verdict"] == "REFUTED_IN_DOMAIN"
