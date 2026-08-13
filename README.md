# Exact Claim Verifier

[![CI](https://github.com/alecstecpe-oss/exact-claim-verifier/actions/workflows/ci.yml/badge.svg)](https://github.com/alecstecpe-oss/exact-claim-verifier/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Exact Claim Verifier (ECV) is a small, offline reference checker for structured exact claims in explicitly declared mathematical domains. It uses only the Python standard library at runtime and never converts exact values to floating point.

ECV does not parse natural-language mathematics. A producer supplies an `ECV/1` JSON claim; the public checker validates its schema, recomputes the relevant exact predicate, and returns a bounded verdict.

## Five-minute replay

Install the local checkout:

```bash
python -m pip install -e .
```

Verify a rational linear-system claim:

```bash
ecv verify examples/linear-valid.json
```

The command exits `0` and emits one canonical JSON line containing:

```json
{"claim_kind":"unique-solution","derived":{"equations":2,"rank_augmented":2,"rank_matrix":2,"residual_matches":true,"solution":["2","1"],"variables":2},"domain":"rational-linear-system","errors":[],"format":"ECV_RESULT_V1","spec":"ECV/1","verdict":"EXACTLY_VERIFIED_IN_DOMAIN"}
```

A mathematically false claim is not an input error:

```bash
ecv verify examples/polynomial-refuted.json
```

It exits `1` with `REFUTED_IN_DOMAIN`. An unsupported but well-formed domain or unmet supported-domain precondition exits `1` with `ABSTAIN_OUT_OF_DOMAIN`. Malformed input exits `2` with `INVALID_INPUT`.

## Supported domains in v0.1

| Domain | Claim kind | Exact check |
|---|---|---|
| `rational-linear-system` | `unique-solution` | Recomputes `A*x = b`, `rank(A)`, and `rank([A|b])` over canonical rational numbers. |
| `integer-polynomial-identity` | `identity` | Normalizes both structured polynomial ASTs over `Z[x1,...,xn]` and compares their coefficient maps. |
| `modular-arithmetic` | `crt-solution` | Checks a canonical solution against pairwise-coprime congruences and derives the uniqueness modulus. |

The normative contract is [ECV specification v1](spec/ECV_SPEC_V1.md).

## Input is structured, not executable text

Top-level documents contain exactly `spec`, `domain`, and `claim`:

```json
{
  "spec": "ECV/1",
  "domain": "rational-linear-system",
  "claim": {
    "kind": "unique-solution",
    "matrix": [["2", "1"], ["1", "-1"]],
    "rhs": ["5", "1"],
    "solution": ["2", "1"]
  }
}
```

Integers and rationals are strings. Canonical examples are `"0"`, `"-7"`, and `"3/5"`. Values such as `"01"`, `"2/4"`, `"1/-2"`, floats, and a zero denominator are rejected before calculation.

Polynomial claims use a JSON AST with only these operations:

- `{"op":"const","value":"..."}`
- `{"op":"var","name":"x"}`
- `{"op":"add","args":[...]}`
- `{"op":"mul","args":[...]}`
- `{"op":"neg","arg":...}`
- `{"op":"pow","arg":...,"exponent":...}`

There is no expression tokenizer, `eval`, plugin dispatch, network access, solver subprocess, or hidden registry.

## Verdict model

| Verdict | CLI exit | Meaning |
|---|---:|---|
| `EXACTLY_VERIFIED_IN_DOMAIN` | 0 | The declared predicate recomputed true under the supported domain contract. |
| `REFUTED_IN_DOMAIN` | 1 | The declared predicate recomputed false under that contract. |
| `ABSTAIN_OUT_OF_DOMAIN` | 1 | The domain or a required domain precondition is outside the checker contract. |
| `RESOURCE_LIMIT` | 1 | A declared deterministic safety ceiling prevented adjudication. |
| `INVALID_INPUT` | 2 | The JSON, schema, canonical representation, or claim shape is invalid. |

`EXACTLY_VERIFIED_IN_DOMAIN` is deliberately narrower than `PROVED`. It is not a universal theorem-prover verdict.

## What a verified result establishes

For the exact input bytes parsed by the CLI, it establishes that:

- the document passed strict JSON parsing, including duplicate-key and nonstandard-constant rejection;
- the claim passed the exact schema and canonical-value rules for its declared domain;
- the public checker recomputed the documented mathematical predicate using arbitrary-precision integers and `fractions.Fraction`;
- the result stayed within the declared verifier ceilings;
- the emitted `derived` fields came from that recomputation.

## What it does not establish

ECV does not establish that:

- a natural-language question was translated into the right formal claim;
- the supplied matrix, polynomial, congruences, or proposed solution describe the real-world object intended by an author;
- an input or result has a particular author, timestamp, provenance, or publication history;
- arbitrary mathematics outside the three documented v0.1 domains is true;
- the Python runtime, operating system, or hardware is uncompromised.

For byte integrity, inventory, and external root pinning, compose ECV with [Verifiable Evidence Capsule](https://github.com/alecstecpe-oss/verifiable-evidence-capsule). VEC does not add mathematical truth; ECV does not add provenance. Their claims remain separate.

## Resource ceilings

ECV v0.1 enforces deterministic in-process ceilings, including:

- input files: 1 MiB;
- JSON nesting: 256 container levels;
- integer components: 1,024 decimal digits;
- intermediate integer/rational components: 4,096 bits;
- rational matrices: at most 64 by 64;
- polynomial variables: 1 to 8;
- polynomial AST depth: 128;
- polynomial AST nodes: 2,048 per side;
- normalized polynomial terms: 10,000;
- polynomial exponent: 0 through 64;
- CRT congruences: 1 through 128.

These are application-level checks, not operating-system CPU or memory quotas. See [the threat model](docs/THREAT_MODEL.md).

## Python API

```python
from exact_claim_verifier import verify_document

result = verify_document(document)
if result["verdict"] == "EXACTLY_VERIFIED_IN_DOMAIN":
    print(result["derived"])
```

The Python API expects a JSON-compatible object. The CLI is the strict byte-to-result reference path.

## Design lineage and disclosure boundary

ECV was extracted as a clean, standalone trust kernel from a broader governed symbolic-computation design. The public ideas carried into this package are:

1. declare the mathematical domain before evaluation;
2. use canonical exact representations, never silent floating point;
3. dispatch to a small decidable checker rather than a universal narrative engine;
4. derive evidence and verdicts by replay;
5. abstain when the checker lacks authority.

Everything that can change an ECV verdict is in this repository. The package contains no South runtime, model, prompt, dataset, private ontology, search heuristic, orchestration layer, memory, hardware integration, or certificate producer. ECV has no runtime dependency on South.

## Development

```bash
python -m pip install -e ".[dev]"
ruff format --check src tests
ruff check src tests
pytest
python -m build
```

The suite includes exact positive and negative predicates, malformed/canonicalization attacks, strict-JSON attacks, resource-boundary cases, and CLI traceback regressions. The release process also installs and replays the built wheel in an isolated environment.

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before contributing or reporting a vulnerability.

## License

MIT. See [LICENSE](LICENSE).
