# ECV in the verification landscape

ECV is a narrow offline reference checker. Its individual algorithms—exact Gaussian elimination, polynomial normalization, CRT checking, and primal/dual LP optimality—are established mathematics. The contribution is the small public trust boundary around structured claims, canonical exact data, bounded authority, deterministic replay, and typed refusal.

| Tool class | Typical role | What it does better than ECV | What ECV deliberately optimizes |
|---|---|---|---|
| Computer algebra system (for example SymPy or SageMath) | Symbolic exploration and broad mathematical computation | Far wider function and domain coverage | A closed claim schema and bounded verdict rather than an open computation environment |
| SMT solver (for example Z3 or cvc5) | Search for models or prove unsatisfiability across expressive theories | General solving, theory combination, and mature performance | No solver subprocess, small standard-library runtime, and direct replay of a few exact predicates |
| Proof assistant (for example Lean, Coq, or Isabelle) | Author and kernel-check formal proofs | Much stronger formal expressiveness and theorem-level assurance | Low-integration-cost JSON gates for fixed predicates; no claim of comparable proof power |
| Proof checker (for example an Alethe checker such as Carcara) | Validate proof certificates emitted by a solver | Rich proof-trace validation and established proof formats | Smaller domain-specific certificates and an explicit five-way operational verdict model |
| ECV | Recompute a declared exact predicate or validate a small certificate | Auditability and deterministic integration within its declared domains | Refuses every claim outside explicit authority |

## When ECV is a good fit

Use ECV when an untrusted producer—an LLM, private optimizer, remote service, heuristic, or human—can emit a structured claim or witness and a downstream pipeline needs a small offline gate that recomputes the decision without trusting that producer.

## When ECV is not a good fit

Do not use ECV as a replacement for:

- mathematical exploration;
- general satisfiability or theorem proving;
- natural-language formalization;
- proof checking outside its numbered domains;
- provenance, signatures, timestamps, or artifact integrity.

The defensible comparison is audit cost and authority clarity, not breadth. Passing ECV does not imply that the same claim has been independently formalized or proved in a general proof assistant.
