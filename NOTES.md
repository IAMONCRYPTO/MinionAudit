# OpenMinion 0.1.22 integration notes

Source inspected before application code: README, `examples/sdk/tool_agent.py`, `delegation.py`, `application_runtime.py`, `sessions.py`, and the implementations in `src/openminion/api`, `base/config`, `tools`, `modules/memory`, `modules/skill`, and `modules/telemetry`.

The supplied workspace was empty and had no SDK installed. The official v0.1.22 tag was fetched locally into ignored `vendor/openminion`. Release commit: `bf7cc18d15abd059ec130f50aa80ecb2ec5c5305`. The published wheel is pinned to the same version. No SDK source modifications are required.

## Building Blocks Tested

| Block | Implementation and observed behavior |
| --- | --- |
| Runtime config | `APIRuntime.from_config_path(..., home_root=..., data_root=...)` keeps runtime state local. Named `agents.auditor.provider` selects the OpenAI adapter. |
| Provider | NVIDIA NIM endpoint, user-selected Nemotron 3.5 Lightning, `api_key_env=NVIDIA_API_KEY`, `tool_call_strategy=native`. Both originally requested models returned HTTP 410. Live verification results are recorded below. |
| Tools | `@tool(min_scope="READ_ONLY", idempotent=True)` and `Agent(tools=[...], forced_tools=[...])`. App fails if the scanner tool did not actually execute. Local scanner detects 12 planted candidates. |
| Permissions | `WRITE_SAFE` describes the `.gitignore` tool; `action_policy.mode=ask`, a tool-specific ask rule, and `approval_callback` route each exact write to terminal approval. Unrecognized tools and extra arguments are denied. |
| Sessions | Explicit `session_id`, actual result run/thread identities, SDK storage, and app snapshots. `inspect` is local; `scan --session` reuses history while re-running current-file checks. |
| Memory | `runtime.runtime_memory_assembly.service.list(ListQueryOptions(...))` and `.write_record(...)` store a structured fingerprint baseline in a repository-specific project scope. This lower-level service is used because exact baseline comparisons must not depend on model-generated recall text. |
| Skills | SDK `Skill.ingest_text`, `get_skill(id, version)` and parsed sections. Bundled procedure is explicitly supplied to the reviewer; no automatic skill-selection claim. Draft skill version is intentionally not promoted. |
| Delegation | SDK `subagent(parent, tools=[], timeout_seconds=120)` shares the runtime, isolates the child session, and records lineage. No repository or memory tools are granted to the child. |
| Diagnostics | Real `AgentRunResult.stats`, metadata, run IDs, SDK session telemetry, elapsed timings, executed tool records, and operator decisions appear in the HTML drawer and JSON. Missing usage is never estimated. |

Observed friction:

