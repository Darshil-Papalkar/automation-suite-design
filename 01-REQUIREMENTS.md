# Product requirements and workflow

Version 1.0 — 28 October 2026.

This is a proposed specification for implementation. It does not report measured results or imply that a framework, model, connector, or environment has already been validated. Quantitative targets below are initial engineering targets to confirm in a pilot.

## 1. Product objective and boundaries

Build a framework-adaptive system that consumes a bounded request, Jira issue content, approved Confluence specifications, selected application repositories, and an existing automation repository. It discovers the applicable test framework and conventions, identifies existing coverage, plans missing scenarios, edits the automation project, and returns a reviewable Git change with requirement traceability and execution evidence.

The system is successful when it produces maintainable, requirement-correct tests in the right project structure and honestly reports the evidence available. A passing runner alone is not proof of correct requirements coverage. A failing test can be a correct result when it demonstrates a product defect; it must retain its expected behavior and be classified and reviewed accordingly.

### In scope

- Unit, component, integration, contract, API, and UI scenarios when supported by the repository and execution environment.
- Multiple application repositories and an independently versioned automation repository.
- Existing suites with substantial coverage, sparse suites, and automation repositories with configured frameworks but no tests.
- Limited onboarding for an absent or unfamiliar framework, governed by an explicit capability contract.
- Source retrieval, structured plans, code patches, isolated validation, bounded repair, draft pull requests, and reviewer evidence.
- Re-running a request after requirement changes without duplicating generated suites.

### Out of scope by default

- Production data access, production mutations, destructive tests, load tests against shared systems, or unrestricted network access.
- Changing application behavior to make generated tests pass.
- Automatically resolving ambiguous business rules by imitating current code.
- Automatically merging a PR, deploying changes, or marking a Jira item complete.
- Claiming universal framework support before its discovery, runner, and validation capabilities have been verified.
- Replacing domain experts for business-rule conflicts or environment owners for unavailable dependencies.

### Mandatory MVP capability slice

The first complete implementation must demonstrate both Python/pytest and TypeScript/Playwright, including a browser UI scenario. This prevents the framework-independent claim from resting on one language or only unit tests. Additional adapters are phased extensions. The core workflow and artifact schemas must not embed pytest- or Playwright-specific assumptions; adapter implementations translate framework-specific collection, execution, fixtures, and results.

## 2. Actors, inputs, and deliverables

| Actor | Responsibility |
|---|---|
| Requester | Supplies desired scope, allowed repositories, requirements references, target branch/build, and execution constraints |
| Repository owner | Defines conventions, reusable infrastructure, permitted modifications, and review rules |
| Requirement owner | Resolves source conflicts and missing expected outcomes |
| Platform operator | Operates workers, model endpoints, connector credentials, policy, retention, and budgets |
| Reviewer | Reviews generated tests, classifies suspected product defects, and decides whether to merge |

Required request inputs are an automation repository, one or more requirement references or attached snapshots, and a target scope. Application repository access is preferred; if missing, the system may operate against approved interface contracts but must label the resulting coverage limitations. Execution credentials and environment availability are prerequisites for verified runtime results, not prerequisites for producing an unverified draft.

Required output bundle: source/version manifest, repository profile, requirement specification, coverage and scenario plan, Git patch or branch, validation report, requirement-to-test traceability matrix, execution logs with redaction, artifact checksums, and unresolved issues. A draft PR is created only when the project integration and request policy authorize it.

## 3. Use cases

