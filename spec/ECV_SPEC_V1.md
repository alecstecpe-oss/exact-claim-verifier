# Exact Claim Verifier specification v1

Status: normative for `ECV/1` and `ECV_RESULT_V1` in package version 0.1.x.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as normative requirements.

## 1. Scope

ECV/1 defines a strict JSON envelope, three exact mathematical claim contracts, deterministic verdicts, and deterministic application-level ceilings. It does not define a natural-language formalizer, provenance system, signature format, or universal proof language.

## 2. Strict JSON input

The CLI MUST read at most 1,048,577 bytes and MUST return `RESOURCE_LIMIT` with `INPUT_BYTE_LIMIT` when the input exceeds 1,048,576 bytes.

The input MUST:

- be a regular file encoded as UTF-8;
- be valid JSON;
- contain no duplicate object key;
- contain no nonstandard `NaN`, `Infinity`, or `-Infinity` constant;
- have a top-level JSON object.

JSON array/object nesting MUST NOT exceed 256 container levels. JSON integer tokens above 1,024 digits and non-integer number tokens above 1,024 characters are invalid parser inputs. JSON numbers remain distinct from the string encodings required by the exact domains.

The top-level object MUST contain exactly:

```json
{"spec":"ECV/1","domain":"...","claim":{}}
```

Unknown or missing fields in closed ECV objects are invalid. Error paths use a JSONPath-like notation beginning with `$`.

## 3. Canonical exact values

### 3.1 Integers

An integer MUST be a JSON string matching:

```text
0 | -?[1-9][0-9]*
```

Therefore `-0`, `01`, `+1`, JSON number `1`, and JSON boolean `true` are invalid integer encodings. An integer component MUST NOT exceed 1,024 decimal digits, excluding a leading minus sign.

### 3.2 Rationals

A rational MUST be either a canonical integer string or `numerator/denominator`, where both components are canonical integer strings, the denominator is nonzero, and the whole value equals the reduced canonical rendering produced by:

- positive denominator;
- numerator and denominator divided by their greatest common divisor;
- omission of `/1`.

Examples: `0`, `-3`, `1/2`, `-1/2`. Nonexamples: `2/4`, `1/-2`, `0/7`, `1/0`.

## 4. Result envelope

Every checker result is an object containing exactly these semantic fields:

- `format`: `ECV_RESULT_V1`;
- `spec`: the accepted input spec or `null` for byte/parser failures;
- `domain`: the input domain or `null`;
- `claim_kind`: the input claim kind or `null`;
- `verdict`: one verdict from section 5;
- `derived`: an object of recomputed values;
- `errors`: an array of `{code,path,message}` objects.

The CLI serializes the result as one UTF-8 JSON line with keys sorted, no insignificant whitespace, and non-ASCII code points escaped.

## 5. Verdicts and exits

| Verdict | Exit | Condition |
|---|---:|---|
| `EXACTLY_VERIFIED_IN_DOMAIN` | 0 | The supported predicate recomputes true. |
| `REFUTED_IN_DOMAIN` | 1 | The supported predicate recomputes false. |
| `ABSTAIN_OUT_OF_DOMAIN` | 1 | The domain or a supported-domain precondition is outside authority. |
| `RESOURCE_LIMIT` | 1 | A deterministic checker ceiling prevents adjudication. |
| `INVALID_INPUT` | 2 | The bytes, JSON, schema, or canonical encoding are invalid. |

An unknown, validly shaped domain MUST produce `ABSTAIN_OUT_OF_DOMAIN`, not `INVALID_INPUT` and not a verified verdict.

## 6. Rational linear systems

Domain: `rational-linear-system`  
Claim kind: `unique-solution`

The claim object MUST contain exactly:

```json
{
  "kind":"unique-solution",
  "matrix":[["..."]],
  "rhs":["..."],
  "solution":["..."]
}
```

Requirements:

- `matrix` is a nonempty rectangular array with nonempty rows;
- every matrix, right-hand-side, and solution element is a canonical rational;
- `len(rhs)` equals the number of matrix rows;
- `len(solution)` equals the number of matrix columns;
- rows and columns MUST each be at most 64.

