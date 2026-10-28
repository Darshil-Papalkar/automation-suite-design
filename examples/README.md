# Synthetic contract examples

These records illustrate the design contracts. They are not results from real test generation, real Jira/Confluence items, or a live repository. IDs, URLs, commit placeholders and repeated-character hashes are intentionally synthetic; recompute real hashes in the implementation.

| File | Domain definition | Meaning |
|---|---|---|
| `job-request.json` | JobRequest | Two requirement references and two repositories; framework omitted so discovery is required. |
| `requirement-spec.json` | RequirementSpec | Explicitly allows three retries after the initial call: four total attempts. |
| `assertion-oracle.json` | AssertionOracle | An upper-bound assertion derived from that explicit requirement. It is illustrative, not a full behavioral test plan. |
| `validation-report.json` | ValidationReport | Shows how an executed failing test and a candidate product defect differ from passing validation. |

The retry example explicitly distinguishes retries from total attempts. If real source text does not make that distinction, the analyst must ask for resolution rather than assume either interpretation. A complete retry suite would also inspect applicable success, non-retryable error, eventual success and backoff behavior when specified.

`contracts/domain.schema.json` holds named definitions. Validate each file against its indicated definition; a schema pass checks structure only. The validation report's failed runtime gate remains failed even if later review confirms a product defect.