| ID | Scenario | Expected behavior |
|---|---|---|
| UC-01 | Add scenarios to a populated automation repository | Reuse its framework, fixtures, naming, directory structure, data conventions, and runner |
| UC-02 | Existing tests partially cover a new Jira issue | Map actual assertions, extend existing tests where appropriate, generate only missing coverage |
| UC-03 | Framework configured, no tests | Verify a minimal discovery/execution probe, then create tests within the existing scaffold |
| UC-04 | No framework or scaffold exists | Propose an explicit onboarding decision using repository/organization evidence; require a configured policy or owner decision where selection is ambiguous |
| UC-05 | Unfamiliar framework or custom runner | Inspect and propose an adapter; enable execution only after the adapter contract passes; return a marked draft if verification is unavailable |
| UC-06 | Feature spans services in several repositories | Resolve service and contract versions and verify environment alignment before claiming cross-service validation |
| UC-07 | Jira and Confluence disagree | Apply configured field-specific source precedence; block only the unresolved scenarios and continue independent work |
| UC-08 | A generated test reveals a product defect | Preserve the assertion, attach reproducible evidence, report a candidate defect, and avoid weakening the test |
| UC-09 | Test environment is unavailable | Complete independent analysis and generation, publish an unverified/partial result, record the missing dependency |
| UC-10 | Request or worker retries | Resume from the last safe checkpoint without duplicate commits, suites, or PRs |
| UC-11 | Requirement or branch changes during generation | Detect drift, recompute impacted stages, and invalidate obsolete validation evidence |
| UC-12 | A user requests an unsupported/destructive test | Apply declared capability and execution policy; explain the unsupported or restricted action without silently expanding scope |

## 4. Functional requirements

The acceptance conditions below are implementation contracts. “Must” means required for the production path, and “should” denotes a recommended default that may be changed by an explicit project policy.

