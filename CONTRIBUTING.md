# Contributing

Thank you for improving Exact Claim Verifier.

## Development setup

```bash
python -m pip install -e ".[dev]"
ruff format --check src tests tools
ruff check src tests tools
pytest
python -m build
```

## Trust-kernel rules

A change that can alter a verdict must:

1. update the normative specification when semantics change;
2. include positive, negative, malformed, and boundary tests as applicable;
3. preserve exact arithmetic and avoid floating point;
4. reject unknown semantics rather than guessing;
5. keep expected failures machine-readable and traceback-free;
6. add no runtime dependency without explicit security justification.
7. run boundary tests with `PYTHONINTMAXSTRDIGITS=640`.
8. add or update conformance vectors when a numbered public contract changes.

New domains should be small and decidable, with an independently reviewable predicate. Expanding mathematical authority requires a new numbered `ECV/N` contract rather than silently widening an existing contract. Natural-language parsers, network calls, plugin execution, and hidden registries do not belong in the verifier TCB.

For suspected vulnerabilities, use [SECURITY.md](SECURITY.md) instead of a public issue.
