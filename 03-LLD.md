# Low-level design: framework-adaptive test-suite generation

This is a proposed implementation contract, not a claim that the system is already implemented or validated. The first production candidate supports Python pytest and TypeScript Playwright Test through explicit adapters. Other frameworks can be detected and reported; runtime-verified generation is unsupported until an adapter is implemented and qualified. An explicitly requested unverified draft may be produced when sufficient conventions and oracle evidence exist, with no claimed execution. Framework-independent orchestration does not imply universal framework support.

## 1. Service and package boundaries

Use Python for the control plane: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Temporal Python SDK, and an S3-compatible artifact store. Use ordinary Python services and typed provider-neutral LLM calls inside Temporal activities. Do not add a second durable orchestration engine in the initial implementation. The TypeScript Playwright adapter runs Node commands inside the test sandbox; it does not require a TypeScript control plane.

Use the canonical package layout in [05-IMPLEMENTATION-PLAN.md](05-IMPLEMENTATION-PLAN.md). Domain modules live under `src/testagent/`; API, Temporal workers and runner workers are separate entry points/processes in that single codebase. The `schemas/`, `migrations/`, `prompts/`, `policies/`, `runner-images/`, `tests/` and `benchmarks/` directories remain separate. Module names in examples describe responsibilities, not a second repository layout.

The public API accepts identifiers and policy choices, never arbitrary terminal commands or access tokens. Secrets are referenced through configured connection IDs. The agent can request tools only from a capability set assigned to its activity; a model-generated action does not create permission.

## 2. HTTP contracts

User-facing resource endpoints require OIDC authentication and tenant-scoped authorization. Provider webhooks use provider-specific signature/authentication verification instead of OIDC. Every ID lookup must include `tenant_id`; object-storage URLs are short lived and issued only after authorization. User-facing mutating methods accept `Idempotency-Key`; provider webhooks deduplicate by verified connection and delivery ID. Return RFC 9457-style problem details with a stable application `code`, request ID, and safe diagnostics.

| Method and path | Behavior |
|---|---|
| `POST /v1/projects` | Register repository roles, connections, adapter policy, permitted environments, and publication policy. |
| `GET /v1/projects/{project_id}` | Return non-secret configuration and capability readiness. |
| `PATCH /v1/projects/{project_id}` | Create a new immutable configuration revision; do not mutate running-job configuration. |
| `POST /v1/projects/{project_id}/discovery-runs` | Detect frameworks, commands, candidate suite roots, and missing setup. No generation. |
| `GET /v1/discovery-runs/{discovery_run_id}` | Return profile and capability-verification results. |
| `POST /v1/source-snapshots` | Register a bounded attached requirement snapshot with provenance and original reference; validate size/type and store immutable bytes. |
| `GET /v1/jobs/{job_id}/blockers` | Return versioned questions/dependencies and affected scenarios. |
| `POST /v1/jobs/{job_id}/blockers/{blocker_id}/resolutions` | Submit an evidence-backed answer against the blocker revision; owner authorization and `If-Match` required. |
| `GET /v1/artifacts/{artifact_id}/download` | Return a short-lived authorized download reference, or stream local-development content. |
| `POST /v1/jobs` | Validate scope, persist job/outbox, and start durable work asynchronously; return `202`. |
| `GET /v1/jobs/{job_id}` | Return lifecycle state, current stage, quality outcome, blocker codes, and summary. |
| `GET /v1/jobs/{job_id}/events` | SSE events with monotonically increasing sequence IDs; support `Last-Event-ID`. |
| `GET /v1/jobs/{job_id}/requirements` | Return versioned requirement records and unresolved conflicts. |
| `GET /v1/jobs/{job_id}/test-plan` | Return scenario plan, coverage disposition, and assertion oracles. |
| `GET /v1/jobs/{job_id}/artifacts` | List authorized artifact metadata; individual download endpoint signs a URL. |
| `GET /v1/jobs/{job_id}/validation-report` | Return machine-readable checks, baseline comparisons, and unmet gates. |
| `GET /v1/jobs/{job_id}/reviews` | Return pending and completed review requests. |
| `POST /v1/jobs/{job_id}/reviews/{review_id}/decisions` | Resolve one exact artifact revision with decision and optional correction; `If-Match` guards stale decisions. |
| `POST /v1/jobs/{job_id}/resume` | Resume a waiting job after an identified dependency is resolved; includes expected blocker revision. |
| `POST /v1/jobs/{job_id}/cancel` | Signal cancellation, terminate active sandbox process, and clean up leases. |
| `POST /v1/jobs/{job_id}/publish` | Publish the validated artifact revision under project publication policy; `If-Match` required. |
| `GET /v1/jobs/{job_id}/pull-requests` | Return publication status and linked Git-provider PRs. |
| `POST /v1/webhooks/{provider}/{connection_id}` | Verify signature, deduplicate delivery, persist event, enqueue processing, return promptly. |

For routes whose provider uses different webhook authentication, implement the provider's verified mechanism; do not invent an HMAC requirement for every service. Webhooks may mark snapshots stale or update CI checks. They do not silently replace accepted requirements or initiate paid jobs unless a configured trigger permits it.

Example create request:

```json
{
  "project_id": "prj_checkout",
  "source_refs": [
    {"kind": "jira_issue", "connection_id": "conn_jira", "external_id": "PAY-241"},
    {"kind": "confluence_page", "connection_id": "conn_confluence", "external_id": "92417"}
  ],
  "repository_refs": [
    {"repository_id": "repo_backend", "ref": "main", "role": "application"},
    {"repository_id": "repo_tests", "ref": "main", "role": "automation"}
  ],
  "scope": {"suite_roots": ["tests/payments"], "test_layers": ["api"], "scenario_limit": 20},
  "environment_id": "env_ephemeral_checkout",
  "publication_mode": "draft_pr",
  "limits": {"wall_clock_seconds": 1800, "model_cost_usd": 10.0, "repair_attempts": 3}
}
```

Limits are illustrative initial guardrails, not measured capacity promises. The server applies the minimum of request limits and tenant/project limits. A caller cannot raise its own permissions or budgets. `draft_pr` is accepted only if project policy and caller scope authorize it; otherwise the request fails with an explicit policy error rather than silently escalating.