| ID | Requirement | Testable acceptance condition |
|---|---|---|
| FR-01 | Accept a typed, bounded generation request | Reject requests missing repository/scope/requirements references; store a normalized request, tenant, actor, idempotency key, and policy version |
| FR-02 | Preserve source access permissions | A request by a principal without access to a Jira issue, Confluence page, or repository cannot retrieve or infer its content through direct reads, cached retrieval, or generated output |
| FR-03 | Snapshot all inputs | Manifest contains source IDs, retrieval times, Jira update/version markers, Confluence page versions, repository commit SHAs, dependency lockfile hashes, and target environment build identifiers when available |
| FR-04 | Discover framework and conventions per module | Detect language/framework/build system, candidate test roots, naming/tag rules, fixtures, helpers, data lifecycle, CI jobs, and exact collection/execution commands with evidence locations and confidence |
| FR-05 | Verify discovered capabilities | The adapter can collect a known baseline suite and parse a representative result; unsupported collection/execution capabilities are explicit rather than guessed |
| FR-06 | Support sparse, empty, and unknown setups | Distinguish configured/no-tests from no-framework and unknown-framework; run the relevant onboarding path and never declare runtime validation from a fabricated runner command |
| FR-07 | Establish an immutable baseline | Store baseline commit, commands, collected test IDs, pass/fail/skip counts, known failures, and environment identity before modifications; if baseline cannot run, label it unavailable |
| FR-08 | Normalize requirements | Each acceptance criterion has a stable ID, source/version references, preconditions, action, expected result, applicability, ambiguity flags, and an approved interpretation if clarified |
| FR-09 | Resolve or expose source conflicts | Use organization/project precedence rules; unresolved contradictions produce a scenario-level blocker containing conflicting excerpts and a precise question |
| FR-10 | Retrieve relevant evidence with provenance | Context bundles identify retrieved files/symbols, source versions, filters, and selection rationale; every bundle observes tenant/repository authorization filters |
| FR-11 | Assess existing coverage by behavior | Coverage mapping records concrete test IDs and assertions supporting a criterion; name similarity without inspected assertions is marked only as a candidate match |
| FR-12 | Produce a structured scenario plan | Every in-scope criterion has one disposition: sufficiently covered, extend existing test, new test, blocked, excluded with approved reason, or not automatically verifiable |
| FR-13 | Choose an appropriate test layer | Each scenario records its chosen layer and reason, applicable existing test infrastructure, boundary conditions, data, and required integration points |
| FR-14 | Ground expected outcomes | Every material assertion traces to authoritative requirements, an approved contract, or a documented invariant; the system distinguishes specification-derived assertions from implementation characterization |
| FR-15 | Generate repository-native patches | New files, helpers, tags, imports, and suite registration obey the discovered conventions; planned helpers/selectors/APIs are checked for existence or created explicitly |
| FR-16 | Bound modification scope | Default writable scope is the automation project and approved test support files; application code, dependency upgrades, CI changes, generated baselines, and credentials require explicit scope policy |
| FR-17 | Make repeated requests idempotent | Stable scenario lineage and Git fingerprints prevent duplicate tests; changed requirements update or supersede previous scenarios with a recorded relationship |
| FR-18 | Validate discovery and execution | Run static checks, collection, generated tests, and affected regressions as available; verify the generated test IDs actually executed and do not count skipped/xfail/quarantined tests as passed |
| FR-19 | Classify failures before repair | Each failure is classified as generated test, suspected product defect, environment, baseline, requirement ambiguity, unsupported capability, or unknown, with evidence and confidence |
| FR-20 | Repair generated artifacts with bounded attempts | Default maximum is three repair attempts per scenario group, subject to token/time budgets; never remove assertions, reduce requirement coverage, broaden tolerances, introduce skips, or alter expected results solely to pass |
| FR-21 | Preserve defect-revealing tests | If the candidate test follows a resolved requirement and failure is reproducible, retain it and produce a candidate-defect report; a reviewer or independent evidence confirms the product-defect classification |
| FR-22 | Handle multi-repository alignment | Before cross-service claims, verify code/contract/build compatibility and environment identifiers; unknown alignment is reflected in validation status and the report |
| FR-23 | Support checkpoints and cancellation | A worker restart resumes the recorded stage; cancellation stops new work, interrupts cancellable jobs, cleans temporary credentials/workspaces, and preserves completed artifacts |
| FR-24 | Produce reviewable Git integration | Commits/PRs include requirement mapping, source/build versions, generated test IDs, checks, failing cases, and limitations; retried publication returns the existing PR instead of a duplicate |
| FR-25 | Detect source and target drift | Before publication, compare target branch and requirement versions against the snapshot; if changed, recompute impacted plans/patches and rerun checks affected by rebasing |
| FR-26 | Record audit and model evidence | Persist actor, stage, inputs/outputs hashes, model/version, prompt template version, tool decisions, policy denials, run costs, and validation artifacts without storing unredacted secrets |
| FR-27 | Support source updates and revocation | Updated/deleted documents invalidate indexes and caches; revoked access is enforced before retrieval and generation even when old artifacts remain under permitted retention |
| FR-28 | Separate generation from approval/publication | Policy determines whether a draft, branch, or draft PR may be created automatically; merge/deploy requires a separate authorization boundary |
| FR-29 | Demonstrate the MVP across languages and layers | The acceptance suite completes real collection/execution for a Python/pytest fixture and a TypeScript/Playwright browser fixture; both use the same core request/workflow/artifact contracts |
| FR-30 | Qualify remote CI execution | Generated-head CI uses isolated runners and scoped credentials; unsafe/unknown privileged execution blocks auto-publication and produces artifact-only delivery |

## 5. Workflow and state machine

The LLD defines the canonical lifecycle, stage and quality enums. Lifecycle is independent of quality: `COMPLETED` means processing and delivery finished; it does not imply passing tests or full scope coverage. PostgreSQL stores an idempotently updated read model of the authoritative Temporal workflow. No second process independently changes workflow progression.

