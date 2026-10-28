# Implementation plan and delivery contract

Version 1.0 — 28 October 2026. Build the full approved scope in increments; do not equate a demo, mocked connector, or a generated folder with completion. This document defines work packages and objective exit criteria. Estimates depend on team capacity and target environments; no schedule guarantee is implied.

## 1. Implementation strategy

When continuing in the design repository, scaffold the platform under `implementation/` and preserve the design documents. If the user supplies an existing implementation repository, adapt its structure instead. The layout below is relative to that implementation root.

Build one modular platform with independently deployed API, orchestration workers and isolated runner workers. Keep business modules in one repository initially. Do not create a microservice for each LLM role. Temporal owns durable job progression. Activity handlers call application services and the bounded model/tool loop.

Support two distinct reference environments before claiming framework adaptation:

- Python/pytest for unit and local API/integration scenarios.
- TypeScript/Playwright Test for UI/API scenarios, including fixtures, page objects or equivalent project abstractions and project-specific test discovery.

Framework names are not supplied in generation requests in the adaptation acceptance cases. The system must discover them. A fixture-only local demo may be completed without external accounts, but live Jira/Confluence/Git integration and provider quality evaluation remain separate release gates.

## 2. Suggested repository layout

```text
framework-adaptive-test-agent/
  pyproject.toml
  uv.lock
  README.md
  .env.example
  compose.yaml
  src/testagent/
    api/                 # request handlers, auth, OpenAPI, status/events
    domain/              # typed artifacts, enums, invariants, errors
    workflows/           # deterministic Temporal workflows and signals
    activities/          # idempotent side-effect handlers
    services/            # ingestion, retrieval, planning, generation, validation
    connectors/          # fixtures, Jira Cloud, Confluence Cloud, Git providers
    adapters/            # test framework adapter registry and implementations
    execution/           # runner client, policies, manifests, artifact capture
    models/              # provider interfaces and live/recorded implementations
    persistence/         # SQL models, repositories, outbox
    observability/       # structured events, tracing, redaction
    cli/                 # job submission, status, review, artifact export
  migrations/
  schemas/               # generated domain JSON Schemas and API schema
  prompts/               # versioned roles, templates, schema mappings
  policies/              # test scope, command/network/data budgets
  runner-images/
    pytest/
    playwright/
  tests/
    unit/
    contract/
    integration/
    workflow/
    security/
    acceptance/
  benchmarks/
    manifests/
    fixtures/
    labels/              # access-separated held-out oracles
    reports/
  docs/
    architecture/
    runbooks/
    decisions/
  scripts/
```

Target repositories are job inputs, not checked into the platform repository except intentionally licensed synthetic benchmark fixtures. Runtime job workspaces and secret files are ignored. Tests generated for users go into their automation repositories according to detected conventions, never into a fixed platform template directory.

## 3. Milestones

### M0 — Bootstrap and close deployment assumptions

Implement:

- Repository setup, locked dependencies, migrations, formatting/type checking and CI.
- ADRs for orchestration, persistence, artifact storage, runner isolation and model-provider configuration.
- Pydantic domain contracts from the LLD, schema export and schema versioning rules.
- Environment configuration without embedded credentials. Explicit development/live modes.
- Configuration for source organization, Git host, allowed repositories, environments and model provider.
- Model capability probe and source connector access probe; do not require live secrets to run deterministic unit tests.

Exit evidence:

- Fresh checkout follows documented commands to start the local control plane.
- API health/readiness tests pass; schema and database migration checks run in CI.
- Dependency/runtime compatibility matrix and initial `implementation-status.md` exist.
- Unresolved organization-specific choices are documented; independent coding work continues.

### M1 — Durable skeleton and offline replay

Implement:

- Job creation, idempotency keys, status/event listing, cancellation and artifact listing.
- Temporal workflow with stubbed/recorded activities, wait-for-review behavior and typed failure outcomes.
- PostgreSQL job projection, versioned records, outbox dispatch, deduplicated events.
- Immutable artifact storage with checksums and ownership checks.
- Fixture connectors for Jira/Confluence-shaped documents and Git repositories.
- CLI for submit, status, review and export; minimal review UI is optional.

