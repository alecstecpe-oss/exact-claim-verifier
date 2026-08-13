# Exact Claim Verifier specification v2

Status: normative for `ECV/2` in package version 0.2.x. `ECV_RESULT_V1` remains the result envelope.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative requirements.

## 1. Relationship to ECV/1

`ECV/2` incorporates the strict JSON, canonical exact-value, result, verdict, rational linear-system, integer-polynomial, pairwise-coprime CRT, resource-ceiling, and security rules of [ECV/1](ECV_SPEC_V1.md).

An implementation advertising `ECV/2` MUST also accept every valid `ECV/1` document without changing the ECV/1 domain semantics. A document selects its contract explicitly with the top-level `spec` field. The new domain in section 2 MUST NOT be adjudicated under `ECV/1`; a well-formed ECV/1 document using it produces `ABSTAIN_OUT_OF_DOMAIN` with `UNSUPPORTED_DOMAIN_FOR_SPEC`.

`ECV/2` adds one certificate-carrying exact domain. It does not add a solver or search procedure.

## 2. Rational linear-program optimality certificates

Domain: `rational-linear-program`
Claim kind: `optimal-solution-certificate`

The claim object MUST contain exactly:

```json
{
  "kind":"optimal-solution-certificate",
  "matrix":[["1"]],
  "rhs":["2"],
  "objective":["3"],
  "primal_solution":["2"],
  "dual_solution":["3"],
  "optimum":"6"
}
```

All scalar values MUST be canonical rationals under ECV/1 section 3. `matrix` MUST be nonempty and rectangular with nonempty rows. If it has `m` rows and `n` columns:

- `rhs` and `dual_solution` MUST each contain exactly `m` values;
- `objective` and `primal_solution` MUST each contain exactly `n` values;
- `m` and `n` MUST each be at most 64.

The document represents the primal program

```text
maximize    c^T x
subject to  A x <= b
            x >= 0
```

and its dual

```text
minimize    b^T y
subject to  A^T y >= c
            y >= 0
```

where `A` is `matrix`, `b` is `rhs`, `c` is `objective`, `x` is `primal_solution`, and `y` is `dual_solution`.

The checker MUST recompute with exact rational arithmetic:

```text
primal_feasible    = (x >= 0) and (A x <= b)
dual_feasible      = (y >= 0) and (A^T y >= c)
primal_objective   = c^T x
dual_objective     = b^T y
objective_agreement = primal_objective == optimum == dual_objective
```

The verdict is `EXACTLY_VERIFIED_IN_DOMAIN` iff all three booleans are true. Otherwise it is `REFUTED_IN_DOMAIN`. By weak duality, feasible primal and dual witnesses with equal objectives certify optimality for this declared form. The checker does not search for either witness and does not decide whether an arbitrary LP is feasible, infeasible, bounded, or unbounded when no closing certificate is supplied.

`derived` MUST contain:

- `constraints` and `variables`;
- `primal_feasible`, `dual_feasible`, and `objective_agreement`;
- canonical `primal_objective`, `dual_objective`, and `optimum`;
- canonical copies of `primal_solution` and `dual_solution`.

Exact intermediate values remain subject to the ECV/1 640-decimal-digit ceiling. Crossing a ceiling produces `RESOURCE_LIMIT`, never refutation.

## 3. Conformance corpus

`ECV_CONFORMANCE_V1` is the finite byte-exact interoperability corpus shipped with package 0.2.x and release assets. Each case binds input bytes, expected `ECV_RESULT_V1` bytes, process exit, and SHA-256 digests.

Passing this corpus demonstrates agreement on the included vectors. It does not prove full implementation correctness, security, or conformance for every possible input. Implementations MUST NOT market a finite corpus pass as formal verification.

## 4. Compatibility

Within a numbered input contract, accepted input meaning and positive-verdict meaning are stable. New mathematical authority requires a new `ECV/N` contract. New optional tooling, tests, examples, diagnostics, or release metadata may be added without changing an existing input contract.

The result contract remains `ECV_RESULT_V1` because its semantic fields and verdict set are unchanged. A future incompatible result shape requires a new result format identifier.

## 5. Security and semantic boundary

An ECV/2 verified result establishes only that the supplied primal and dual values close the exact optimality predicate above under the declared canonical data. It does not establish that:

- the linear program formalizes a natural-language or real-world problem correctly;
- either witness was produced independently;
- the input has authentic provenance;
- a publisher identity, timestamp, or execution history is valid;
- a general LP solver or proof assistant has certified any claim outside this contract.

Implementations MUST preserve the distinction among verification, refutation, abstention, invalid input, and resource limits.