| Ordered stage | Work | Required evidence / exception |
|---|---|---|
| AUTHORIZE | Validate request identity, source/target entitlements, quotas, publication and runner policies | Normalized request and immutable project policy revision; reject unauthorized input |
| SNAPSHOT | Capture documents and resolve repository refs | Immutable source manifest, ACL references and content hashes |
| DISCOVER | Inspect relevant modules, framework/configuration, helpers and CI commands | RepositoryProfile and qualified adapter; otherwise onboarding decision or explicitly unverified draft |
| BASELINE | Prepare sandbox, collect and run selected existing tests | Comparable baseline or explicit unavailable/empty baseline result |
| NORMALIZE | Extract criteria, normative behavior and conflicts | RequirementSpec; block only unresolved dependent scenarios |
| RETRIEVE | Retrieve relevant contracts, implementation, examples and actual existing assertions | Cited evidence bundle and existing coverage mapping |
| PLAN | Select scenarios, layer, test data, target paths, dependencies and assertions | Validated TestPlan and frozen AssertionOracle revisions; WAITING_REVIEW only if policy requires |
| GENERATE | Apply bounded changes to disposable automation checkout | Patch and assertion map referencing frozen plan/oracle |
| VALIDATE | Check scope, syntax, imports, test discovery, generated tests and relevant regressions | Normalized results bound to patch and environment hashes |
| DIAGNOSE | Compare results with oracle and baseline | Failure findings distinguish test errors, product defects, environment issues and unknowns |
| REPAIR | Correct eligible generated defects within budget | New patch revision with unchanged expected behavior; return to VALIDATE |
| REVIEW | Assess traceability, oracle fidelity, defects, reliability and remaining scope | ValidationReport and exact-revision review decisions when required |
| FRESHNESS | Recheck permissions, source versions, branch and validated tree | Invalidate affected artifacts on drift; replan/revalidate before verified publication |
| PUBLISH | Reconcile and create authorized artifact, branch or draft PR | Persist external IDs and content/tree hashes; no duplicate publication |
| CI | Observe configured CI gates for the exact published head | WAITING_CI while pending; failed/missing checks are visible; artifact-only jobs can mark CI not applicable |
| CLEANUP | Revoke leases/credentials and remove ephemeral compute/data | Retained evidence plus cleanup status; orphan-resource sweeper retries failures |

Lifecycle states: `QUEUED`, `RUNNING`, `WAITING_INPUT`, `WAITING_ENVIRONMENT`, `WAITING_REVIEW`, `READY_TO_PUBLISH`, `PUBLISHING`, `WAITING_CI`, `CANCELLING`, `COMPLETED`, `FAILED`, `CANCELLED`.

Quality outcomes: `UNASSESSED`, `VERIFIED`, `VERIFIED_DEFECT_EXPOSING`, `SUSPECTED_PRODUCT_DEFECT`, `PARTIAL`, `BLOCKED`, `UNVERIFIED`, `REJECTED`. The LLD defines their aggregation rules. A confirmed defect-exposing test can satisfy generation while failing a passing-CI merge gate. A suspected defect remains a candidate until adjudicated. Blocks, skips and missing validations never count as verified automated coverage.

Waiting states persist exact scenario, required decision/dependency, owner, artifact revision, resume prerequisites and expiry. Independent scenario groups continue first. Waiting holds no active runner; wait duration is separate from active execution budget. A terminal job is not resumed: create a linked successor job using prior immutable evidence where still valid.

Plan scenarios as a dependency DAG. Shared fixtures/setup have one writer. Independent groups use separate workspaces; serialize consolidation and validate the combined patch. Use isolated test namespaces/data or serialize groups sharing mutable state. A failed prerequisite blocks only dependent groups.

## 6. Nonfunctional requirements and initial targets

These targets are proposals for a pilot under a stated reference workload: a request with at most 10 acceptance criteria, 3 application repositories plus 1 automation repository, cached repository indexes, and generated-test runtime below 15 minutes. Larger repositories and slow UI suites require separate capacity classes. LLM and external service latency are observable dependencies; targets must be revised from measurements.

