# Compatibility and schema stability

ECV is alpha software, but numbered contracts are not moving aliases.

## Input contracts

- `ECV/1` is frozen to its three original domains and normative ceilings.
- `ECV/2` is a superset that adds rational linear-program optimality certificates.
- A document always selects its contract explicitly through `spec`.
- Existing-domain semantics are not expanded silently. New mathematical authority requires a new `ECV/N` identifier.

The reference checker may support several numbered contracts at once. A valid but unsupported domain produces abstention; malformed schema or canonical data produces invalid input.

## Result contract

`ECV_RESULT_V1` remains stable while its fields and five verdict meanings remain unchanged. Adding a new input contract does not by itself require a new result format. Removing or changing a semantic field, changing a verdict meaning, or changing canonical CLI serialization requires a new result-format identifier.

## Release metadata and conformance

Release statements and conformance manifests have independent format identifiers. Their versions do not imply new mathematical authority.

The committed `ECV_CONFORMANCE_V1` corpus is immutable once published in a release. Adding or changing a normative vector requires a new conformance format or a documented correction release that preserves the earlier asset for audit history.

## Package versions

- patch releases may fix implementation, packaging, diagnostics, or security defects without expanding a numbered input contract;
- minor releases may add a new explicitly numbered input contract or additive tooling;
- incompatible public Python or CLI changes require a major package release.

Because ECV remains alpha, consumers should pin the package or Git commit and always inspect the numbered input and result identifiers rather than trusting the package version alone.