Exit evidence:

- Worker crash/restart resumes a job without losing review state or duplicating artifacts.
- Same idempotency key with different body is rejected; exact replay returns the original job.
- Cancellation stops further side effects and terminates active runners within the configured bound.
- Offline replay is explicitly labeled and cannot masquerade as live connector validation.

### M2 — Real repository discovery and baseline execution

Implement:

- Read-only snapshot creation and repository manifest with resolved commits.
- Static detection by manifests, dependencies, CI, framework configuration and module boundaries.
- pytest adapter: environment preparation, collection, scoped baseline, execution and result parsing.
- Isolated runner service with argv-based commands, resource limits and restricted egress.
- Existing-test/helper inventory, empty/sparse repository handling and profile evidence.
- Baseline fingerprints tied to dependency locks, runtime, application build, seed/data profile and selected tests.

Exit evidence:

- Detect pytest in differently organized fixture repositories without a supplied framework name.
- Discover existing fixtures and collection rules; reject unknown commands until verified.
- Correctly distinguish no tests, collection error, failing existing test and unavailable dependency.
- No repository code executes in API/orchestration processes.

### M3 — Requirement grounding and test planning

Implement:

- Requirement normalization preserving tables, criterion IDs, custom field mappings and source locations.
- Conflict detection and partial-scope progress rules.
- Exact/syntax retrieval and authorization filters; optional lexical document indexing.
- Existing coverage mapping with inspection of actual assertions.
- Structured TestPlan and AssertionOracle; source/risk references and test-layer selection.
- Review decision endpoint with plan hash and version binding.

Exit evidence:

- Conflict cases do not silently change expected behavior.
- Missing/unsupported attachments are visible, not silently omitted.
- Grounded plans identify covered/partial/missing scenarios correctly in the labeled fixtures.
- Malicious document instructions do not change tool permissions or test scope.

### M4 — Generation, repair and meaningful verification

Implement:

- Provider-neutral model interface and one real model-provider adapter.
- Role prompts for extraction, planning, authoring and review, plus semantic validation.
- Small patch generation reusing project helpers; path scope and diff checks.
- Import/compile/lint, collection, targeted test execution and selected regression validation.
- Failure classification, bounded repair and frozen-oracle enforcement.
- Assertion sensitivity checks on controlled faults or mutations for suitable examples.
- Validation report with honest passed/failed/blocked/unverified scenario accounting.

Exit evidence:

- Real model creates usable tests from synthetic requirements into actual target repositories.
- Correct test exposing a product defect remains failing and is reported appropriately.
- Repair fixes invalid imports/fixtures without deleting assertions or adding skip/xfail.
- Generated tests are discovered by normal project commands.
- Reports distinguish recorded-model tests from live-model benchmark results.

### M5 — Second framework and multi-repository support

Implement:

- TypeScript Playwright adapter with project selection, fixtures, reporter parsing, traces and controlled browser access.
- Multi-module detection and selection; preserve installed framework versions.
- Application-to-automation repository relationship mapping, contracts and environment build identity.
- Cross-service scenario planning with explicit available environment dependencies.
- Adapter conformance suite shared with pytest.

Exit evidence:

- Same job API succeeds on Python and TypeScript/UI projects without framework input.
- Generated UI tests use verified locators and relevant existing abstractions.
- A mixed monorepo chooses the correct module/framework or returns a specific ambiguity.
- An environment running a different application build cannot receive an unqualified validation claim.

### M6 — Live connectors, Git delivery and CI

Implement:

- Jira Cloud REST v3 connector including custom acceptance-criteria fields and linked issues.
- Confluence Cloud REST v2 connector with page revision, permissions, tables and linked-page bounds.
- OAuth/app authentication appropriate to the organization's installation model.
- GitHub provider adapter, branch ownership, PR creation/update and publication reconciliation.
- Read CI status/results through the provider adapter; compare current base/head with the validated patch.
- Access revalidation before retrieval/publication; stale requirement handling.