Example accepted response:

```json
{
  "job_id": "job_01JEXAMPLE",
  "state": "QUEUED",
  "stage": null,
  "quality_outcome": "UNASSESSED",
  "status_url": "/v1/jobs/job_01JEXAMPLE",
  "events_url": "/v1/jobs/job_01JEXAMPLE/events"
}
```

Repeated identical request/key returns the original response and job ID. Reusing the key with a different canonical request body returns `409 IDEMPOTENCY_KEY_REUSED`. Retain request idempotency records for a documented interval; use generation and publication uniqueness constraints to prevent duplicates after expiry.

## 3. Durable state machine

Separate lifecycle from test quality; a technically completed workflow may have discovered a product defect or produced only a partial result.

```text
JobState = QUEUED | RUNNING | WAITING_INPUT | WAITING_ENVIRONMENT |
           WAITING_REVIEW | READY_TO_PUBLISH | PUBLISHING | WAITING_CI |
           CANCELLING | COMPLETED | FAILED | CANCELLED

Stage = AUTHORIZE | SNAPSHOT | DISCOVER | BASELINE | NORMALIZE | RETRIEVE | PLAN |
        GENERATE | VALIDATE | DIAGNOSE | REPAIR | REVIEW | FRESHNESS | PUBLISH | CI | CLEANUP

QualityOutcome = UNASSESSED | VERIFIED | VERIFIED_DEFECT_EXPOSING | PARTIAL |
                 SUSPECTED_PRODUCT_DEFECT | BLOCKED | UNVERIFIED | REJECTED
```

`VERIFIED` means configured gates passed for the declared scope and evidence; it is not a guarantee of complete bug detection. `BLOCKED` means no usable test patch or qualified existing-coverage result can be produced because a required capability, authorization or requirement resolution is missing. A usable patch with insufficient execution evidence is UNVERIFIED instead. `COMPLETED/PARTIAL` is valid when the user receives the finished subset and explicit uncovered criteria. `FAILED` is reserved for unrecoverable orchestration/infrastructure failure or exhausted execution budget without a deliverable. Cancellation is terminal for that job; restarting creates a new job linked by `replaces_job_id`.

| Current state/event | Next state | Required behavior |
|---|---|---|
| `QUEUED` / admitted by tenant quota | `RUNNING` | Resolve source and repository refs to immutable versions. |
| `RUNNING` / critical requirement ambiguity | `WAITING_INPUT` | Persist exact question, affected scenarios, and evidence; independent scenarios may finish first. |
| `RUNNING` / environment dependency unavailable | `WAITING_ENVIRONMENT` | Record missing dependency and retry policy; preserve artifacts. |
| `RUNNING` / policy requires artifact review | `WAITING_REVIEW` | Freeze artifact hash; expose diff and validation evidence. |
| `WAITING_*` / valid resolution | `RUNNING` | Resume from a checkpoint; invalidate downstream artifacts if inputs changed. |
| `RUNNING` / validated deliverable, manual publication | `READY_TO_PUBLISH` | Return downloadable patch and complete report. |
| `RUNNING` or `READY_TO_PUBLISH` / authorized publication | `PUBLISHING` | Recheck authorization, remote head, source freshness, and artifact hash. |
| `PUBLISHING` / external effect verified | `WAITING_CI` or `COMPLETED` | Persist external IDs; wait if CI gates are required, otherwise finish with applicable limitations. |
| `WAITING_CI` / generated-code failure with repair budget | `RUNNING` at DIAGNOSE | Diagnose/repair, revalidate, recheck freshness, update the same PR and wait for checks on the new head. |
| `WAITING_CI` / checks settled and no repair eligible, or deadline | `COMPLETED` | Aggregate exact-head evidence and gaps; failed/timed-out checks never become passed. |
| `RUNNING` / artifact-only mode finished | `COMPLETED` | Return artifacts; do not require publication to finish. |
| Any nonterminal state / cancel | `CANCELLING` then `CANCELLED` | Stop processes and cleanup; preserve audit records. |
| Any running state / unrecoverable error | `FAILED` | Preserve evidence and indicate whether an external effect may have occurred. |

Use a deterministic Temporal workflow for branching, timers, waits, and retry decisions. Network calls, Git access, model inference, sandbox execution, and database mutations are activities. Persist large artifacts in object storage and pass immutable references through workflow history. Heartbeat long-running activities and check cancellation. A bounded inference activity can manage a short agent tool loop, but every tool invocation is separately audited and budget checked.

An approval/correction resolves a `ReviewRequest` with an artifact revision. Corrections create a new artifact revision and invalidate dependent plans, patches, and reports. A reviewer cannot approve a stale revision by accident.

### Outcome aggregation and CI completion

Apply summary rules in this order, while retaining every scenario-level finding:

1. Policy/review rejection => REJECTED. No deliverable and missing prerequisites => BLOCKED. Infrastructure lifecycle FAILED remains distinct from quality.
2. If the request has a usable patch or inspected existing coverage but no sufficiently validated scenario, use UNVERIFIED, unless the entire exercised scope meets the candidate-defect criteria below.
3. If some scenarios are adequately validated and others remain blocked, unverified or missing, use PARTIAL. Do not count blocked criteria as passing merely because their disposition is recorded.
4. For fully exercised/resolved scope with oracle-supported application contradictions awaiting adjudication, use SUSPECTED_PRODUCT_DEFECT.
5. For fully exercised/resolved scope with independently confirmed defects and passing artifact/oracle/traceability gates, use VERIFIED_DEFECT_EXPOSING. Relevant test/CI failure remains failed; generation quality and merge eligibility are separate. This outcome cannot override a required green-CI merge policy.
6. For complete declared scope satisfying configured passing validation gates, use VERIFIED.

`UNASSESSED` applies before assessment. Failure findings, criterion dispositions, check results and `merge_eligible` remain separate facts; a single enum never replaces those details. An unknown failure explanation cannot become a confirmed defect.

