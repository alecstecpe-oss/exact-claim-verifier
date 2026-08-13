from __future__ import annotations

import exact_claim_verifier


def test_rejects_unknown_top_level_field() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "future-domain",
            "claim": {"kind": "future-claim"},
            "approve_anyway": True,
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"] == [
        {
            "code": "UNKNOWN_FIELD",
            "path": "$.approve_anyway",
            "message": "field is not permitted",
        }
    ]


def test_reports_resource_limit_for_oversized_integer_literal() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "modular-arithmetic",
            "claim": {
                "kind": "crt-solution",
                "congruences": [{"residue": "0", "modulus": "1" * 4097}],
                "solution": "0",
            },
        }
    )

    assert result["verdict"] == "RESOURCE_LIMIT"
    assert result["errors"][0]["code"] == "INTEGER_DIGIT_LIMIT"


def test_python_api_rejects_nonstring_object_key_without_throwing() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "future-domain",
            "claim": {"kind": "future-claim"},
            7: "not-json",
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["errors"][0]["code"] == "NONSTRING_OBJECT_KEY"


def test_valid_unknown_domain_abstains() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "future-domain",
            "claim": {"kind": "future-claim"},
        }
    )

    assert result["verdict"] == "ABSTAIN_OUT_OF_DOMAIN"
    assert result["errors"][0]["code"] == "UNSUPPORTED_DOMAIN"


def test_rejects_nonstring_domain_without_echoing_attacker_structure() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": {"nested": ["attacker"]},
            "claim": {"kind": "future-claim"},
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["domain"] is None
    assert result["errors"][0]["code"] == "DOMAIN_NOT_STRING"


def test_unknown_domain_requires_string_claim_kind() -> None:
    result = exact_claim_verifier.verify_document(
        {
            "spec": "ECV/1",
            "domain": "future-domain",
            "claim": {"kind": ["not", "text"]},
        }
    )

    assert result["verdict"] == "INVALID_INPUT"
    assert result["claim_kind"] is None
    assert result["errors"][0]["code"] == "CLAIM_KIND_NOT_STRING"
