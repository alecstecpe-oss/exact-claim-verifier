from __future__ import annotations

import re
from fractions import Fraction
from math import gcd
from typing import Any

_CANONICAL_INTEGER = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")
_VARIABLE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")
_MAX_POLYNOMIAL_NODES = 2_048
_MAX_POLYNOMIAL_TERMS = 10_000
_MAX_POLYNOMIAL_DEPTH = 128
_MAX_EXPONENT = 64
_MAX_INTEGER_DIGITS = 1_024
_MAX_INTEGER_RESULT_BITS = 4_096
_MAX_MATRIX_DIMENSION = 64


class _InputError(ValueError):
    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message


class _ResourceLimit(_InputError):
    """A valid-shaped request exceeds a declared verifier resource ceiling."""


def _encode(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _parse_rational(value: Any, path: str) -> Fraction:
    if not isinstance(value, str):
        raise _InputError(
            "RATIONAL_NOT_STRING",
            path,
            "exact rationals must be encoded as strings",
        )
    parts = value.split("/")
    if any(len(part.removeprefix("-")) > _MAX_INTEGER_DIGITS for part in parts):
        raise _ResourceLimit(
            "INTEGER_DIGIT_LIMIT",
            path,
            f"integer components are limited to {_MAX_INTEGER_DIGITS} digits",
        )
    if len(parts) not in {1, 2} or any(not _CANONICAL_INTEGER.fullmatch(part) for part in parts):
        raise _InputError(
            "INVALID_RATIONAL",
            path,
            "rational must be a canonical integer or numerator/denominator string",
        )
    if len(parts) == 2 and int(parts[1]) == 0:
        raise _InputError("ZERO_DENOMINATOR", path, "rational denominator must be nonzero")
    parsed = Fraction(int(parts[0]), int(parts[1]) if len(parts) == 2 else 1)
    if _encode(parsed) != value:
        raise _InputError(
            "NONCANONICAL_RATIONAL",
            path,
            "rational must use its reduced canonical form",
        )
    return parsed


def _parse_integer(value: Any, path: str) -> int:
    if isinstance(value, str) and len(value.removeprefix("-")) > _MAX_INTEGER_DIGITS:
        raise _ResourceLimit(
            "INTEGER_DIGIT_LIMIT",
            path,
            f"integers are limited to {_MAX_INTEGER_DIGITS} digits",
        )
    if not isinstance(value, str) or not _CANONICAL_INTEGER.fullmatch(value):
        raise _InputError(
            "INVALID_INTEGER",
            path,
            "integer must be a canonical decimal string",
        )
    return int(value)


def _expect_keys(node: dict[str, Any], expected: set[str], path: str) -> None:
    if any(not isinstance(key, str) for key in node):
        raise _InputError(
            "NONSTRING_OBJECT_KEY",
            path,
            "object keys must be strings",
        )
    extra = sorted(set(node) - expected)
    missing = sorted(expected - set(node))
    if missing:
        raise _InputError("MISSING_FIELD", path, f"missing field: {missing[0]}")
    if extra:
        raise _InputError("UNKNOWN_FIELD", f"{path}.{extra[0]}", "field is not permitted")


def _bounded_integer_result(value: int, path: str) -> int:
    if value.bit_length() > _MAX_INTEGER_RESULT_BITS:
        raise _ResourceLimit(
            "INTEGER_RESULT_LIMIT",
            path,
            f"intermediate integer results are limited to {_MAX_INTEGER_RESULT_BITS} bits",
        )
    return value


def _bounded_rational_result(value: Fraction, path: str) -> Fraction:
    if (
        value.numerator.bit_length() > _MAX_INTEGER_RESULT_BITS
        or value.denominator.bit_length() > _MAX_INTEGER_RESULT_BITS
    ):
        raise _ResourceLimit(
            "RATIONAL_RESULT_LIMIT",
            path,
            f"intermediate rational components are limited to {_MAX_INTEGER_RESULT_BITS} bits",
        )
    return value


def _poly_add(
    left: dict[tuple[int, ...], int], right: dict[tuple[int, ...], int]
) -> dict[tuple[int, ...], int]:
    result = left.copy()
    for monomial, coefficient in right.items():
        combined = _bounded_integer_result(
            result.get(monomial, 0) + coefficient,
            "$.claim",
        )
        if combined:
            result[monomial] = combined
        else:
            result.pop(monomial, None)
    if len(result) > _MAX_POLYNOMIAL_TERMS:
        raise _ResourceLimit("POLYNOMIAL_TERM_LIMIT", "$.claim", "polynomial term limit exceeded")
    return result


def _poly_mul(
    left: dict[tuple[int, ...], int], right: dict[tuple[int, ...], int]
) -> dict[tuple[int, ...], int]:
    result: dict[tuple[int, ...], int] = {}
    for left_power, left_coefficient in left.items():
        for right_power, right_coefficient in right.items():
            monomial = tuple(a + b for a, b in zip(left_power, right_power, strict=True))
            product = _bounded_integer_result(
                left_coefficient * right_coefficient,
                "$.claim",
            )
            result[monomial] = _bounded_integer_result(
                result.get(monomial, 0) + product,
                "$.claim",
            )
            if result[monomial] == 0:
                del result[monomial]
            if len(result) > _MAX_POLYNOMIAL_TERMS:
                raise _ResourceLimit(
                    "POLYNOMIAL_TERM_LIMIT", "$.claim", "polynomial term limit exceeded"
                )
    return result


def _normalize_polynomial(
    node: Any,
    variables: tuple[str, ...],
    path: str,
    counter: list[int],
    depth: int = 1,
) -> dict[tuple[int, ...], int]:
    if depth > _MAX_POLYNOMIAL_DEPTH:
        raise _ResourceLimit(
            "POLYNOMIAL_DEPTH_LIMIT",
            path,
            f"polynomial depth is limited to {_MAX_POLYNOMIAL_DEPTH}",
        )
    counter[0] += 1
    if counter[0] > _MAX_POLYNOMIAL_NODES:
        raise _ResourceLimit("POLYNOMIAL_NODE_LIMIT", path, "polynomial node limit exceeded")
    if not isinstance(node, dict):
        raise _InputError("NODE_NOT_OBJECT", path, "polynomial node must be an object")
    operation = node.get("op")
    if not isinstance(operation, str):
        raise _InputError(
            "INVALID_OPERATION",
            f"{path}.op",
            "operation must be a supported string",
        )
    zero = (0,) * len(variables)
    if operation == "const":
        _expect_keys(node, {"op", "value"}, path)
        coefficient = _parse_integer(node["value"], f"{path}.value")
        return {} if coefficient == 0 else {zero: coefficient}
    if operation == "var":
        _expect_keys(node, {"op", "name"}, path)
        name = node["name"]
        if name not in variables:
            raise _InputError("UNDECLARED_VARIABLE", f"{path}.name", "variable is not declared")
        powers = [0] * len(variables)
        powers[variables.index(name)] = 1
        return {tuple(powers): 1}
    if operation in {"add", "mul"}:
        _expect_keys(node, {"op", "args"}, path)
        arguments = node["args"]
        if not isinstance(arguments, list) or not arguments:
            raise _InputError("EMPTY_ARGUMENTS", f"{path}.args", "args must be a nonempty array")
        result = {} if operation == "add" else {zero: 1}
        for index, argument in enumerate(arguments):
            normalized = _normalize_polynomial(
                argument, variables, f"{path}.args[{index}]", counter, depth + 1
            )
            result = (
                _poly_add(result, normalized)
                if operation == "add"
                else _poly_mul(result, normalized)
            )
        return result
    if operation == "neg":
        _expect_keys(node, {"op", "arg"}, path)
        normalized = _normalize_polynomial(
            node["arg"], variables, f"{path}.arg", counter, depth + 1
        )
        return {powers: -coefficient for powers, coefficient in normalized.items()}
    if operation == "pow":
        _expect_keys(node, {"op", "arg", "exponent"}, path)
        exponent = node["exponent"]
        if type(exponent) is not int or not 0 <= exponent <= _MAX_EXPONENT:
            raise _InputError(
                "INVALID_EXPONENT",
                f"{path}.exponent",
                f"exponent must be an integer from 0 to {_MAX_EXPONENT}",
            )
        base = _normalize_polynomial(node["arg"], variables, f"{path}.arg", counter, depth + 1)
        result = {zero: 1}
        factor = base
        power = exponent
        while power:
            if power & 1:
                result = _poly_mul(result, factor)
            power >>= 1
            if power:
                factor = _poly_mul(factor, factor)
        return result
    raise _InputError("UNKNOWN_OPERATION", f"{path}.op", "operation is not supported")


def _encode_polynomial(polynomial: dict[tuple[int, ...], int]) -> list[dict[str, Any]]:
    return [
        {"coefficient": str(coefficient), "powers": list(powers)}
        for powers, coefficient in sorted(polynomial.items(), reverse=True)
    ]


def _rank(rows: list[list[Fraction]]) -> int:
    matrix = [row[:] for row in rows]
    if not matrix:
        return 0
    pivot_row = 0
    for column in range(len(matrix[0])):
        pivot = next(
            (row for row in range(pivot_row, len(matrix)) if matrix[row][column]),
            None,
        )
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        pivot_value = matrix[pivot_row][column]
        matrix[pivot_row] = [
            _bounded_rational_result(value / pivot_value, "$.claim.matrix")
            for value in matrix[pivot_row]
        ]
        for row in range(len(matrix)):
            if row == pivot_row:
                continue
            factor = matrix[row][column]
            if factor:
                matrix[row] = [
                    _bounded_rational_result(
                        value
                        - _bounded_rational_result(
                            factor * pivot_value,
                            "$.claim.matrix",
                        ),
                        "$.claim.matrix",
                    )
                    for value, pivot_value in zip(matrix[row], matrix[pivot_row], strict=True)
                ]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row


def _invalid(document: Any, code: str, path: str, message: str) -> dict[str, Any]:
    claim = document.get("claim") if isinstance(document, dict) else None
    spec = document.get("spec") if isinstance(document, dict) else None
    domain = document.get("domain") if isinstance(document, dict) else None
    claim_kind = claim.get("kind") if isinstance(claim, dict) else None
    return {
        "format": "ECV_RESULT_V1",
        "spec": spec if isinstance(spec, str) else None,
        "domain": domain if isinstance(domain, str) else None,
        "claim_kind": claim_kind if isinstance(claim_kind, str) else None,
        "verdict": "INVALID_INPUT",
        "derived": {},
        "errors": [{"code": code, "path": path, "message": message}],
    }


def _abstain(document: dict[str, Any], code: str, path: str, message: str) -> dict[str, Any]:
    claim = document["claim"]
    return {
        "format": "ECV_RESULT_V1",
        "spec": document["spec"],
        "domain": document["domain"],
        "claim_kind": claim.get("kind"),
        "verdict": "ABSTAIN_OUT_OF_DOMAIN",
        "derived": {},
        "errors": [{"code": code, "path": path, "message": message}],
    }


def _resource_limit(document: dict[str, Any], code: str, path: str, message: str) -> dict[str, Any]:
    claim = document["claim"]
    return {
        "format": "ECV_RESULT_V1",
        "spec": document["spec"],
        "domain": document["domain"],
        "claim_kind": claim.get("kind"),
        "verdict": "RESOURCE_LIMIT",
        "derived": {},
        "errors": [{"code": code, "path": path, "message": message}],
    }


def _verify_linear(document: dict[str, Any]) -> dict[str, Any]:
    claim = document["claim"]
    try:
        _expect_keys(claim, {"kind", "matrix", "rhs", "solution"}, "$.claim")
        if claim["kind"] != "unique-solution":
            raise _InputError(
                "UNSUPPORTED_CLAIM_KIND",
                "$.claim.kind",
                "claim kind is not supported",
            )
    except _InputError as error:
        return _invalid(document, error.code, error.path, error.message)
    raw_matrix = claim["matrix"]
    raw_rhs = claim["rhs"]
    raw_solution = claim["solution"]
    if not isinstance(raw_matrix, list) or not raw_matrix:
        return _invalid(document, "EMPTY_MATRIX", "$.claim.matrix", "matrix must be nonempty")
    if any(not isinstance(row, list) for row in raw_matrix):
        return _invalid(document, "MATRIX_ROW_NOT_ARRAY", "$.claim.matrix", "rows must be arrays")
    columns = len(raw_matrix[0])
    if columns == 0:
        return _invalid(document, "EMPTY_MATRIX_ROW", "$.claim.matrix[0]", "rows must be nonempty")
    if len(raw_matrix) > _MAX_MATRIX_DIMENSION or columns > _MAX_MATRIX_DIMENSION:
        return _resource_limit(
            document,
            "MATRIX_DIMENSION_LIMIT",
            "$.claim.matrix",
            f"matrix dimensions are limited to {_MAX_MATRIX_DIMENSION} by {_MAX_MATRIX_DIMENSION}",
        )
    if any(len(row) != columns for row in raw_matrix):
        return _invalid(
            document,
            "RAGGED_MATRIX",
            "$.claim.matrix",
            "all matrix rows must have equal length",
        )
    if not isinstance(raw_rhs, list) or len(raw_rhs) != len(raw_matrix):
        return _invalid(
            document,
            "RHS_LENGTH_MISMATCH",
            "$.claim.rhs",
            "rhs length must equal the number of equations",
        )
    if not isinstance(raw_solution, list) or len(raw_solution) != columns:
        return _invalid(
            document,
            "SOLUTION_LENGTH_MISMATCH",
            "$.claim.solution",
            "solution length must equal the number of variables",
        )
    try:
        matrix = [
            [
                _parse_rational(value, f"$.claim.matrix[{row_index}][{column_index}]")
                for column_index, value in enumerate(row)
            ]
            for row_index, row in enumerate(claim["matrix"])
        ]
        rhs = [
            _parse_rational(value, f"$.claim.rhs[{index}]")
            for index, value in enumerate(claim["rhs"])
        ]
        solution = [
            _parse_rational(value, f"$.claim.solution[{index}]")
            for index, value in enumerate(claim["solution"])
        ]
    except _ResourceLimit as error:
        return _resource_limit(document, error.code, error.path, error.message)
    except _InputError as error:
        return _invalid(document, error.code, error.path, error.message)
    try:
        rank_matrix = _rank(matrix)
        augmented = [row + [value] for row, value in zip(matrix, rhs, strict=True)]
        rank_augmented = _rank(augmented)
        residual_matches = True
        for row, expected in zip(matrix, rhs, strict=True):
            observed = Fraction(0)
            for coefficient, value in zip(row, solution, strict=True):
                product = _bounded_rational_result(
                    coefficient * value,
                    "$.claim",
                )
                observed = _bounded_rational_result(observed + product, "$.claim")
            if observed != expected:
                residual_matches = False
    except _ResourceLimit as error:
        return _resource_limit(document, error.code, error.path, error.message)
    verified = residual_matches and rank_matrix == len(solution) == rank_augmented
    return {
        "format": "ECV_RESULT_V1",
        "spec": document["spec"],
        "domain": document["domain"],
        "claim_kind": claim["kind"],
        "verdict": ("EXACTLY_VERIFIED_IN_DOMAIN" if verified else "REFUTED_IN_DOMAIN"),
        "derived": {
            "equations": len(matrix),
            "variables": len(solution),
            "rank_matrix": rank_matrix,
            "rank_augmented": rank_augmented,
            "residual_matches": residual_matches,
            "solution": [_encode(value) for value in solution],
        },
        "errors": [],
    }


def _verify_polynomial(document: dict[str, Any]) -> dict[str, Any]:
    claim = document["claim"]
    try:
        _expect_keys(claim, {"kind", "variables", "left", "right"}, "$.claim")
        if claim["kind"] != "identity":
            raise _InputError(
                "UNSUPPORTED_CLAIM_KIND", "$.claim.kind", "claim kind is not supported"
            )
        raw_variables = claim["variables"]
        if not isinstance(raw_variables, list) or not 1 <= len(raw_variables) <= 8:
            raise _InputError(
                "INVALID_VARIABLES", "$.claim.variables", "variables must contain 1 to 8 names"
            )
        if any(
            not isinstance(name, str) or not _VARIABLE_NAME.fullmatch(name)
            for name in raw_variables
        ):
            raise _InputError(
                "INVALID_VARIABLE_NAME",
                "$.claim.variables",
                "variable names must match [A-Za-z][A-Za-z0-9_]{0,31}",
            )
        if len(set(raw_variables)) != len(raw_variables):
            raise _InputError(
                "DUPLICATE_VARIABLE", "$.claim.variables", "variable names must be unique"
            )
        variables = tuple(raw_variables)
        left = _normalize_polynomial(claim["left"], variables, "$.claim.left", [0])
        right = _normalize_polynomial(claim["right"], variables, "$.claim.right", [0])
    except _ResourceLimit as error:
        return _resource_limit(document, error.code, error.path, error.message)
    except _InputError as error:
        return _invalid(document, error.code, error.path, error.message)
    return {
        "format": "ECV_RESULT_V1",
        "spec": document["spec"],
        "domain": document["domain"],
        "claim_kind": claim["kind"],
        "verdict": ("EXACTLY_VERIFIED_IN_DOMAIN" if left == right else "REFUTED_IN_DOMAIN"),
        "derived": {
            "variables": list(variables),
            "left_normal_form": _encode_polynomial(left),
            "right_normal_form": _encode_polynomial(right),
        },
        "errors": [],
    }


def _verify_modular(document: dict[str, Any]) -> dict[str, Any]:
    claim = document["claim"]
    try:
        _expect_keys(claim, {"kind", "congruences", "solution"}, "$.claim")
        if claim["kind"] != "crt-solution":
            raise _InputError(
                "UNSUPPORTED_CLAIM_KIND", "$.claim.kind", "claim kind is not supported"
            )
        raw_congruences = claim["congruences"]
        if not isinstance(raw_congruences, list) or not 1 <= len(raw_congruences) <= 128:
            raise _InputError(
                "INVALID_CONGRUENCES",
                "$.claim.congruences",
                "congruences must contain 1 to 128 entries",
            )
        residues: list[int] = []
        moduli: list[int] = []
        for index, congruence in enumerate(raw_congruences):
            path = f"$.claim.congruences[{index}]"
            if not isinstance(congruence, dict):
                raise _InputError("CONGRUENCE_NOT_OBJECT", path, "congruence must be an object")
            _expect_keys(congruence, {"residue", "modulus"}, path)
            modulus = _parse_integer(congruence["modulus"], f"{path}.modulus")
            residue = _parse_integer(congruence["residue"], f"{path}.residue")
            if modulus <= 1:
                raise _InputError(
                    "INVALID_MODULUS", f"{path}.modulus", "modulus must be greater than 1"
                )
            if not 0 <= residue < modulus:
                raise _InputError(
                    "NONCANONICAL_RESIDUE",
                    f"{path}.residue",
                    "residue must be in the interval 0 <= residue < modulus",
                )
            residues.append(residue)
            moduli.append(modulus)
        for left in range(len(moduli)):
            for right in range(left + 1, len(moduli)):
                if gcd(moduli[left], moduli[right]) != 1:
                    return _abstain(
                        document,
                        "DOMAIN_PRECONDITION_NOT_MET",
                        "$.claim.congruences",
                        "ECV/1 CRT requires pairwise coprime moduli",
                    )
        uniqueness_modulus = 1
        for modulus in moduli:
            uniqueness_modulus = _bounded_integer_result(
                uniqueness_modulus * modulus,
                "$.claim.congruences",
            )
        solution = _parse_integer(claim["solution"], "$.claim.solution")
        if not 0 <= solution < uniqueness_modulus:
            raise _InputError(
                "NONCANONICAL_CRT_SOLUTION",
                "$.claim.solution",
                "solution must be canonical modulo the product of the moduli",
            )
    except _ResourceLimit as error:
        return _resource_limit(document, error.code, error.path, error.message)
    except _InputError as error:
        return _invalid(document, error.code, error.path, error.message)
    verified = all(
        solution % modulus == residue for residue, modulus in zip(residues, moduli, strict=True)
    )
    return {
        "format": "ECV_RESULT_V1",
        "spec": document["spec"],
        "domain": document["domain"],
        "claim_kind": claim["kind"],
        "verdict": ("EXACTLY_VERIFIED_IN_DOMAIN" if verified else "REFUTED_IN_DOMAIN"),
        "derived": {
            "residues": [str(value) for value in residues],
            "moduli": [str(value) for value in moduli],
            "solution": str(solution),
            "uniqueness_modulus": str(uniqueness_modulus),
        },
        "errors": [],
    }


def verify_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        return _invalid(document, "DOCUMENT_NOT_OBJECT", "$", "document must be an object")
    try:
        _expect_keys(document, {"spec", "domain", "claim"}, "$")
    except _InputError as error:
        return _invalid(document, error.code, error.path, error.message)
    if document.get("spec") != "ECV/1":
        return _invalid(document, "UNSUPPORTED_SPEC", "$.spec", "only ECV/1 is supported")
    claim = document.get("claim")
    if not isinstance(claim, dict):
        return _invalid(document, "CLAIM_NOT_OBJECT", "$.claim", "claim must be an object")
    domain = document.get("domain")
    if not isinstance(domain, str):
        return _invalid(
            document,
            "DOMAIN_NOT_STRING",
            "$.domain",
            "domain must be a string",
        )
    kind = claim.get("kind")
    if not isinstance(kind, str):
        return _invalid(
            document,
            "CLAIM_KIND_NOT_STRING",
            "$.claim.kind",
            "claim kind must be a string",
        )
    if domain == "rational-linear-system":
        return _verify_linear(document)
    if domain == "integer-polynomial-identity":
        return _verify_polynomial(document)
    if domain == "modular-arithmetic":
        return _verify_modular(document)
    return {
        "format": "ECV_RESULT_V1",
        "spec": document.get("spec"),
        "domain": domain,
        "claim_kind": claim.get("kind"),
        "verdict": "ABSTAIN_OUT_OF_DOMAIN",
        "derived": {},
        "errors": [
            {
                "code": "UNSUPPORTED_DOMAIN",
                "path": "$.domain",
                "message": "domain is not supported by this verifier",
            }
        ],
    }
