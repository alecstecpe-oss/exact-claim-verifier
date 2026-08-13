# Security policy

## Supported versions

Exact Claim Verifier is alpha software.

| Version | Security fixes |
|---|---|
| 0.1.x | Yes |
| Earlier | No |

## Report a vulnerability

Use GitHub private vulnerability reporting:

<https://github.com/alecstecpe-oss/exact-claim-verifier/security/advisories/new>

Please include:

- the ECV and Python versions;
- the operating system;
- a minimal JSON document or script that reproduces the issue;
- the expected and observed verdict and exit code;
- whether the issue is a false verification, uncaught exception, schema ambiguity, or resource-ceiling bypass.

Do not include secrets or personal data. Please avoid publishing an exploit before a fix and advisory are available.

## Security boundary

ECV v0.1 verifies only the exact structured predicates in the three ECV/1 domains. It does not authenticate authors, validate natural-language formalization, prove real-world source data, impose OS resource quotas, or protect a compromised runtime.

Read [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) before security-sensitive use.

For release artifacts, verify both `SHA256SUMS.txt` and the GitHub artifact attestation. These checks bind bytes to the published build but do not establish mathematical truth beyond the declared ECV/1 predicate.
