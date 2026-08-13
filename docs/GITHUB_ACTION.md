# GitHub Action

The repository root is a composite GitHub Action. Pin it to a release tag or commit and require the exact verdict your workflow accepts:

```yaml
- name: Verify exact claim
  id: ecv
  uses: alecstecpe-oss/exact-claim-verifier@v0.2.0
  with:
    document: claims/optimality.json
    expected-verdict: EXACTLY_VERIFIED_IN_DOMAIN
```

The Action installs the pinned checkout with no runtime dependencies, runs the reference CLI, checks that process exit and verdict agree, and fails unless the observed verdict exactly equals `expected-verdict`.

Negative evidence can be asserted explicitly:

```yaml
- uses: alecstecpe-oss/exact-claim-verifier@v0.2.0
  with:
    document: tests/known-false.json
    expected-verdict: REFUTED_IN_DOMAIN
```

Outputs:

- `verdict`: the exact bounded verdict;
- `result-path`: path to the canonical one-line `ECV_RESULT_V1` JSON (default `ecv-result.json`).

The full result is written to a file rather than `$GITHUB_OUTPUT`, whose size is bounded by GitHub Actions.

The Action does not authenticate the input or prove that a formal claim matches external intent. Pinning a commit protects against tag movement but does not create independent build or runtime trust.
