# ECV conformance corpus

`ECV_CONFORMANCE_V1.json` defines byte-exact test vectors for independent ECV implementations.

Each case binds:

- the input path and SHA-256;
- the expected canonical `ECV_RESULT_V1` bytes and SHA-256;
- the expected process exit code;
- the expected bounded verdict.

The corpus covers `ECV/1` and `ECV/2` plus all five verdict classes. It is a finite interoperability suite, not an exhaustive proof of implementation correctness.

Run the Python reference implementation:

```bash
python tools/run_conformance.py conformance -- ecv verify
```

Run another implementation by replacing `ecv verify` with a command that accepts the input path as its final argument and emits exactly one canonical result line on stdout with no stderr.

Do not regenerate `expected/` during ordinary tests. `tools/build_conformance.py` is a maintainer tool used only when a normative contract change intentionally updates the corpus.
