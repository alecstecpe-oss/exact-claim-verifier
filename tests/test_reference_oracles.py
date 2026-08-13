from __future__ import annotations

import random
from math import prod
from typing import Any

from exact_claim_verifier import verify_document


def _integer(value: int) -> str:
    return str(value)


def test_100_invertible_linear_systems_against_determinant_oracle() -> None:
    rng = random.Random(20260813)
    checked = 0
    while checked < 100:
        a, b, c, d = (rng.randint(-7, 7) for _ in range(4))
        if a * d - b * c == 0:
            continue
        x0, x1 = rng.randint(-9, 9), rng.randint(-9, 9)
        rhs0 = a * x0 + b * x1
        rhs1 = c * x0 + d * x1
        base: dict[str, Any] = {
            "spec": "ECV/1",
            "domain": "rational-linear-system",
            "claim": {
                "kind": "unique-solution",
                "matrix": [[_integer(a), _integer(b)], [_integer(c), _integer(d)]],
                "rhs": [_integer(rhs0), _integer(rhs1)],
                "solution": [_integer(x0), _integer(x1)],
            },
        }

        verified = verify_document(base)
        wrong = {
            **base,
            "claim": {
                **base["claim"],
                "solution": [_integer(x0 + 1), _integer(x1)],
            },
        }
        refuted = verify_document(wrong)

        assert verified["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
        assert verified["derived"]["rank_matrix"] == 2
        assert verified["derived"]["residual_matches"] is True
        assert refuted["verdict"] == "REFUTED_IN_DOMAIN"
        assert refuted["derived"]["residual_matches"] is False
        checked += 1


def _const(value: int) -> dict[str, Any]:
    return {"op": "const", "value": str(value)}


def _expanded_polynomial(coefficients: list[int]) -> dict[str, Any]:
    x = {"op": "var", "name": "x"}
    terms: list[dict[str, Any]] = []
    for exponent, coefficient in enumerate(coefficients):
        if coefficient == 0:
            continue
        power = x if exponent == 1 else {"op": "pow", "arg": x, "exponent": exponent}
        terms.append(
            _const(coefficient)
            if exponent == 0
            else {"op": "mul", "args": [_const(coefficient), power]}
        )
    if not terms:
        return _const(0)
    return terms[0] if len(terms) == 1 else {"op": "add", "args": terms}


def _horner_polynomial(coefficients: list[int]) -> dict[str, Any]:
    x = {"op": "var", "name": "x"}
    result = _const(coefficients[-1])
    for coefficient in reversed(coefficients[:-1]):
        result = {
            "op": "add",
            "args": [
                {"op": "mul", "args": [result, x]},
                _const(coefficient),
            ],
        }
    return result


def test_100_polynomials_against_independent_horner_construction() -> None:
    rng = random.Random(20260814)
    for _ in range(100):
        coefficients = [rng.randint(-5, 5) for _ in range(rng.randint(1, 6))]
        expanded = _expanded_polynomial(coefficients)
        horner = _horner_polynomial(coefficients)
        base = {
            "spec": "ECV/1",
            "domain": "integer-polynomial-identity",
            "claim": {
                "kind": "identity",
                "variables": ["x"],
                "left": expanded,
                "right": horner,
            },
        }

        verified = verify_document(base)
        refuted = verify_document(
            {
                **base,
                "claim": {
                    **base["claim"],
                    "right": {"op": "add", "args": [horner, _const(1)]},
                },
            }
        )

        assert verified["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
        assert verified["derived"]["left_normal_form"] == verified["derived"]["right_normal_form"]
        assert refuted["verdict"] == "REFUTED_IN_DOMAIN"


def test_100_crt_claims_against_bounded_exhaustive_oracle() -> None:
    rng = random.Random(20260815)
    primes = [2, 3, 5, 7]
    for _ in range(100):
        moduli = rng.sample(primes, rng.randint(1, len(primes)))
        residues = [rng.randrange(modulus) for modulus in moduli]
        uniqueness_modulus = prod(moduli)
        solution = next(
            candidate
            for candidate in range(uniqueness_modulus)
            if all(
                candidate % modulus == residue
                for residue, modulus in zip(residues, moduli, strict=True)
            )
        )
        base = {
            "spec": "ECV/1",
            "domain": "modular-arithmetic",
            "claim": {
                "kind": "crt-solution",
                "congruences": [
                    {"residue": str(residue), "modulus": str(modulus)}
                    for residue, modulus in zip(residues, moduli, strict=True)
                ],
                "solution": str(solution),
            },
        }

        verified = verify_document(base)
        wrong_solution = (solution + 1) % uniqueness_modulus
        refuted = verify_document(
            {
                **base,
                "claim": {**base["claim"], "solution": str(wrong_solution)},
            }
        )

        assert verified["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN"
        assert verified["derived"]["uniqueness_modulus"] == str(uniqueness_modulus)
        assert refuted["verdict"] == "REFUTED_IN_DOMAIN"