For all-existing-coverage/no-change jobs, VERIFIED requires inspected assertion evidence and the configured validation gates; no PR is required. Record `delivery_kind=no_change`. For no-change jobs, required CI results are queried for the pinned automation base commit; unavailable relevant checks are a gap, and no dummy PR is created. A required CI gate pending after publication keeps lifecycle WAITING_CI; a timeout yields an explicit missing-check result and PARTIAL/UNVERIFIED outcome. Optional CI observation can continue after completion as a separate monitor, without retroactively rewriting the immutable report. Publish a new report revision for new evidence. Completion fraction is criterion accounting, not runtime coverage.

## 4. Persistence model

Use UUIDv7 or an equivalent sortable opaque ID internally; external examples above use readable aliases. Store timestamps in UTC and render in the user's timezone. Binary artifacts and large logs belong in object storage; database rows retain hashes, URI, media type, size, ACL scope, and expiry.

| Entity | Essential fields / constraints |
|---|---|
| `tenants` | `id`, policy revision, quotas, retention policy. |
| `projects` / `project_revisions` | Tenant, immutable versioned repository/environment/publication configuration. |
| `connections` | Provider, tenant, secret reference, allowed resource scopes, health; no access token in rows exposed to agents. |
| `repositories` | Provider ID, URL, role, permitted refs and path scopes. |
| `jobs` | Tenant/project/config revision, lifecycle state, stage, quality outcome, limits, request principal, generation key, optimistic row version. |
| `job_input_snapshots` | Immutable manifest, content hash, resolved revisions, ACL snapshot reference, environment fingerprint. |
| `source_documents` / `source_chunks` | External ID/version, text hash, source link, heading/anchor, tenant/project ACL scope, embedding model/version. |
| `repository_profiles` | Job/repository/module, schema version, detected adapter version, evidence and verified commands. |
| `requirement_specs` | Job, stable criterion key, revision, normalized behavior, source refs, conflict status. |
| `test_plans` / `scenarios` | Revision, coverage disposition, oracle refs, target paths, generation status. |
| `assertion_oracles` | Immutable revision/hash, assertion descriptions, structured predicates, evidence refs, review status. |
| `patches` | Base commits, file operations, diff hash, scenario mapping, generated commit. |
| `execution_runs` / `test_results` | Phase, environment fingerprint, command ID, attempt, test ID, outcome, duration, failure signature, report artifact. |
| `validation_reports` | Artifact revision, gate results, baseline diff, unresolved criteria, quality outcome. |
| `review_requests` / `review_decisions` | Type, artifact hash, status, actor, rationale, decision timestamps. |
| `publications` | Repository, generation key, branch, commit, provider PR ID, state and reconciliation status. |
| `job_events` / `audit_events` | Monotonic sequence, event type, safe payload, actor, trace ID. |
| `idempotency_records` / `webhook_deliveries` | Unique tenant/key or provider connection/delivery ID; payload hash. |
| `outbox_events` | Committed with business state, processed idempotently by dispatcher. |
| `leases` | Tenant/repository/branch scope, owner, expiry, fencing token. |

Enforce tenant filtering in the application and database policy where feasible. Retrieval queries apply ACL predicates before ranking, including vector search. Cached chunks and evidence bundles are scoped to the same authorization context; a shared vector index must never return an unauthorized chunk to the model.

## 5. Shared contract envelope

Every generated artifact has:

```json
{
  "schema_version": "1.0",
  "artifact_id": "art_...",
  "revision": 1,
  "job_id": "job_...",
  "created_at": "2026-10-28T09:00:00Z",
  "input_manifest_sha256": "...",
  "parent_artifact_hashes": ["..."],
  "content_sha256": "...",
  "producer": {"component": "planner", "version": "0.1.0"}
}
```

Serialize using canonical JSON before hashing. Source references include `source_id`, exact revision, content hash, paragraph/heading or file/line range, and human-readable URL. File/line evidence is always anchored to a commit. Model outputs are parsed against Pydantic schemas, validated semantically, and rejected on unknown properties. Schema validity alone does not establish factual correctness.

### SourceSnapshotManifest and ExecutionManifest

The following is a conceptual combined view. Persist the source and execution parts separately as specified in section 13; `InputManifest` is an umbrella term, not a third mutable object.

```text
InputManifest
  project_config_revision
  repositories[]: repository_id, role, requested_ref, resolved_commit_sha,
                  submodule_commits, lockfile_hashes, sparse_checkout_paths
  sources[]: source_id, kind, requested_reference, resolved_revision,
             updated_at, content_sha256, acl_scope_reference
  environment: environment_id, application_builds[], sandbox_image_digest,
               runtime_versions, service_image_digests[], config_digest,
               feature_flag_digest, test_data_revision, region_or_locality
  tooling: adapter_versions, generator_version, retrieval_config_version,
           policy_revision, prompt_template_hashes, model_config_ids
  request: scope, principal_reference, budget_limits
```

Do not hash raw low-entropy secret values; fingerprints contain non-secret configuration and secret version identifiers where permitted. An environment fingerprint is useful only if the deployment/build identity is actually observable. If it is unknown, record `unknown` and lower verification status rather than manufacturing reproducibility.

### RepositoryProfile

```text
RepositoryProfile
  repository_id, commit_sha, module_root
  framework_candidates[]: name, version, evidence_refs[], status
  selected_adapter: adapter_id, adapter_version, capabilities
  runtimes[], package_manager, lockfiles[], dependency_policy
  test_roots[], naming_patterns[], test_layers[]
  fixtures[], helpers[], page_objects[], api_clients[], factories[]
  abstraction_ref: symbol, file_path, commit_sha, signature, usage_examples[]
  commands: prepare_command_id, collect_command_id, run_command_id,
            static_check_command_ids[], format_command_id
  suite_registration: discovery_rules[], explicit_manifests[], CI_jobs[]
  lifecycle: setup_refs[], teardown_refs[], test_data_strategy
  execution_readiness: ready | dependency_missing | unsupported | unverified
  detected_evidence[], verified_probes[], unresolved_items[]
```

`framework_candidates` are evidence-backed hypotheses; only a successful collect/probe establishes executable adapter readiness. Multiple modules may have different profiles. Existing wrapper commands such as `make test-api` or an npm script take precedence when they are verified and policy approved.

### RequirementSpec