| ID | Requirement | Proposed initial acceptance target |
|---|---|---|
| NFR-01 | Durable job control | No acknowledged job lost during orchestrator/worker restart in fault-injection tests; checkpoint before externally visible side effects |
| NFR-02 | Submission responsiveness | p95 submission acknowledgement ≤2 seconds excluding user authentication redirect; processing is asynchronous |
| NFR-03 | Planning latency | p95 first reviewable plan ≤10 minutes for the reference workload with warm indexes; report cold-index timing separately |
| NFR-04 | Job latency | p95 completed draft ≤45 minutes for reference workload excluding human waits, environment outages, and test runtime beyond 15 minutes; do not guarantee arbitrary UI-suite completion |
| NFR-05 | Availability | Initial control-plane target 99.5% monthly excluding agreed maintenance; dependency degradation is visible rather than masked |
| NFR-06 | Cost control | Every job has configured money/token/tool/runtime caps; stop starting new paid activities at cap, with a bounded in-flight allowance stated in policy |
| NFR-07 | Isolation | Zero cross-tenant retrieval or execution access in the authorization test matrix; all tenant content queries carry enforced tenant and entitlement filters |
| NFR-08 | Cancellation | Stop scheduling within 5 seconds; terminate interruptible worker activities within 30 seconds; disclose non-interruptible external requests |
| NFR-09 | Observability | Every activity carries job/tenant/correlation identifiers; stage duration, failures, model usage, retries, and queue delay are measurable |
| NFR-10 | Artifact integrity | All delivered artifacts have content hashes and source lineage; executed patch hash equals delivered patch hash or validation is invalidated |
| NFR-11 | Reproducibility | Replay same snapshots, pinned dependencies, environment image, and committed tests without invoking the LLM; acknowledge that live systems and model generation can be nondeterministic |
| NFR-12 | Budgeted concurrency | Per-tenant and global limits for running jobs, workers, model calls, and target environment sessions; backpressure is explicit |
| NFR-13 | Retention and deletion | Retention is policy-configured by artifact class; deletion/revocation tested across primary storage, indexes, caches, and backups according to documented windows |
| NFR-14 | Disaster recovery | Proposed initial metadata RPO ≤15 minutes and RTO ≤4 hours; validate through restore drill before promising them |
| NFR-15 | Portability | A new framework adapter can be registered without altering requirement planning and orchestration domain logic |
| NFR-16 | Quality transparency | Every run reports denominators, skips, unavailable checks, blocked criteria, and uncertainty; no fabricated pass/coverage claims |

## 7. Security threat model, controls, and verification

Threat boundaries: requester to API; connector to retrieval/index; source text to model; model to tool executor; repository/generated code to sandbox; sandbox to application environment; worker to credentials/artifact store; tenant to shared infrastructure; publisher to Git host. The model is not an authorization authority. Deterministic policy and credentials constrain tool execution.

| Threat | Required control | Verification scenario |
|---|---|---|
| Cross-tenant or cross-project retrieval | Tenant partitioning plus source ACL/entitlement enforcement at ingestion and query; revocation-aware caches | Same semantic query from two principals returns only their permitted documents; revoke access and repeat against warmed cache |
| Prompt injection in Jira, Confluence, repository files, tool output, or logs | Treat external content as evidence; separate policies from retrieved text; allowlisted structured tools; authorization checked outside model | Seed a page/comment/README that asks the agent to exfiltrate credentials or change scope; confirm denied action and normal requirement processing |
| Arbitrary code execution from test code or package scripts | Ephemeral worker isolation, resource quotas, read-only base image, bounded writable workspace, no host socket, no privileged mode, scoped network | Malicious install/postinstall/test attempts host-file access, container escape prerequisites, infinite process spawning, and forbidden outbound calls; verify containment |
| Secret leakage to model/logs/patches | Short-lived scoped credentials injected only at execution, secret scanning/redaction, no secrets in prompts, minimum retention | Seed canary secret into environment/logs; verify it never appears in prompt capture, indexed data, patch, or deliverable |
| Source-code exfiltration | Approved model providers/endpoints and data policies, egress allowlist, bounded tool destinations | Source text instructs outbound upload; unauthorized destination fails and is audited |
| Destructive tests or production mutation | Environment inventory and allowlist; default non-production; operation-level capability policy and scoped accounts | Test proposes deleting shared data or points at production hostname; block before execution |
| Dependency/supply-chain abuse | Honor lockfiles, trusted registries, dependency provenance checks, explicit install policy, approved images | Dependency swap or unexpected install script cannot gain broader permissions; changed dependency lock requires review policy |
| PR tampering or validation mismatch | Immutable artifact hashes, commit provenance, check-to-patch linkage, drift revalidation | Modify patch after checks; publishing refuses verified status until affected checks rerun |
| Duplicate mutations after network timeout | Idempotency keys, unique job/publication constraints, external reconciliation | Git API response lost after PR creation; retry finds existing PR rather than creating another |
| Budget abuse and denial of service | Quotas, file/content limits, decompression limits, tool timeouts, cancellation, request rate limits | Huge generated logs, recursive tools, archive bombs, and timeout loops remain within quotas |
| Stored injection/XSS in reports | Escape untrusted excerpts and sanitize rendered HTML/links | Malicious Jira title/test log cannot execute script in the review UI |
| Artifact poisoning or unauthorized read | Encrypted storage, short-lived scoped download URLs, content hash verification, tenant access checks | Another tenant cannot access a guessed artifact ID; altered artifact hash is detected |
| Credential misuse by a generated command | Brokered tools receive task-scoped credentials only; command approval is based on policy and scope | Generated shell command cannot access connector refresh tokens or publish outside the allowed repo |
| Unapproved business-rule modification during repair | Assertion/oracle lineage checks; diff policy; reviewer gate for semantic changes | A failed test prompts weaker assertion, added skip, or broader tolerance; reject or require explicit requirement-backed change |

