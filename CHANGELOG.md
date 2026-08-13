# Changelog

All notable changes to this project are documented here.

## 0.2.0 - 2026-08-13

- Add the explicit `ECV/2` contract while preserving `ECV/1` semantics.
- Add exact certificate checking for rational linear-program optimality via primal/dual feasibility and objective agreement.
- Add a byte-exact nine-case `ECV_CONFORMANCE_V1` corpus and external runner covering all five verdicts.
- Fix cross-platform canonical CLI bytes by emitting LF directly instead of platform-translated newlines.
- Fail closed when the Python API receives a non-string, unhashable `spec` value instead of leaking `TypeError`.
- Add a reusable composite GitHub Action with explicit expected-verdict gating.
- Add schema compatibility policy and an honest comparison with CAS, SMT solvers, proof assistants, and proof checkers.
- Bind the conformance archive in `ECV_RELEASE_STATEMENT_V2` and release checksums.

## 0.1.1 - 2026-08-13

- Make JSON-token, exact-component, and intermediate-result ceilings host-independent at 640 decimal digits.
- Return machine-readable `COMMAND_INPUT_ERROR` results for invalid CLI syntax.
- Add regressions for Python's minimum `PYTHONINTMAXSTRDIGITS` policy and serialization growth.
- Add deterministic release statements, basename-only checksums, exact sdist/wheel replay, and GitHub artifact attestations.
- Document the separation between bounded mathematical verification, release provenance, and universal proof.

## 0.1.0 - 2026-08-13

- Add the strict `ECV/1` input and `ECV_RESULT_V1` result contracts.
- Add exact verification for unique rational linear-system solutions.
- Add structured integer-polynomial identity verification.
- Add pairwise-coprime CRT solution verification.
- Add explicit refutation, abstention, invalid-input, and resource-limit verdicts.
- Add strict JSON parsing, deterministic application ceilings, CLI, tests, specification, and threat model.