```text
RequirementSpec
  requirement_id, stable_criterion_key, revision
  title, normative_statement
  source_refs[], authority_resolution
  actor, preconditions[], action, expected_outcomes[]
  boundaries[], permissions[], state_transitions[], failure_behaviors[]
  scope: services[], feature_flags[], supported_versions[]
  status: resolved | ambiguous | conflicting | not_testable | out_of_scope
  questions[]: question_id, text, evidence_refs[], affected_scenarios[]
  assumptions[]: text, provenance, approval_status
```

Authority precedence is project configuration, not a hard-coded “Jira always wins” rule. An acceptance criterion may reference a normative Confluence section. Preserve both references. Existing implementation behavior may help identify interfaces but cannot silently override a normative expected outcome.

### TestPlan and AssertionOracle

```text
TestPlan
  plan_id, revision, profile_hashes[], requirement_hashes[]
  scenarios[]:
    scenario_id, stable_scenario_key, requirement_ids[]
    coverage_disposition: existing | extend_existing | new | blocked |
                          out_of_scope | not_automatable
    existing_test_refs[], coverage_reason
    layer: unit | component | integration | contract | api | ui | performance
    target_repository_id, target_suite_root, target_paths[]
    priority, preconditions[], data_requirements[], ordered_actions[]
    oracle_id, oracle_revision, oracle_sha256
    reusable_abstractions[], environment_dependencies[]
    cleanup_requirements[], estimated_execution_class, blockers[]
  criterion_dispositions[]: requirement_id, scenario_ids[], disposition, reason

AssertionOracle
  oracle_id, revision
  assertions[]:
    assertion_id, behavior_statement
    observable, comparison_operator, expected_value_or_invariant
    units_or_normalization, tolerance_policy, temporal_bound
    evidence_refs[], provenance: requirement | contract | approved_invariant
  prohibited_weakening[]
  review_state: policy_accepted | human_accepted | needs_resolution
  sha256
```

Not every assertion can use a tiny fixed expression language. Structured observable/predicate fields provide traceability; framework-native assertion code is still generated. The validator checks that code expresses the planned oracle and that it is exercised. Human-readable invariants require review when mechanical validation cannot establish equivalence.

An oracle is frozen before generation. The coding/repair activity has read access only to that revision. A legitimate oracle correction requires a new requirement/plan revision with evidence or authorized review, invalidates dependent validation, and triggers regeneration. Do not let the same repair call edit both the expectation and the implementation to make tests pass.

### PatchManifest

```text
PatchManifest
  patch_id, revision, plan_hash, input_manifest_hash
  repositories[]:
    repository_id, base_commit_sha
    file_changes[]: path, operation: add | modify | delete,
                    before_sha256, after_sha256, scenario_ids[], purpose
    unified_diff_artifact, diff_sha256
  dependency_changes[], suite_registration_changes[]
  assertion_map[]: assertion_id, generated_file, generated_symbol,
                   oracle_sha256
  forbidden_change_scan, generated_commit_sha
```

Default writable scope is the designated automation repository and approved test-support paths. New dependencies, fixture changes with broad impact, CI changes, or application changes are distinct policy decisions. A generation job does not gain permission to rewrite application behavior to satisfy a test.

### ValidationReport

```text
ValidationReport
  report_id, revision, patch_hash, plan_hash, environment_fingerprint
  quality_outcome, delivery_kind, merge_eligible, completion_fraction
  gates[]: gate_id, status: passed | failed | blocked | not_applicable,
           evidence_artifact_refs[], explanation
  collection: baseline_test_ids[], candidate_test_ids[], added[], removed[],
              generated_tests_collected[], registration_warnings[]
  baseline_comparison: new_failures[], persistent_failures[], resolved_failures[],
                       incomparable_results[], selection_differences[]
  runs[]: execution_run_id, phase, command_id, exit_code, result_summary,
          normalized_result_artifact_ref
  requirement_coverage[]: requirement_id, disposition, scenario_ids[], evidence
  oracle_review[], defect_sensitivity_evidence[], flakiness_evidence[]
  failure_findings[], uncovered_criteria[], verification_limitations[]
  repair_history[], publication_eligibility, publication_restrictions[]
```

Completion fraction counts dispositioned criteria; it must not be presented as passed-test percentage. Report blocked/out-of-scope criteria separately. A criterion linked to a test name is not automatically covered; assertion mapping and review evidence are required.

## 6. Adapter protocol and command execution

```python
from typing import Protocol

class FrameworkAdapter(Protocol):
    def detect(self, inventory: RepoInventory) -> DetectionResult: ...
    def profile(self, ctx: ReadOnlyRepoContext) -> RepositoryProfile: ...
    def prepare(self, ctx: SandboxContext, profile: RepositoryProfile) -> PrepareResult: ...
    def collect(self, ctx: SandboxContext, selection: TestSelection) -> CollectionResult: ...
    def run(self, ctx: SandboxContext, selection: TestSelection,
            run_policy: RunPolicy) -> ExecutionResult: ...
    def parse(self, artifacts: ExecutionArtifacts) -> NormalizedTestResults: ...
    def static_check(self, ctx: SandboxContext,
                     changed_paths: list[str]) -> CheckResult: ...
    def map_failure(self, result: NormalizedTestResult) -> FailureFinding: ...
```

Adapter capabilities are explicit and independently qualified:

```json
{
  "supports_collection": true,
  "supports_test_selection": true,
  "supports_machine_readable_results": true,
  "supports_coverage": true,
  "supports_mutation": false,
  "supports_parallel_workers": true,
  "supports_browser_artifacts": false,
  "supports_parameterized_test_ids": true,
  "requires_external_environment": false
}
```

Capabilities can be refined by repository profile. A framework supporting parallel execution does not make an existing suite safe to run in parallel. Unsupported optional capabilities return `not_applicable` with a reason. Unsupported required capabilities return `blocked`; neither can masquerade as a passed gate.

`CommandSpec` contains an executable, argument array, workspace-relative working directory, approved environment variable names, secret references, timeout, memory/CPU limits, network policy ID, and expected result artifacts. Execute with `shell=False`. Validate resolved paths, symlink targets, executable source, and arguments. Never execute a command copied directly from a requirement page or unrestricted model output. Repository scripts themselves are untrusted code and still run only in the sandbox.

