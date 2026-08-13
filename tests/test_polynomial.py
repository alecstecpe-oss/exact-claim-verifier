from __future__ import annotations

import exact_claim_verifier


def test_verifies_structured_integer_polynomial_identity() -> None:
    x = {"op": "var", "name": "x"}
    one = {"op": "const", "value": "1"}
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": {
                    "op": "pow",
                    "arg": {"op": "add", "args": [x, one]},
                    "exponent": 2,
                },
                "right": {
                    "op": "add",
                    "args": [
                        {"op": "pow", "arg": x, "exponent": 2},
                        {"op": "mul", "args": [{"op": "const", "value": "2"}, x]},
                        one,
                    ],
                },
            },
        }
    )

    normal_form = [
        {"coefficient": "1", "powers": [2]},
        {"coefficient": "2", "powers": [1]},
        {"coefficient": "1", "powers": [0]},
    ]
    assert result["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
    assert result["derived"] == {
        "variables": ["x"],
        "left_normal_form": normal_form,
        "right_normal_form": normal_form,
    }


def test_refutes_false_integer_polynomial_identity() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": {"op": "var", "name": "x"},
                "right": {"op": "const", "value": "1"},
            },
        }
    )

    assert result["verdict"] == "REFUTED_IN_DOMAIN"


def test_rejects_undeclared_polynomial_variable() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": {"op": "var", "name": "y"},
                "right": {"op": "const", "value": "0"},
            },
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "UNDECLARED_VARIABLE"


def test_reports_resource_limit_for_deep_polynomial_ast() -> None:
    expression = {"op": "var", "name": "x"}
    for _ in range(129):
        expression = {"op": "neg", "arg": expression}

    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": expression,
                "right": {"op": "const", "value": "0"},
            },
        }
    )

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "POLYNOMIAL_DEPTH_LIMIT"


def test_rejects_nonstring_polynomial_operation_without_throwing() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": {"op": []},
                "right": {"op": "var", "name": "x"},
            },
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"] == [
        {
            "code": "INVALID_OPERATION",
            "path": "$.claim.left.op",
            "message": "operation must be a supported string",
        }
    ]


def test_reports_resource_limit_for_polynomial_coefficient_growth() -> None:
    huge = "9" * 1000
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": {
                    "op": "pow",
                    "arg": {"op": "const", "value": huge},
                    "exponent": 2,
                },
                "right": {"op": "const", "value": "0"},
            },
        }
    )

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "INTEGER_RESULT_LIMIT"