Let `A` be `matrix`, `b` be `rhs`, and `x` be `solution`. The checker recomputes exact Gaussian-elimination ranks over rational numbers and the exact residual predicate `A*x == b`.

The verdict is `EXACTLY_VERIFIED_IN_DOMAIN` iff all are true:

```text
A*x == b
rank(A) == len(x)
rank([A|b]) == len(x)
```

Otherwise the verdict is `REFUTED_IN_DOMAIN`. `derived` includes equation/variable counts, both ranks, `residual_matches`, and the canonical solution.

## 7. Integer polynomial identities

Domain: `integer-polynomial-identity`  
Claim kind: `identity`

The claim object MUST contain exactly:

```json
{
  "kind":"identity",
  "variables":["x"],
  "left":{},
  "right":{}
}
```

`variables` MUST contain 1 to 8 unique names matching `[A-Za-z][A-Za-z0-9_]{0,31}`.

A polynomial node is exactly one of:

```json
{"op":"const","value":"canonical integer"}
{"op":"var","name":"declared_name"}
{"op":"add","args":["one or more nodes"]}
{"op":"mul","args":["one or more nodes"]}
{"op":"neg","arg":"node"}
{"op":"pow","arg":"node","exponent":0}
```

The illustrative strings `node` and `one or more nodes` above stand for nested JSON objects, not literal accepted values. `exponent` MUST be a JSON integer from 0 through 64; JSON booleans are not integers for this rule.

Both sides are expanded into exact sparse coefficient maps over the ordered variable list. The verdict is `EXACTLY_VERIFIED_IN_DOMAIN` iff the two maps are equal, otherwise `REFUTED_IN_DOMAIN`. `derived` includes both canonical normal forms.

Per side, the AST is limited to depth 128 and 2,048 visited nodes. A normalized polynomial is limited to 10,000 nonzero terms.

## 8. Pairwise-coprime CRT solutions

Domain: `modular-arithmetic`  
Claim kind: `crt-solution`

The claim object MUST contain exactly:

```json
{
  "kind":"crt-solution",
  "congruences":[{"residue":"2","modulus":"3"}],
  "solution":"2"
}
```

Requirements:

- 1 to 128 congruences;
- each congruence contains exactly `residue` and `modulus`;
- both are canonical integer strings;
- each modulus is greater than 1;
- each residue is canonical modulo its modulus: `0 <= residue < modulus`;
- all moduli are pairwise coprime.

Non-pairwise-coprime moduli produce `ABSTAIN_OUT_OF_DOMAIN` with `DOMAIN_PRECONDITION_NOT_MET`; ECV/1 does not adjudicate generalized CRT.

Let `M` be the product of all moduli. The proposed solution MUST satisfy `0 <= solution < M`; otherwise the input is noncanonical. The verdict is `EXACTLY_VERIFIED_IN_DOMAIN` iff every congruence `solution mod modulus == residue` holds, otherwise `REFUTED_IN_DOMAIN`. `derived` includes all canonical values and `M` as `uniqueness_modulus`.

## 9. Intermediate-result ceilings

Each supplied integer component is limited to 1,024 decimal digits. In addition:

- intermediate integer results are limited to 4,096 bits;
- every intermediate rational numerator and denominator is limited to 4,096 bits.

Crossing a ceiling produces `RESOURCE_LIMIT`. These checks are deterministic application-level boundaries, not OS-enforced CPU/memory quotas.

## 10. Security and semantic boundary

A verified ECV result is valid only for the structured claim and declared domain contract. ECV/1 makes no claim about:

- natural-language-to-formal-claim equivalence;
- truth or provenance of real-world source data;
- authorship, signatures, timestamps, or confidentiality;
- arbitrary mathematics outside sections 6 through 8;
- integrity of the host Python runtime, standard library, OS, or hardware.

Implementations MUST NOT relabel `ABSTAIN_OUT_OF_DOMAIN`, `RESOURCE_LIMIT`, or `INVALID_INPUT` as proof.