Initial adapter implementation:

| Adapter | Detection evidence | Collection/results | Guardrails |
|---|---|---|---|
| pytest | `pyproject.toml`, pytest configuration, lockfiles, `conftest.py`, existing test imports | Prefer existing wrapper; otherwise `python -m pytest --collect-only` with a structured collection plugin and JUnit XML for outcomes | Respect existing fixtures, markers, async plugin, parameterization, configured test paths; avoid silently introducing plugins. |
| Playwright Test | `package.json`, lockfile, `playwright.config.*`, existing imports | Prefer existing npm/pnpm/yarn script; use Playwright list/JSON reporting through adapter where compatible | Reuse projects, fixtures, page objects, configured browsers and base URL; capture trace/screenshots per existing policy; do not replace stable waits with arbitrary sleeps. |

Do not treat output shown above as universal CLI invocation for all versions. The adapter must verify installed versions and use the installed tool's compatible options. Pin adapter fixture tests to supported version ranges. Future adapters may include JUnit/TestNG with Maven/Gradle and .NET xUnit/NUnit; qualification requires real example repositories and recovery tests.

## 7. Generation and repair algorithm

1. Resolve input versions; fetch only authorized sources and repositories.
2. Discover each relevant automation module and verify adapter readiness; prepare the isolated environment and establish the initial baseline.
3. Retrieve an evidence bundle per criterion: normative text, interfaces/contracts, representative existing tests and their transitive helpers, dependency facts, existing asserted coverage.
4. Normalize requirements, resolve precedence, and record missing expected outcomes. Produce a plan with explicit disposition for every criterion.
5. Freeze the plan and oracle revisions. Establish the baseline during BASELINE after discovery; extend its test selection now if planning reveals additional regression dependencies. Reuse only comparable baseline evidence.
6. Generate a minimal patch against the pinned automation base. Apply it only in a disposable checkout; enforce writable-path and dependency policies.
7. Collect tests again, run static checks, run generated/modified tests, and run the configured affected regression selection.
8. Compare expected versus actual behavior and baseline; classify failures using evidence. Review oracle-to-assertion correspondence and dangerous test shortcuts.
9. Repair only eligible generated-code defects, rerun affected validation, and stop at the attempt/time/cost limit. A repair cannot suppress or relax assertions, mark tests skipped, add unconditional retries, or alter application code without a separately authorized plan change.
10. Optionally run targeted negative controls/mutations in an isolated application copy. Restore/recreate the environment after each experiment; never mutate a shared or production service.
11. Build the final report, perform source/head freshness checks, and publish only under the configured policy.

Model calls return structured outputs. Keep requirement normalization, scenario planning, coding, and critical review as separate calls with role-specific context. An independent review pass uses the frozen oracle and patch, rather than accepting the generator's self-assessment. This reduces coupled mistakes but does not establish statistical independence or guarantee correctness.

## 8. Baseline, comparison, and failure semantics

Baseline is an execution artifact, not just a boolean. Record collection results, test IDs, exit codes, failure signatures, setup failures, skips, durations, application builds, feature flags, and data revision. Execute baseline and candidate against comparable application/environment state. Create isolated test data for both runs; a baseline run must not leave state that changes the candidate's expected result.

Stable test identity is `repository_id + module_root + framework + logical_test_path + test_symbol + normalized_parameter_identity`. Maintain framework-native IDs alongside canonical IDs. If parameter identities are dynamic or unstable, mark the comparison as uncertain rather than merging unrelated tests.

| Failure code | Evidence needed | Next action |
|---|---|---|
| `GENERATED_SYNTAX_OR_IMPORT` | Parser/compiler/import traceback in changed test files | Eligible for bounded repair. |
| `GENERATED_FIXTURE_OR_API_MISUSE` | Verified fixture/helper signature versus generated invocation | Eligible for bounded repair. |
| `ASSERTION_ORACLE_MISMATCH` | Generated predicate differs from frozen oracle | Repair test to oracle; preserve expected behavior. |
| `REQUIREMENT_AMBIGUITY` / `REQUIREMENT_CONFLICT` | Source references and conflicting/missing expected outcomes | Block affected scenarios; request resolution. |
| `ENVIRONMENT_UNAVAILABLE` / `AUTHENTICATION_UNAVAILABLE` | Health/setup/auth evidence | Retry transient failures or wait for environment action. |
| `TEST_DATA_OR_CLEANUP_FAILURE` | Fixture/data lifecycle evidence | Repair if generated support is responsible; otherwise environment issue. |
| `PREEXISTING_BASELINE_FAILURE` | Same comparable test failure on base | Report separately; block verification only if it invalidates the new test's evidence. |
| `SUSPECTED_PRODUCT_DEFECT` | Oracle-supported expectation, valid setup/action, observed application contradiction | Preserve failing test; surface suspected defect for triage. |
| `FLAKY_OR_NONDETERMINISTIC` | Inconsistent comparable repeats with recorded state | Diagnose isolation/timing; do not hide with retries. |
| `UNSUPPORTED_FRAMEWORK` | Missing qualified adapter or unavailable required capability | Complete discovery report; require onboarding. |
| `STALE_INPUTS` / `REMOTE_HEAD_CONFLICT` | Source revision or remote base changed | Regenerate/revalidate or ask for explicitly permitted stale publication. |
| `SECURITY_POLICY_VIOLATION` | Disallowed tool/path/network/dependency action | Reject action; retain audit evidence. |
| `BUDGET_EXHAUSTED` / `INTERNAL_ERROR` | Budget ledger or infrastructure diagnostics | Preserve partial artifacts; no false “verified” result. |

An assertion failure alone cannot establish a product defect: first check oracle fidelity, test setup, data, application build, and observable selection. When the evidence remains inconclusive, report `UNVERIFIED` with the competing explanations.

## 9. Idempotency, concurrency, and external effects

Use separate keys:

```text
request_key = tenant_id + caller-provided Idempotency-Key
generation_key = SHA256(project_id, normalized requested scope,
                        resolved application/test commits,
                        source revision/content hashes,
                        environment fingerprint, policy revision)
scenario_key = stable business criterion key + normalized behavior dimensions
execution_key = patch_hash + environment_fingerprint + selection_hash + phase
publication_key = target_repository_id + generation_key
```