For mutually untrusted tenants, prefer stronger isolation than ordinary shared containers; select dedicated VMs or microVM-backed workers according to the deployment threat model. A container image by itself is not a security boundary against every hostile workload. Egress restrictions must be enforced at the network/runtime layer, not merely described in a prompt.

Do not index secrets or store full chain-of-thought. Retain concise decisions, cited evidence, tool actions, and structured reports needed for debugging and review. Separate audit access from general application access. Data residency, provider retention, and connector permission requirements are deployment decisions that must be resolved before real organizational data is processed.

The acceptance scenarios and evaluation plan are maintained in [06-ACCEPTANCE-AND-EVALS.md](06-ACCEPTANCE-AND-EVALS.md).



## 8. Definition of done for one generation request

1. Source versions, repository commits, environment identity, request scope, and policy are recorded.
2. All in-scope criteria have a disposition, and no unresolved criterion is silently counted as covered.
3. Planned tests are in the intended automation structure and reuse appropriate conventions and helpers.
4. The normal runner discovers generated tests; required checks ran against the delivered patch, or the exact missing validation is marked as a gap.
5. Assertions are grounded, meaningful, and retain required behavior throughout repairs.
6. Test results distinguish test defects, candidate/confirmed product defects, baseline failures, environment problems, and unknowns.
7. All in-scope tests required by the agreed plan are delivered, or the request is marked partial with explicit outstanding work.
8. The handoff contains the patch/PR, traceability, validation evidence, limitations, and next actions for unresolved items.
9. Temporary runtime resources and credentials are cleaned up; retained artifacts obey policy.

An accepted result may be verified-passing or verified-defect-exposing. A useful but unexecuted patch is a draft with gaps. No user-facing success message may collapse these distinct outcomes into “all tests complete and passing.”

## 9. Deployment decisions that must remain explicit

The implementation agent may develop locally with synthetic fixtures while these decisions are pending, but it must not invent organization-specific values or claim live integration:

- Jira/Confluence Cloud versus Data Center, allowed spaces/projects, and authentication method.
- Git provider, repositories, base branches, branch protection, and publication permissions.
- Model/provider allowlist, data residency and retention requirements, and spend budget.
- Expected tenant count, concurrency, repository sizes, test runtime distribution, and target availability.
- Test-environment inventory, sandbox access, secrets broker, approved network destinations, and production restrictions.
- Organization-specific requirement precedence, review rules, adapter approval, and dependency installation policy.
- Artifact retention/deletion windows, audit access, and incident response ownership.

The reference design should document defaults and provide configuration points for these choices. Absence of a real credential should not prevent building and testing connector interfaces using recorded synthetic fixtures; it does prevent claiming successful live authentication or end-to-end operation against the user's systems.

FR-30 applies to publication that triggers CI, including jobs with a validated local sandbox. Test it using AT-025.
