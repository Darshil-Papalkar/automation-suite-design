# Technology choices, techniques, and evidence

Design version: 1.0. Research checked: 28 October 2026. This is a recommended implementation baseline, not a claim that every listed tool is required or that the design has been implemented. Recheck support, licensing, account access, and exact compatible package versions when implementing; commit dependency lockfiles and runner image digests. Never install unpinned `latest` dependencies in production jobs.

## 1. Selected baseline

| Layer | Selected approach | Why / boundary |
|---|---|---|
| Platform language | Python; use a supported release compatible with the selected Temporal SDK and dependencies, initially evaluate Python 3.12 or 3.13 | Platform language does not constrain target project languages. Do not alter target runtimes. |
| HTTP API and contracts | FastAPI, Pydantic v2, generated OpenAPI | Typed request/response validation; explicit domain validation remains required. |
| Workflow execution | Temporal Python SDK and Temporal server/cloud | Sole authority for durable workflow progression. LLM/network/runner work belongs in Activities. |
| Domain storage | PostgreSQL, SQLAlchemy, Alembic | Tenant-aware metadata, queryable job projections, unique constraints, transactional outbox and migrations. Temporal persistence is separate. |
| Large artifacts | S3-compatible object-store adapter; filesystem implementation in offline development | Immutable source snapshots, context bundles, patches, reports, traces and logs. Per-tenant access and retention. |
| Retrieval v1 | Git snapshots, ripgrep, syntax-aware chunks, PostgreSQL full-text search | Exact symbols and project-local evidence before introducing embedding complexity. |
| Retrieval extension | pgvector + lexical retrieval + reciprocal-rank fusion; optional reranking | Add after retrieval evaluation demonstrates value. No graph database required. |
| Code structure | Tree-sitter plus language-specific resolution where needed | Syntax boundaries, imports and declarations. Tree-sitter alone is not a complete cross-language call-graph or type resolver. |
| Model execution | Provider-neutral model adapter, typed outputs, narrowly scoped tool calls | Explicit model configuration, token budgets, retry handling, evidence references and policy-enforced tools. |
| Target runners | First pytest; then TypeScript Playwright Test | Two distinct language/test-layer vertical slices prove adaptation. More frameworks use the same contracts. |
| Local execution | Rootless containers on a dedicated development runner where supported | Suitable for controlled development fixtures; no host Docker socket exposed to generated code. |
| Production execution | Ephemeral isolated worker with gVisor or dedicated VM/microVM, selected after compatibility testing | Treat checkout scripts, package installs, test discovery and test runs as untrusted code. Containers alone do not establish strong tenant isolation. |
| Git integration | Git CLI internally; GitHub App/provider adapter first | Repository allowlists, short-lived credentials, branch ownership and idempotent PR creation. GitLab/Bitbucket are separate adapters. |
| Requirements connectors | Jira Cloud REST v3 and Confluence Cloud REST v2 first | Custom field mapping, pagination, permissions and linked content handling. Data Center support uses distinct connectors. |
| Observability | OpenTelemetry instrumentation; existing logs/metrics/tracing backend | Correlate job, activity, model request and runner attempt without logging secrets or full source by default. |
| Development tooling | uv or equivalent locked environment, Ruff, static typing, pytest for the platform, Docker Compose | Target-repository tooling takes precedence over platform preferences. |
| Deployment | Compose for local development; API/control workers plus separate runner capacity in production | Use the organization's existing container/VM platform. Kubernetes is optional infrastructure, not a product requirement. |

These decisions are architectural recommendations. Official capability references for the platform stack are in the HLD source register; the sources below support the AI/testing choices.

## 2. Model selection and configuration

Implement `ModelProvider.generate_structured()` and `ModelProvider.run_tool_step()` behind an application-owned interface. No business stage should directly import a provider SDK. Keep provider model identifiers, reasoning effort, context limits, timeout, cost table, retention configuration and schema capabilities in versioned configuration.