The generation key identifies equivalent input work; model config and implementation versions remain in provenance. An intentional regeneration can specify a new `generation_revision`, linked to the earlier generation. Exact replays may reuse persisted outputs; do not promise identical LLM output from identical prompts.

Use an active-generation uniqueness constraint or atomic admission record to prevent simultaneous duplicates. Scope publication leases to the generated branch/PR, not the entire repository. Independent suites may generate concurrently, but overlapping target paths/base changes require a merge/revalidation decision. Leases include fencing tokens so an expired worker cannot publish after a newer owner acquires the lease.

Persist `publication_intent` before external Git operations. If a worker crashes after creating a branch or PR, reconciliation searches for the durable generation marker and records the existing effect. Never blindly retry “create PR” after an ambiguous timeout. Provider operations and webhook delivery are treated as at least once; application idempotency provides duplicate protection.

Use a transactional outbox between API persistence and Temporal dispatch. Workflow ID is derived from tenant/job ID. A retry of dispatch starts or retrieves that same workflow. Workflow progress is the orchestration source of truth; the database status read model is updated idempotently with monotonic event sequence/version checks.

## 10. Multi-repository and CI behavior

Map application services to their repositories, API contracts, deployment/build IDs, and target environments. If a suite spans services, freeze the tested service-version matrix. Checkout of source commit A does not prove the remote environment runs A.

The MVP writes to one automation repository per job; multiple application repositories are read-only context. A later release may create multiple coordinated test PRs. Separate repositories cannot be atomically merged by this system; each PR must carry compatibility/dependency information, and cross-repo gates must reference the intended version matrix.

Before publication, check the remote automation base. If it moved, either rebase the generated patch and rerun relevant gates or report a conflict. Never silently publish “verified” evidence from a different resulting tree. Recheck source revisions and mark a plan stale when requirements changed; do not overwrite old provenance.

CI should report distinct checks: `generation/traceability`, `generation/discovery`, `generation/static`, `generation/generated-tests`, and `generation/affected-regression`. Mutation and reliability checks are optional policy gates with explicit applicability. Existing CI remains authoritative for merge requirements. The system does not auto-merge in the initial scope.

## 11. Sandbox and credential boundary

The control plane retrieves approved snapshots and supplies a scoped workspace. The generation sandbox sees read-only application snapshots and writable automation paths; it does not receive Jira/Confluence tokens, Git publication credentials, or the host's environment.

Static file discovery may run in a restricted read-only parser process. Any dynamic discovery, test collection, imports, dependency installation, build, or test execution must run inside the sandbox because all can execute repository-controlled code. No trust exemption is granted to `collect-only`, package metadata commands, configuration loading, or test fixtures.

Use separate credential scopes for dependency retrieval, environment access, and publication. Install dependencies through approved registries/proxies and pinned lockfiles where available. Treat install/build hooks as code execution. Runtime egress defaults to denied except required registry/application endpoints; secrets are injected only to the activity needing them and redacted from logs/artifacts.

Local development can use disposable Docker containers with non-root users, resource limits, no privileged mode, no host Docker socket, and restricted mounts. For production workloads containing untrusted repositories, select and validate a stronger sandbox boundary such as microVMs or a hardened sandbox runtime. Kubernetes scheduling by itself is not a strong code-isolation boundary.

Use ephemeral namespaces/tenants and generated data IDs for stateful tests. Never run destructive scenarios on a shared production environment. This is an environment policy enforced by the execution service, not a prompt instruction to the LLM.

## 12. Operational behavior and acceptance tests

Track per-stage latency, queue wait, model tokens/cost, retrieval source usage, sandbox resource use, retry/repair count, generated-test collection, requirement disposition, failure category, reviewer edits, and accepted PR outcomes. Log artifact IDs, hashes, and traces; avoid raw secrets, sensitive fixture data, or full proprietary prompts by default. Record a sanitized prompt/template/config reference sufficient for controlled investigation.

Minimum implementation acceptance tests:

- Repeated create requests produce one job; mismatched idempotency payloads return 409.
- Worker termination during inference/execution/publication resumes without duplicate PRs or lost artifacts.
- Requirement corrections invalidate the old plan, patch, report, and any stale approval.
- A test with a passing but weakened assertion fails the oracle review gate.
- A correct failing test against a seeded product defect is retained and classified as suspected defect.
- Existing baseline failures are distinguished from generated failures when environments are comparable.
- A repository with no collected tests cannot be reported as successfully validated merely because a command exited zero.
- Added tests are collected through the repository's real suite mechanism, including registration files and tags.
- Retrieval cannot cross tenant/resource ACL boundaries; malicious document text cannot grant tool access.
- Unsupported frameworks return an onboarding report without fabricated run commands or successful results.
- Tests do not leak data across baseline/candidate jobs or parallel runs.
- Budget and cancellation signals stop tool execution and release sandbox resources.
- A remote head or requirement revision change invalidates stale verification before publication.
- Representative pytest API/unit and Playwright UI fixtures demonstrate correct placement, reuse of helpers, assertion fidelity, and normal runner execution.

Exact framework-version ranges, source precedence, environment access, deployment infrastructure, and acceptance thresholds must be finalized from the real repositories and organization policy. The contract above intentionally makes those inputs explicit so an implementation agent can build the system without pretending they are already known.

## 13. Persistence, hashing and invalidation details

The examples use readable IDs; implementations may generate UUIDv7/ULID internally. PostgreSQL constraints must include tenant ownership. At minimum implement these uniqueness rules:

```sql
-- Illustrative DDL; concrete migration types must match domain models.
CREATE UNIQUE INDEX uq_request_idempotency
  ON idempotency_records (tenant_id, operation, idempotency_key);
CREATE UNIQUE INDEX uq_workflow_event
  ON job_events (tenant_id, job_id, sequence_number);
CREATE UNIQUE INDEX uq_publication
  ON publications (tenant_id, target_repository_id, generation_key);
CREATE UNIQUE INDEX uq_webhook_delivery
  ON webhook_deliveries (connection_id, delivery_id);
CREATE UNIQUE INDEX uq_artifact_revision
  ON artifacts (tenant_id, logical_artifact_id, revision);
```

