# Threat model

## Assets

ECV protects the meaning of its bounded verdict: a caller should not receive `EXACTLY_VERIFIED_IN_DOMAIN` unless the exact structured predicate documented by ECV/1 recomputes true.

The trusted computing base for v0.1 is:

- `src/exact_claim_verifier/core.py`;
- `src/exact_claim_verifier/cli.py` for the byte-to-result path;
- the compatible Python interpreter and standard library;
- the host operating system and hardware.

No network service, model, solver binary, plugin, South runtime, or private registry is in the runtime TCB.

## Attacker capabilities considered

The input producer may control the entire input file and may attempt:

- malformed UTF-8 or JSON;
- duplicate keys or nonstandard JSON constants;
- unknown, missing, or wrong-typed fields;
- noncanonical integers and rationals;
- zero denominators, invalid moduli, undeclared variables, or unknown AST operations;
- false linear, polynomial, or CRT claims;
- deep/wide ASTs, large matrices, huge integer components, and growing intermediates;
- excessively nested JSON containers and oversized JSON number tokens;
- a directory, missing path, or oversized file in place of a regular input document.

The checker fails closed with `INVALID_INPUT`, `RESOURCE_LIMIT`, `ABSTAIN_OUT_OF_DOMAIN`, or `REFUTED_IN_DOMAIN` for the covered cases.

## Security properties

Within ECV/1 and the stated TCB:

- no floating-point conversion participates in a verdict;
- unknown top-level or claim fields cannot silently change semantics;
- duplicate JSON keys cannot shadow earlier values;
- polynomial expressions are data-only ASTs, not executable text;
- supported-domain predicates are recomputed by public code;
- unknown domains produce abstention;
- non-pairwise-coprime generalized CRT produces abstention;
- deterministic application ceilings bound declared input dimensions and exact-number growth;
- decimal input and result ceilings remain enforceable under Python's minimum supported integer-string threshold;
- expected document and command-line failures produce machine-readable JSON instead of Python tracebacks.

## Out of scope and residual risk

ECV does not defend against:

- a compromised interpreter, standard library, OS, hardware, or package artifact;
- concurrent replacement or mutation of the input file while it is being opened/read;
- OS-level denial of service outside its application ceilings;
- hostile process scheduling, disk faults, or forced termination;
- natural-language formalization errors;
- fabricated real-world inputs;
- provenance, authentication, signatures, timestamps, confidentiality, or replay freshness;
- arbitrary mathematical domains or a universal theorem-proving adversary.

The 1 MiB input cap and mathematical ceilings reduce denial-of-service surface but are not CPU, wall-clock, address-space, or process quotas. Run untrusted workloads under OS sandboxing and quotas when those properties are required.

The GitHub release workflow, checksums, release statement, and attestations protect distribution identity and provenance. They do not authenticate an ECV input, prove that a formal claim matches external intent, or make the source repository itself a trusted independent builder.

## Composition with VEC

A Verifiable Evidence Capsule can bind ECV input/result bytes to a content-addressed inventory and an externally pinned root. That composition does not prove that the formal claim matches a natural-language statement or real-world fact. Keep byte-integrity and mathematical-verdict claims distinct.

## Reporting

Report a suspected false positive, uncaught exception, ceiling bypass, or schema ambiguity privately using the process in [SECURITY.md](../SECURITY.md).
