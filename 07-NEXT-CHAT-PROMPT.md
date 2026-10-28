# Implementation handoff prompt

Copy the text below into a new coding chat that can access the repository, or attach the handoff package and paste it. The repository contains specifications, not an implemented platform. It is separate from the application and automation repositories that future generation jobs will process.

---

Implement the framework-adaptive test-generation platform specified in this repository:

https://github.com/Darshil-Papalkar/automation-suite-design

Read `README.md`, `01-REQUIREMENTS.md`, `02-HLD.md`, `03-LLD.md`, `04-TECHNOLOGY-AND-SOURCES.md`, `05-IMPLEMENTATION-PLAN.md`, `06-ACCEPTANCE-AND-EVALS.md`, `contracts/` and `examples/` before implementation. Preserve these documents. If I provide an existing implementation repository, use it and follow its conventions. Otherwise scaffold the platform under `implementation/` in this design repository, following the layout in the implementation plan.

The product must read a bounded request, Jira title/description/acceptance criteria, relevant Confluence requirements, one or more application repositories, and an automation repository. It must discover the actual framework and project structure, inspect existing coverage, plan missing scenarios, generate tests using the existing fixtures/helpers/conventions, execute and diagnose them in isolation, repair only generated-test defects, and deliver a traceable patch or authorized draft PR. Do not require the requester to manually specify the framework. Do not replace the existing framework with one preferred by the agent.

Use the baseline architecture unless repository evidence justifies an explicit ADR: Python, FastAPI/Pydantic, PostgreSQL/SQLAlchemy/Alembic, Temporal as the only durable workflow authority, immutable artifact storage, a provider-neutral model adapter, and isolated target runners. Start with exact/syntax/lexical retrieval and add vector retrieval only with measured benefit. The target repositories may use other languages. Implement pytest and TypeScript Playwright Test vertical slices before claiming framework adaptation; qualify additional adapters separately. Do not claim arbitrary frameworks work automatically.

Execute milestones M0–M7 in order, parallelizing independent modules after contracts stabilize. Begin by inspecting the repository and scaffolding a running local control plane plus a complete pytest vertical slice; then complete the Playwright slice, live connectors, Git/CI integration, evaluation and hardening. Continue implementation and verification rather than stopping after a plan or empty scaffold. Maintain a requirement-to-implementation/test mapping.

Enforce these invariants:

1. Expected behavior comes from resolved requirements/contracts/approved invariants. Current application behavior does not automatically define correctness.
2. Freeze oracle revisions before generation. Repair cannot weaken assertions, add skips, broaden tolerances, change expected outcomes or modify application behavior merely to pass.
3. Treat all repository execution, including installation, imports and collection, as untrusted. Control-plane credentials and publication tokens never enter target runners.
4. Job lifecycle, requirement accounting, test execution and quality outcome are separate. No skipped, uncollected, mocked or unexecuted test is reported as validated coverage.
5. A correct failing test may expose a product defect; retain it and distinguish suspected from independently confirmed defects.
6. Keep exact source, commit, runtime, application-build, plan/oracle and patch identities. Revalidate after relevant changes.
7. Side effects are idempotent through persisted intent and reconciliation; a timeout does not justify blindly creating another PR or rerunning a potentially destructive external action.
8. Existing CI must be qualified for safely running generated code before publication triggers it. Never infer CI safety from local sandbox safety.
9. Missing credentials do not prevent building offline fixtures and connector contracts, but fixture tests cannot establish live integration or production readiness.
10. Publication and environment access follow project/user policy; there is no default permission to merge, deploy, access production, or post Jira comments.

Use the machine-readable contracts as a baseline and keep schemas, API behavior and documentation synchronized. Validate semantic invariants in application code; JSON shape validation alone is insufficient. Use current compatible supported dependencies, pin lockfiles and image digests, and record model/prompt versions. Recheck official tool/API documentation because the design research date is 28 October 2026.

Use synthetic fixtures and recorded model responses for deterministic orchestration/security tests. Also run real-model generation and actual target test runners to evaluate generation quality when authorized provider access is available. Implement the AT acceptance scenarios and report every relevant result, including gaps, denominators and skipped checks. Do not claim success from fake providers alone.

Create and continuously update:

- `implementation/docs/implementation-status.md`: requirement IDs, milestone progress, verified behavior, exact commands/results and known gaps.
- `implementation/docs/decisions.md`: substantive design changes and reasons.
- `implementation/docs/next-steps.md`: the next executable work items and external prerequisites.

When organization-specific information is missing, use clearly labeled local-development defaults and continue independent work. Request only information needed for a real blocked integration, such as deployment type, repository access, model account, source field mappings, environment build identity or publication policy. Do not invent organization details or credentials.

At completion provide runnable code, setup instructions, locked dependencies, migrations, API/domain schemas, adapter conformance tests, real execution evidence for both required framework families, CI integration, benchmark reports, runbooks and the remaining supported/unsupported capability matrix. If external access prevents part of this, state exactly what remains unverified while completing all independent work.

---

Suggested first user-supplied information, when available: implementation destination, Jira/Confluence Cloud or Data Center, application/automation repository URLs, model-provider restrictions, test-environment inventory, allowed publication mode, and data-handling requirements. These are deployment inputs, not assumptions already answered by this design.