Add foreign keys for every artifact/review/scenario lineage and check tenant ownership at service boundaries. A unique publication record stores the remote-effect intent and reconciliation state; it does not itself make a remote API exactly-once. Workers must claim actions using compare-and-swap/row locking and use fencing tokens where an external broker supports them. A per-repository publication coordinator additionally serializes overlapping target-file or base-update operations; independent generation stays parallel.

Hash raw files and blobs over their exact bytes. For structured domain artifacts, hash canonical JSON of the `payload` only, excluding the envelope and `content_sha256` field. Use one canonicalization implementation and golden test vectors (UTF-8, deterministic key ordering, JSON number rules, no NaN/Infinity). Prefer RFC 8785-compatible canonicalization. Store immutable parent hashes and schema version in the envelope; validate referential lineage independently. A patch report binds both unified diff hash and resulting Git tree/commit identity because the same diff against a different base is not the same tested tree.

Separate manifests to avoid circular or mutable snapshots:

- `SourceSnapshotManifest`: fixed source/repository/request/configuration inputs captured at SNAPSHOT.
- `ExecutionManifest`: derived immutable revision after discovery/preparation, binding source snapshot, profile versions, commands, runner image, service builds, environment, test-data and feature flags.
- `ValidationReport`: binds source manifest, execution manifest, oracle/plan and candidate patch/tree. A newly discovered environment identity creates a new ExecutionManifest; it never edits an earlier snapshot in place.

The generic `input_manifest_sha256` in envelopes refers to the SourceSnapshotManifest. Model/tooling provenance and execution bindings live in their appropriate derived artifacts. Do not put future profile hashes into the source snapshot and then reference that snapshot from the same profiles.

For intentional regeneration, include `generation_revision` in the generation admission key. For execution deduplication use `(job_id, patch_hash, environment_fingerprint, selection_hash, phase, logical_repetition_index, experiment_id)`. A retry of the same logical execution reconciles its existing runner; a reliability rerun uses a new repetition index and isolated test-data namespace. Mutation/negative-control experiments use distinct experiment IDs. This prevents cached runs from falsely satisfying repeat-execution checks.

Invalidation rules:

| Change | Invalidate / recompute |
|---|---|
| Normative requirement or authority decision | Dependent RequirementSpec, oracle, plan, patch and validation |
| Target helper/configuration or automation base | Affected profile, plan placement, patch and regression checks |
| Application implementation with unchanged contract | Impact analysis, retrieval and applicable validation; revise oracle only if normative evidence changes |
| Environment image, service build, flags or data revision | Execution manifest, baseline comparability and candidate validation |
| Prompt/model/provider config | Future generation provenance; existing committed tests remain replayable without LLM |
| Entitlement revoked | Deny new use/download/publication; invalidate cached authorization, constrain existing derived artifacts by lineage |
| Patch changed after review | Invalidate affected checks and exact-revision review/publication authorization |

A cached model response is reusable only when input artifacts, model configuration, prompt/schema version, principal entitlements and policy match; cache use is recorded as such. Cache keys must not cross tenants or bypass fresh authorization.

## 14. Tool broker, context retrieval and role contracts

Expose a deliberately small tool surface per role:

| Role | Tools | Output |
|---|---|---|
| Requirement analyst | Read authorized source span, follow bounded approved source link | RequirementSpec with conflicts and provenance |
| Repository analyst | List files, read bounded file, exact search, symbol lookup; request sandbox profile probe | RepositoryProfile and evidence |
| Planner | Read source/profile/coverage evidence, retrieve helper signatures | TestPlan and AssertionOracle |
| Author | Read frozen plan/oracle and files; propose/apply scoped patch; request allowed static/targeted checks | PatchManifest and assertion map |
| Diagnoser/repairer | Read exact run logs/results and frozen oracle; patch permitted test artifacts | Classified finding or repaired patch |
| Reviewer | Read source evidence, plan, diff and results; request bounded verification | Gate findings; no permission to silently alter code/oracle |

Tool requests are typed records validated by the broker. Use bounded result sizes, path normalization and resolved symlink checks. No raw shell tool is exposed to the LLM. The execution broker may run a verified project script with approved arguments inside the sandbox. A legitimate script can still be hostile; sandbox isolation remains mandatory. The Git publisher is an application service, not an author-agent tool.

Retrieval algorithm defaults: filter by tenant/principal/resource entitlement and snapshot, exact identifiers first, lexical candidate search next, optional vector candidates, reciprocal-rank fusion if both exist, bounded reranking, then expand signatures/imports/fixture dependencies. These are configurable heuristics to calibrate, not universal optimal thresholds. Log selected evidence IDs, omitted-needed-evidence flags, query/ranking versions and token budgets. Preserve original source references when compacting context. Do not replace normative text with model summaries alone.

Prompts must include role goal, allowed tools, immutable artifact references, expected schema and explicit treatment of missing evidence. Ask for concise evidence-linked decisions rather than private chain-of-thought. When a stage cannot support its output, return typed gaps instead of invented symbols or business values.

## 15. Review and publication authorization

Review decisions identify `review_id`, artifact ID, revision, payload hash, reviewer identity, decision, and optional corrected requirement evidence. `If-Match` compares the current revision ETag. `approve` permits only the action named by the review type; it is not blanket permission for arbitrary future changes. `request_changes` creates a new revision and invalidates dependent approvals. Record policy-based automatic acceptance separately from human acceptance.

For external publication recheck: caller/project publish permission, current source use rights, permitted target audience/data policy, permitted paths, immutable approved/validated patch, target head, and remote publication ledger. Artifact provenance can include restrictive sources; do not paste confidential excerpts into a less-restricted repository. Prefer source links and approved summaries. Publication authorization is enforced outside the model.

PR contents: original request/scope; source snapshots; changed suites and helpers; criterion-to-scenario-to-test IDs; commands and environment identities; executed/skipped/failed counts; baseline comparison; confirmed/candidate defects; unavailable checks; exact tested tree; CI status; remaining decisions. Defect-exposing PRs remain draft or follow the repository's explicit policy; they are never falsely labeled passing.