Exit evidence:

- Live authorized ticket/page snapshots lead to a reviewable PR in a test repository.
- Repeated publication attempt reconciles the existing remote branch/PR after a simulated timeout.
- Moved base branch causes rebase/revalidation or explicit stale status.
- Expired credentials and 429 responses are classified/retried within policy.
- No automatic merge, Jira commenting or issue creation is included without explicit configured authorization.

### M7 — Production hardening and release evaluation

Implement:

- Production runner isolation and network controls tested with adversarial fixtures.
- Tenant/source ACL enforcement, scoped credentials, artifact retention and redaction.
- Backups, restore drills, cleanup/reconciliation workers and operational runbooks.
- Per-tenant fairness, concurrency quotas, model budgets and operational dashboards.
- Benchmark evaluation and controlled model/prompt/adapter rollout.
- Organization-specific CI and environment integration; SLO load/failure tests.

Exit evidence:

- Acceptance and security suites in `06-ACCEPTANCE-AND-EVALS.md` pass at their required release stage.
- Quality results include denominators, unresolved cases, error bars where meaningful and reviewer findings.
- Dependency/license inventory and incident runbooks exist.
- Release report distinguishes implemented, tested, supported, unverified and deferred capabilities.

## 4. Work sequencing and parallel work

The contracts and state machine come first. Connector development, runner isolation, retrieval and benchmark fixtures can then proceed in parallel against those contracts. Generation must not begin before profile, oracle and patch constraints exist. Publication comes after validated artifacts. Use separate worker workspaces/branches; consolidate overlapping fixture/helper edits before running the combined regression suite.

## 5. Required development fixtures

Create small synthetic repositories with known behavior and independent labels:

1. pytest project with reusable fixtures, custom testpaths and existing partial coverage.
2. pytest project with no tests but configured framework.
3. Empty automation repository paired with an application: onboarding decision needed.
4. TypeScript Playwright project with page objects/fixtures, multiple projects and non-default naming.
5. Mixed monorepo with both test families.
6. Two application services plus separate automation repo and explicit contract/build mapping.
7. Product defect that a valid generated assertion must expose.
8. Existing flaky/pre-failing suite, missing service and missing credentials as separate variants.
9. Malicious source/README/test-output text, symlink traversal, secret canaries and forbidden egress.
10. Stale requirement, moved Git branch and duplicate-delivery fixtures.

Use realistic structured requirements and deterministic local services. Label fixture IDs and expected outcomes. Never present synthetic fixture performance as measured performance on the user's real repositories.

## 6. Provider and connector testing strategy

Use recorded responses for deterministic parser/orchestration testing, and live calls for provider-conformance and quality evaluation. Model responses must include malformed schema, refusal, timeout, usage-limit, invalid tool-call and incomplete-output cases. Connector tests must include pagination, deleted items, permission changes, timeouts and rate limits.

Retain sanitized fixtures, never live secrets or unapproved private data. Require fixture regeneration review when upstream API formats change. Keep schema conformance separate from semantic correctness.

## 7. Release checklist

A release is ready only when:

- Documented supported adapters pass conformance tests and the real execution benchmark.
- Critical invariants are enforced in code and exercised adversarially.
- Requirement-to-test traceability survives retries, review, publication and updates.
- Validated commands run under the intended runner isolation policy.
- Results accurately report scope, baseline, environment alignment and failure classification.
- A clean installation and rollback/restore procedure are exercised.
- External account access and environment provisioning needed for the deployment are verified.
- Implementation status contains actual commands/results and links to evidence.

A future implementation chat must not claim production readiness solely because unit tests with fake providers pass.

## 8. Continuity files the implementation chat must maintain

Create `docs/implementation-status.md`, `docs/decisions.md`, and `docs/next-steps.md` in the implementation repository. Update after each milestone with completed requirements, exact verification commands/results, remaining gaps, migrations, configuration assumptions and changed files. These files are the durable handoff if another chat continues the implementation.