- The parser rejects top-level `provider` with an error recommending `agent.provider`. Following that instruction fails because the same release rejects the top-level `agent` block. Working shape: `agents.<id>.provider`. Source: `base/config/parser/payload.py`.
- A named profile without explicit `default_channel` defaults to an empty string. The SDK `Agent.run` then fails with `inbound authenticity denied (reason=invalid_channel, mode=warn)` before model execution. Explicit `default_channel: console` fixes the local CLI route. The authenticity guard remains enabled.
- `Skill.ingest_text` stores a draft. `get_skill(id)` returned `NOT_FOUND`, while `get_skill(id, returned_version_hash)` succeeded. Repeated ingestion returns `admission.duplicate_content`; the returned version is usable.
- Default bootstrap logging emits dozens of registration and migration messages. `OPENMINION_LOG_LEVEL=ERROR` keeps CLI output concise; explicit audit traces remain available.
- On 2026-11-26 both requested NIM models returned HTTP 410. Qwen's response explicitly reports end of life on 2026-05-12. NVIDIA's current `/v1/models` catalog included `nvidia/nemotron-3.5-lightning-30b-a3b`; the user selected it. This is provider availability friction, not an SDK failure. NVIDIA also marks [Llama 3.3 deprecated](https://build.nvidia.com/meta/llama-3_3-70b-instruct).
- Nemotron returned a completed SDK run with zero tools and the message “I could not safely update the task conditions.” `forced_tools` therefore did not guarantee execution on this model path. MinionAudit checks actual execution and treats that outcome as failure. An explicit request beginning `Call scan_repository` completed the scanner turn successfully.
- A delegated turn with a bare JSON input failed with `EMPTY_PROVIDER_RESPONSE` at the initial 1600-token provider cap. The completion cap was increased to 8192 and the child input now explicitly asks for a review before presenting the JSON. The causal contribution of each change was not independently isolated.
- The fresh Python 3.14 environment successfully installed the published wheel and dependencies. Dependency versions beyond the SDK are resolved by pip; a full environment lock would improve cross-platform reproducibility.

## What We Learned

- Fix legacy-config errors to recommend the schema actually accepted by the release, and ship a minimal custom-endpoint `agents.json` example beside the SDK tools example.
- A named SDK profile should resolve a valid local channel by default or reject missing channel configuration during bootstrap with an actionable message.
- Expose a compact public memory key/value baseline API so applications need not access runtime assembly services for exact structured recall.
- Document draft-skill retrieval by version, duplicate-ingest behavior, and the distinction between explicit application selection and runtime skill promotion.
- Provide a quiet application bootstrap mode and a small documented diagnostic export that combines parent/child run statistics, permission decisions, and tool latency.
- Reduce orchestration overhead for bounded SDK tools: the successful second scan used 7 LLM calls for 1 scanner tool invocation. Its child used 3 LLM calls, and its approved fix turn used 5. Expose a documented minimal tool loop for applications that already own the workflow.
- Report presence and exploitability separately. A `.env` ignore rule is helpful but never constitutes credential rotation or a resolved exposure. Likewise, low-level Solidity calls need review; their presence alone is not a confirmed exploit.

### Verification record

- Local unit suite: 6 tests passed (planted rules/redaction, AST and stable fingerprints, safe write idempotency, hard-link write refusal, report escaping, and real scanner findings resolving from 2 to 1 without false new issues).
- The filesystem sandbox denies hard-link creation, so the hard-link fixture initially failed before reaching the application. The full suite was then run outside that sandbox; all 6 tests passed, including refusal to modify the linked file. No production files were used by the fixture.
- First complete real NIM run: `audit-a6d73f9bee724345`, 85.252 seconds, 3 files, 12 candidates (2 Critical / 9 High / 1 Medium). Scanner tool executed once; real bounded child produced remediation advice. Terminal answer `no` recorded `DENY`; no target `.gitignore` existed afterward. Baseline was stored in SDK memory.
- Second complete real NIM run: `audit-91ebc5f4c1a14d10`, 126.312 seconds including operator wait, same 12 candidates. SDK memory recall returned `found=true`; terminal displayed `Previous run: 12 issues -> Current run: 12 issues (0 resolved, 0 new)`. Terminal answer `yes` recorded `ALLOW`; `protect_env` executed and created exactly `.env\n` in the sample `.gitignore`.
- Findings remain at 12 because an ignore rule does not remove an environment file or rotate credentials. This is intentional; resolution counts must reflect actual removed scanner candidates.
- Single-file HTML and JSON reports were generated from real run data. Escaping and structural checks passed. Browser visual QA could not run because the available browser tool blocks local `file://` URLs; no screenshot-based layout claim is made.
- Final HTML structural check: 12 finding articles, 4 filter buttons, 1 diagnostic drawer, no external `src`/`href` resources. The saved successful session also passed the actual `inspect` CLI check.
- Initial Git ignore verification allowed the fake sample `.env` as an exception. Before public publication, that exception was removed at the user's request: every `.env` is now ignored. Setup copies the public `fixtures/sample.env.example` into the local sample target. The regression fixture test creates its own temporary `.env`, so tests work from a clean clone. A content check of 98 local files outside vendor/venv found no copy of the supplied API credential outside the root `.env`.
