# Changelog

All notable changes to this project are documented here.

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
