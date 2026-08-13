from __future__ import annotations

import exact_claim_verifier


def test_verifies_pairwise_coprime_crt_solution() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "modular-arithmetic",
            "claim": {
                "kind": "crt-solution",
                "congruences": [
                    {"residue": "2", "modulus": "3"},
                    {"residue": "3", "modulus": "5"},
                    {"residue": "2", "modulus": "7"},
                ],
                "solution": "23",
            },
        }
    )

    assert result == {
        "format": "ECV_RESULT_V1",
        "spec": "ECV/1",
        "domain": "modular-arithmetic",
        "claim_kind": "crt-solution",
        "verdict": "EXACTLY_VERIFIED_IN_DOMAIN",
        "derived": {
            "residues": ["2", "3", "2"],
            "moduli": ["3", "5", "7"],
            "solution": "23",
            "uniqueness_modulus": "105",
        },
        "errors": [],
    }


def test_refutes_wrong_crt_solution() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "modular-arithmetic",
            "claim": {
                "kind": "crt-solution",
                "congruences": [
                    {"residue": "2", "modulus": "3"},
                    {"residue": "3", "modulus": "5"},
                ],
                "solution": "7",
            },
        }
    )

    assert result["verdict"] == "REFUTED_IN_DOMAIN"


def test_abstains_when_crt_moduli_are_not_pairwise_coprime() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "modular-arithmetic",
            "claim": {
                "kind": "crt-solution",
                "congruences": [
                    {"residue": "1", "modulus": "4"},
                    {"residue": "3", "modulus": "6"},
                ],
                "solution": "9",
            },
        }
    )

    assert result["verdict"] == "ABSTAIN_OUT_OF_DOMAIN"
    assert result["errors"] == [
        {
            "code": "DOMAIN_PRECONDITION_NOT_MET",
            "path": "$.claim.congruences",
            "message": "ECV/1 CRT requires pairwise coprime moduli",
        }
    ]


def test_reports_resource_limit_for_crt_product_growth() -> None:
    first_modulus = "1" + ("0" * 998) + "7"
    second_modulus = "1" + ("0" * 998) + "9"
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "modular-arithmetic",
            "claim": {
                "kind": "crt-solution",
                "congruences": [
                    {"residue": "0", "modulus": first_modulus},
                    {"residue": "0", "modulus": second_modulus},
                ],
                "solution": "0",
            },
        }
    )

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "INTEGER_RESULT_LIMIT"
