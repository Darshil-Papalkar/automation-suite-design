# Framework-adaptive AI test generation — implementation handoff

**Version 1.0 · 28 October 2026 · Status: design specification, not an implemented or validated platform.**

This package specifies a system that turns Jira/Confluence requirements and application code into useful tests inside an existing automation project. The agent discovers the framework, reuses the project structure and helpers, evaluates existing coverage, generates missing tests, executes them, and delivers a reviewable change with evidence.

The framework-independent core is paired with qualified execution adapters. The initial complete scope demonstrates Python/pytest and TypeScript/Playwright Test, including a browser test; further frameworks are extensible additions. “Any framework” is a discovery and onboarding goal, not an unverified universal capability claim.

## Read and use the package

| Document | Contents |
|---|---|
| [Requirements](01-REQUIREMENTS.md) | 30 functional requirements, 16 nonfunctional requirements, use cases, workflow, security controls and definition of done |
| [HLD](02-HLD.md) | Components, trust boundaries, deployment, retrieval, durability, scaling, Git/CI and technology decisions |
| [LLD](03-LLD.md) | APIs, lifecycle/outcomes, data model, artifact contracts, adapter protocol, algorithms, idempotency and recovery |
| [Technology and sources](04-TECHNOLOGY-AND-SOURCES.md) | Selected stack, current AI/testing techniques, tool options, sources and version policy |
| [Implementation plan](05-IMPLEMENTATION-PLAN.md) | M0–M7 milestones, repository layout, build sequence, fixtures and release evidence |
| [Acceptance and evaluation](06-ACCEPTANCE-AND-EVALS.md) | 25 end-to-end acceptance scenarios, benchmark design, metrics and proposed pilot gates |
| [Next-chat prompt](07-NEXT-CHAT-PROMPT.md) | Ready-to-paste instructions for a separate coding chat |
| [Domain schema](contracts/domain.schema.json) | Named JSON Schema definitions for requests and core artifacts |
| [OpenAPI](contracts/openapi.json) | Proposed HTTP interface and typed request/response views |
| [Examples](examples/README.md) | Synthetic requests, requirement, oracle and result examples |
| [Combined design](MASTER-DESIGN.md) | The prose documents in one file for uploading into another chat |

For another coding chat, provide access to this repository and paste `07-NEXT-CHAT-PROMPT.md`. If repository access is unavailable, attach the ZIP package or the combined design plus the contracts and examples. The implementation should start under `implementation/` unless you supply a different destination.

## Scope and assumptions

- Cloud-first reference integrations: Jira Cloud, Confluence Cloud and GitHub. Data Center and other Git hosts require separate configured adapters.
- One automation target repository per job; multiple application/contract repositories can supply context.
- Python control plane; target runtime and framework are discovered independently.
- Temporal is the sole durable workflow authority. PostgreSQL holds domain data and a status projection.
- Optional pgvector retrieval and additional model/agent roles are introduced through evaluation.
- Generated tests run in isolated environments. Publication also checks the target CI trust boundary.
- No automatic merge, deployment, product-code correction or production testing in the default scope.
- No real application repository, credentials, organization-specific policies or test environment were supplied for this design. No generated-suite performance has been measured.

## Authoritative contract rules

The requirements define required behavior; the LLD defines canonical field names, states and outcomes. Machine-readable contracts are the concrete starter interface baseline. Implementation must keep all three synchronized and record substantive changes in an ADR. A conflict is a specification defect to resolve explicitly, not permission to weaken requirements.

`COMPLETED` describes lifecycle only. Quality can be VERIFIED, VERIFIED_DEFECT_EXPOSING, SUSPECTED_PRODUCT_DEFECT, PARTIAL, BLOCKED, UNVERIFIED or REJECTED. Passing tests are not proof of correct requirements coverage; an appropriate failing test can expose a product defect.

The technology research was checked against official documentation and primary research on 28 October 2026. Links support tool capabilities; the selected architecture, budgets and thresholds are recommendations. Exact dependencies must be compatibility-tested and pinned during implementation.

## Verification of this package

Run `python3 scripts/validate_package.py` from this directory after installing the validation-only dependency with `python3 -m pip install -r requirements-validation.txt` in your chosen virtual environment. The check validates JSON syntax/schemas, example conformance, internal references, API references and required acceptance/requirement IDs. It does not run an implementation or prove the architecture's runtime behavior.

See [PACKAGE-VALIDATION.md](PACKAGE-VALIDATION.md) for the checks performed on the delivered version. `checksums.sha256` identifies the delivered source documents and contract files; Git provides the publication history.

After editing source documents, run `python3 scripts/build_package.py` to refresh the combined handoff and checksums, then run the validator.