## 16. Machine-readable companion contracts

`contracts/domain.schema.json` defines the starter canonical JSON shapes used by the supplied examples. `contracts/openapi.json` defines the API surface and shared request/status/review contracts. These are design contracts, not generated evidence of a running service. Implement the domain models, export schemas from them and maintain semantic equivalence with these documents. Add complete internal models and endpoint-specific views without silently relaxing the prescribed invariants.

The schema validates structure, enums and references; it cannot prove oracle correctness, real execution, source permission, hash integrity or correct scope. Those need the domain checks and acceptance tests specified above. Provider-facing schemas may be transformed to a supported subset; validate returned values against the full schema and semantic rules afterward.

## 17. Input resolution and attached snapshots

Attached snapshots use `POST /v1/source-snapshots` with `project_id`, `kind`, `original_reference`, `declared_source_revision`, `media_type` and bounded text content in the initial text-only API. Unsupported binary attachment extraction returns a typed limitation; a later upload adapter may add malware/size/type checks and asynchronous extraction. The server derives tenant/actor, content hash and capture time; it does not trust caller-supplied ACLs or checksums. Offline fixture snapshots are explicitly labeled synthetic. A snapshot ID may be used as a `source_ref` without live Atlassian credentials, but does not establish current live content or entitlement.

Blocker resolutions include `blocker_revision`, `resolution_type` (requirement_answer, environment_ready, adapter_qualified), `answer`, `evidence_refs` and optional selected policy/adapter IDs. The server checks that the actor may resolve that blocker. An environment_ready assertion triggers a real health/build probe, not immediate verified status. A requirement answer creates an immutable interpretation revision and downstream invalidation. Resume signals only an existing waiting workflow; terminal jobs require a linked successor job.

## 18. CI execution trust boundary

Before enabling publication that triggers CI, onboard the target CI configuration. Generated patches must execute with restricted tokens, no production secrets, isolated runners and approved network/environment scope. Do not run untrusted generated heads in privileged workflows or permit a `pull_request_target`-style trusted context to check out and execute the generated head with secrets. Repository CI workflow changes remain separately authorized. The publisher verifies the applicable policy and fails closed to artifact-only delivery if CI execution is unsafe or unknown.

Test this boundary with a malicious generated-test fixture: it must fail to read control-plane/production secrets, access host runtime sockets or reach forbidden destinations in the actual CI runner. Passing platform-sandbox checks alone does not qualify the remote CI environment. A remote test attempt with unknown outcome may have mutated data; reconcile its attempt namespace or discard the isolated environment before rerunning. Arbitrary external systems cannot be given an exactly-once mutation guarantee by this platform.

## 19. End-to-end interaction and error contract

```mermaid
sequenceDiagram
  participant U as Requester
  participant A as API
  participant D as Domain DB / outbox
  participant W as Temporal workflow
  participant C as Connector / reasoning activities
  participant R as Isolated runner
  participant G as Git / CI
  U->>A: POST job + idempotency key
  A->>D: Transaction: request, job, outbox
  A-->>U: 202 + job ID
  D->>W: Dispatcher starts stable workflow ID
  W->>C: Authorize, snapshot, discover
  C->>R: Prepare and baseline using verified commands
  R-->>C: Baseline + environment binding
  W->>C: Normalize, retrieve, plan and freeze oracle
  opt Review required by policy
    W-->>U: Exact-revision decision request
    U->>A: Decision + If-Match
    A->>W: Durable signal after authorization
  end
  loop Bounded generation and eligible repair
    W->>C: Generate or repair scoped patch
    C->>R: Static, collection, tests, regression
    R-->>C: Structured evidence
    C-->>W: Findings + immutable artifact references
  end
  W->>C: Oracle review, freshness, publication policy
  W->>G: Reconcile and create/update draft PR
  G-->>W: External identity, exact head
  G-->>A: Verified/deduplicated webhook
  A->>W: CI result signal
  alt Eligible failure found only in CI
    W->>C: Diagnose and repair within remaining budget
    C->>R: Revalidate new patch
    W->>G: Update same PR; observe new-head checks
  else Checks settled or budget exhausted
    W->>D: Idempotent report/status projection activity
  end
  W->>R: Revoke leases and cleanup
  U->>A: Read result/artifacts
  A-->>U: Outcome, traceability, failures and limitations
```

Arrows to domain storage represent activities or dispatchers; workflow code itself performs no database/network I/O. Webhook ingress persists an inbox/outbox event before acknowledging; a dispatcher signals the workflow and retries using the event ID. Polling reconciles missing webhook deliveries. Cleanup failure is visible and retried by a sweeper; it must not be hidden by a completed test report.

| HTTP status | Application codes / policy |
|---|---|
| 400 | MALFORMED_REQUEST, INVALID_SOURCE_REFERENCE |
| 401 | AUTHENTICATION_REQUIRED, TOKEN_INVALID |
| 403 | SOURCE_ACCESS_DENIED, PUBLICATION_DENIED, ENVIRONMENT_POLICY_DENIED |
| 404 | RESOURCE_NOT_FOUND; use consistent tenant-isolation policy to avoid resource enumeration |
| 409 | IDEMPOTENCY_KEY_REUSED, STALE_REVIEW, STALE_BLOCKER, INVALID_JOB_STATE, REMOTE_HEAD_CONFLICT |
| 413 | SNAPSHOT_TOO_LARGE, ARTIFACT_LIMIT_EXCEEDED |
| 422 | DOMAIN_VALIDATION_FAILED, UNSUPPORTED_REQUESTED_CAPABILITY |
| 429 | TENANT_QUOTA_EXCEEDED with bounded Retry-After where known |
| 503 | CONTROL_PLANE_UNAVAILABLE; accepted jobs record external-service failures in workflow rather than holding an HTTP request open |

The API validates exactly one automation repository per job, project ownership of connection/repository/environment IDs, safe relative suite roots, source-ref consistency, authorized test layers, request limits, publication mode and the expected project revision. Performance/destructive layers are policy-restricted even though the extensible enum contains them. Client-supplied IDs never confer authorization.