A concrete OpenAI pilot candidate is `gpt-6.1-sol`, with `gpt-6-astra` as a quality-focused comparison. Both identifiers appeared in the official API catalog on the research date. Treat this as a starting shortlist, not a demonstrated winner for this product. Availability and supported features must be confirmed in the deployment account. Avoid fixing prices or context-window assumptions into business logic. [OpenAI model catalog](https://developers.openai.com/api/docs/models)

For an OpenAI implementation use the Responses API, function calling for tools, and structured output for stage artifacts. Provider schema support is a subset of JSON Schema: maintain a provider-compatible generation schema, then validate the returned object against the full domain schema and semantic rules. A schema-valid expected result can still be factually wrong. [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [function calling](https://developers.openai.com/api/docs/guides/function-calling)

Start with one capable model across roles. Record separate stage prompts and independent reviewer calls. Add a cheaper extraction/classification model only after paired evaluations show no material quality loss. A different reviewer model can diversify errors but does not establish oracle independence. Benchmark model changes with the same inputs, tool permissions, budgets and reference evaluations. [OpenAI model selection guidance](https://developers.openai.com/api/docs/guides/model-selection)

If policy requires a different cloud provider or a self-hosted model, replace the provider adapter and run the same conformance/evaluation suite. Do not assume an OpenAI-compatible endpoint implements identical tool calling, schema constraints, cancellation, usage accounting or retention semantics.

## 3. Techniques to implement

| Technique | Concrete implementation | Verification |
|---|---|---|
| Requirement grounding | Atomic criteria with source snapshot, location, expected behavior and ambiguity status | Every business assertion has a source or approved invariant. |
| Repository context engineering | Targeted files, trusted example patterns, dependency slices and on-demand reads | Retrieval recall and citation correctness against a labeled set. |
| Hybrid retrieval | Lexical + optional vector ranks; filter by tenant, access, repository and snapshot before candidates enter prompts | Exact-symbol cases, domain paraphrases and unauthorized decoys. |
| Syntax-aware chunking | Preserve functions/classes with path, symbol, language, imports and content hash | No orphan snippets without needed signatures or helper references. |
| Structured intermediate artifacts | Versioned RequirementSpec, RepositoryProfile, TestPlan, PatchManifest and ValidationReport | JSON/domain validation, referential integrity, schema migrations. |
| Tool-using generation | Agent reads evidence, resolves helper definitions and proposes bounded patches | Every file/command operation is authorized outside the model. |
| Execution-guided repair | Actual compiler/runner feedback; limited attempts; unchanged oracle | Assertion weakening, skips and product-code edits are rejected. |
| Risk-based scenario design | Boundaries, negative paths, roles, state transitions and relevant cross-service contracts | Review against risk rubric and requirements. |
| Property-based testing | Use existing property framework; add properties only from justified invariants | Counterexample replay and invariant review. |
| Metamorphic testing | Derive justified relations where exact outputs are difficult | Relation must be valid for the domain; never invent a relation just to create an assertion. |
| Mutation and fault sensitivity | Target changed/relevant logic or controlled service faults | New test fails for the intended semantic change, not setup breakage. |
| Independent review | Separate pass sees requirements, patch and evidence; optionally independently plans high-risk assertions | Human-labeled oracle correctness; reviewer disagreement is not resolved by simple majority. |
| Adaptive test selection | Dependency/coverage signals select fast feedback; required CI remains authoritative | Compare selected versus full relevant regressions periodically. |
| Incremental regeneration | Stable requirement/scenario IDs, fingerprints, source deltas and invalidation | Repeat runs do not duplicate tests; changed requirements retire or revise affected scenarios. |

Context engineering and on-demand search are supported by current agent design guidance, but the specific retrieval policy here is our design choice. [Anthropic context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

Execution-feedback research supports evaluating this approach, not promising correctness. CoverUp evaluates Python regression tests; a 2026 replication reports that stronger plain-model baselines can outperform more elaborate older methods in its tested setting. Therefore retain a strong direct-generation baseline and justify every added agent/index/review stage with measured benefit. [CoverUp](https://arxiv.org/abs/2403.16218), [2026 test-generation replication](https://arxiv.org/abs/2601.09695)

## 4. Available tools and where they fit

| Tool / family | Use here | Limits |
|---|---|---|
| Playwright Test agents | Optional planner/generator/healer integration within the Playwright adapter | Framework-specific; must obey this system's frozen oracle and repair restrictions. Does not solve Jira governance or cross-framework adaptation. |
| Playwright locators, traces and reporters | Ground UI actions and diagnose failures with the actual application | DOM observations do not establish intended business behavior. Redact auth state and user data in traces. |
| pytest collection and JUnit XML | Inventory and normalized results for Python adapter | Collection imports code and executes plugins; run in the sandbox. XML does not describe all semantic assertions. |
| Hypothesis | Property-based and stateful cases for Python where appropriate | Requires a correct invariant and controlled environment. |
| Schemathesis | OpenAPI/GraphQL-derived API cases and workflow exploration | Schema conformance is not complete business requirement coverage. |
| Stryker | Mutation evaluation for supported JavaScript/TypeScript, .NET and Scala targets | Apply only through a supported compatible test adapter; mutation results have equivalent/uncovered/invalid cases. |
| Language-native coverage tools | Branch/line impact evidence, selected by adapter | Coverage does not prove assertion quality. |
| Tree-sitter | Syntax indexing and localized patch/context boundaries | Requires supported grammars; dynamic resolution may be incomplete. |
| MCP | Optional connector/tool interoperability | Not a workflow engine, authentication shortcut, or execution security boundary. |
| Existing CI and native test reports | Final repository integration evidence | CI unavailability means CI-unverified, not CI-passed. |

Playwright currently documents planner, generator and healer agents. Their output can be integrated without replacing the platform's requirement and review contracts. [Playwright Test agents](https://playwright.dev/docs/test-agents)

Hypothesis supports property-based testing, while Schemathesis generates tests from OpenAPI/GraphQL schemas. Use them when they fit the target project and approved scope. [Hypothesis](https://hypothesis.readthedocs.io/en/latest/), [Schemathesis](https://schemathesis.readthedocs.io/en/stable/)

Tree-sitter provides incremental concrete-syntax parsing. Stryker describes mutation testing and the limits of code coverage. [Tree-sitter](https://tree-sitter.github.io/tree-sitter/), [Stryker](https://stryker-mutator.io/docs/)

The Python adapter should follow the installed pytest version's documented collection and report options. [pytest reference](https://docs.pytest.org/en/stable/reference/reference.html)

## 5. Techniques deliberately deferred

- Fine-tuning: revisit after collecting consented, reviewed examples and proving recurring errors that retrieval or tool improvements do not solve. Keep current repository facts in retrieval.
- General multi-agent debate or voting: extra tokens are justified only by evaluation. Independent modules can be generated concurrently in isolated branches.
- Graph database / full GraphRAG: store explicit repository/symbol/test links in ordinary tables first; add traversal infrastructure only if measured queries require it.
- Fully autonomous merge, production environment testing, automatic source-code fixes, broad dependency upgrades: outside default generation scope.
- Unrestricted automatic healing: forbidden when it changes expected behavior or masks defects.
- Replacing project frameworks to make generation easier: outside default scope.

## 6. Security references and implementation implication

Prompt injection and excessive agency are relevant because the agent reads external text and invokes tools. Repository files, tickets, comments, browser pages and test output are all untrusted content. Enforce file scope, network policy, credentials, resource budgets and publication authorization in application/runner code. Prompt instructions alone are insufficient. [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/), [OWASP excessive agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)

If MCP is added, validate token audience and server identity; do not pass unrelated upstream tokens through to tools, and enforce SSRF protections. Implement against the chosen protocol version rather than assuming every server implements the newest specification. [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)

## 7. Version and procurement policy

1. Resolve current supported versions during milestone M0. Check Python/Node/SDK/runtime compatibility and deployment constraints.
2. Pin application dependencies in a lockfile and runner images by digest. Preserve target repository lockfiles.
3. Record model requested/resolved ID where available, configuration and prompt version per call. Model outputs are not guaranteed reproducible byte-for-byte.
4. Run adapter conformance and benchmark gates before model, prompt, tool, image or parser upgrades.
5. Keep a software bill of materials and license review for redistributed services and packages. Do not assume all S3-compatible server products have equivalent licenses.
6. Pricing, region availability, retention options and service limits are deployment decisions to confirm with the chosen account/provider. Use cost formulas and usage accounting rather than hard-coded price claims.
