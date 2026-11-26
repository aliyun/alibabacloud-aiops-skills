# Offline Question Export and Assertion Checking

`evals/evaluate.py` is a standard-library-only offline helper. It exports candidate-visible questions, compares an actual candidate file with a separate reference, records provenance/access-trace gaps, and optionally imports an actually completed semantic-review declaration. It does not execute candidates/exported session code, create model runs, call models/APIs, or access the network. Platform scenarios and fixture indexes are not this tool's input; use the explicit role formats below.

## Unattended workflow integrations

The W01-W15 scenarios run separately from the sixteen supplied-evidence answers and the routing suite. W01-W09 give the agent a natural question and a case-scoped offline read tool. Use one command per business read. Catalog pages, metadata, details and focused follow-ups require parameters from prior responses. W05 exposes two distinct definitions. W06-W09 run one logical read in the offline tool's `observe-error` mode. It calls the production client, including its built-in retry policy, and returns a local observation only when the terminal business error code and RequestId match the actual recorded response. The unchanged failure envelope and internal attempt count are visible. Transport setup, mismatched requests and unexpected success cannot produce a verified observation. A zero exit in this mode proves local observation of failure, never successful service access. Multiple outer invocations are forbidden; check the actual tool trace. The runner uses the production CLI parser, request validation, client retries, response validation and output handling, with a fixed local transport and an empty credential environment. An unrecorded operation, scope, identity or cursor fails locally. The recordings are immutable service examples, with no live account, endpoint, SDK or network validation. Recordings do not maintain a shared session ledger. Check ordering and identity provenance in the agent trace. Source inspection is disallowed for candidates; an instruction is not OS-level isolation.

W10 and W11 supply full synthetic detail responses and require real execution of the installed TSV answer validator. Score complete-snapshot sets and proportions separately from observations on a truncated extract and unknown fields. W12 asks for a readiness assessment based only on the task and installed instructions. It has no service recording. The replay command rejects this case before loading recordings, including when the caller guesses a target. Audit the actual trace for zero business calls, runtime probes and auxiliary file reads; a forbidden read contaminates the run even if the final text matches. These restrictions do not conceal other files on a shared host. Keep the registered case UUIDs when updating prompts or checks. Compare fresh results by AgentHub request ID and the recorded Git commit. W13 starts from a metric search, reads the metric graph, focuses retrieval on the newly discovered table node, and reads the downstream relation to verify both join keys. W14 and W15 use an explicitly authorized synthetic counterpart through the replay CLI. W14 supplies the target only after a pertinent question. W15 requires both returned candidate identities and names before the counterpart chooses a definition. W14 target reads and W15 selected detail reads require the actual synthetic ReplyId issued after the appropriate clarification. Pass the same existing host-approved output parent to issue and verify this per-dialogue receipt. The local tool uses a random private mode-0700 directory and exclusive mode-0600 record. A receipt is scoped to its case and parent and may be reused there. It is not a cloud credential or an OS-level attestation. W15 initial discovery takes no receipt. Audit the trace for order, current-session ownership and allowed call counts. This measures automated clarification and follow-through; it does not measure interaction with a human. All fifteen cases require a final answer without operator replies. Use `python3 evals/build_workflow_replay.py --check` to verify the active workflow files. Report actual platform coverage, model performance, local offline execution, and live OpenAPI availability separately.

## Unattended provided-evidence evaluations

The files in the active platform v2 auto-generated scenario directory contain sixteen independent `provided-evidence-v7` tasks named `provided-evidence-process-answer-*` alongside separately maintained routing and offline workflow tasks. Their names and UUIDs differ from the superseded supplied-evidence v1, v2, v3, v4, v5 and v6 tasks; results must not be merged with earlier runs or historical API-workflow results. Only the sixteen known superseded generated v6 A paths are removed from the active catalog; Git retains their history, and the original fifty-four API/trigger fixtures remain unchanged. `evals/provided-evidence.json` is the grading-side index. Its schema remains unchanged. Definitions and generated inputs have `execution_status=not_run`; they are not candidate execution results.

Each candidate prompt contains the original natural business question, concise local-answer execution context, raw successful synthetic knowledge responses, and a delivery reminder after the JSON. The first tool action reads the installed `alibabacloud-dataworks-context-graph` entry point. The known AgentHub session-workspace entry point is `.qwen/skills/alibabacloud-dataworks-context-graph/SKILL.md`; the helper is `scripts/knowledge_answer.py` under that same installed directory. Candidates run the helper by its absolute installed path. Assemble the original responses and selected source fields first, then send the full JSON job to new-job --from-stdin under the host-approved existing outputs parent. Render from its returned private path with --full-selected-fields and the original response-batch SHA256. The builder computes that fingerprint from the same original response list before candidate execution; the candidate copies it unchanged into --expected-response-sha256 and must never replace it with a digest of its draft job. Generic job-shape guidance supplies no case-specific facts, selected paths, gold or scoring rules. Other hosts use explicitly advertised installed paths without searching.

The local helper needs POSIX Python 3.10+ and the standard library, with no SDK, CLI, cloud runtime, credentials or network for provided evidence. If the host-specified output parent is absent, the candidate creates that approved directory before new-job rather than changing output scope or preparing a cloud runtime. No doctor, installation, API calls, evaluation-file reads or human follow-up are allowed. At most two local repairs may use the same response batch. The helper accepts only source pointers and exact quotations or actual Graph JSON, not free business conclusions, reasons or citation labels. Source attribution is computed from actual bound identities/titles/filenames/RequestId; JSON audit retains the original pointer and hashes. Unknown fragments must be literal question substrings; unresolved applicability requires multiple selected source identities. Valid extracts retain original warnings and never certify global absence or completeness. Extraction validation cannot prove relevance, question intent, business truth or complete answer coverage; independent semantic grading remains necessary.

The final assistant response must be exactly the helper's complete Markdown stdout, with conclusion, evidence and unconfirmed-item sections. These short answer tasks need no todo_write or planning tools. Complete all required local job, artifact and log work before the final successful render tool step. If host logs require the actual render exit status, combine render execution, truthful status logging and complete stdout delivery in one final shell call; never prefill success logs or skip required host logging. After that successful call, make no further tool or todo calls and send only the complete final assistant answer; do not append business prose, a summary, a completion notice or a path receipt. If the Skill or helper is absent in a without-Skill baseline, disclose absence and answer with literal supplied source quotations and actual titles/IDs in the same three sections, without installation, fabricated tools, directory searches or human input. If unable to complete, briefly end without requesting later input. This is forced installed-Skill evidence-use evaluation, not natural Skill discovery. The active suite retains the sixteen original questions, thirty-seven raw responses, thirty-two semantic criteria, literal checks, expected outputs and fifty-four archives. The write guard allows only the private job, host-approved outputs and required logs. It still forbids business writes, SQL execution, builds, grants, cloud changes, changes to Skill or evaluation files, and saving evidence to unauthorized paths. The thirty-nine routing v3 tasks, their identities, requests, provenance and forbidden rules are also unchanged.

The real AgentHub A15 pilot at commit `e9cc446`, Skill version `1.1.7`, used Qwen3.7-Plus and completed in 61 seconds without human input or SDK setup. It wrote a complete `outputs/answer.md` but returned only a 207-character summary as the final response. Native `result_verification.checks` actually ran and failed both groups: the output guard matched 1/3 labels, missing the evidence and unknown sections; the evidence guard matched 2/3 values, missing `DERIVED_FROM`. The visible trace showed two `write_file` calls and no observed `SKILL.md` read. A complete artifact therefore did not satisfy final-answer delivery or establish Skill invocation. Version `1.1.8` and supplied-evidence v2 attempted to address these gaps without weakening checks.

The subsequent v2 A15 pilot at commit `79c3079` produced a complete 1,386-character final answer and passed both native guard groups. Its trace included reading the installed `SKILL.md`, two directory listings, an output-directory shell command and two file writes. Candidate work finished in roughly 90 seconds, but the with-Skill session was reported as timed out after 5 minutes 12 seconds; the without-Skill baseline passed both guards in 4 minutes 50 seconds. Native answer guards passing did not establish a successful with-Skill pilot session or independent semantic acceptance.

On 2026-11-18 (Asia/Shanghai), the v2 full-run session table completed 72 Qwen3.7-Plus sessions: sixteen evidence tasks and twenty positive routing tasks, each with and without the Skill, with a ten-minute session budget. That session-only view showed 70 successes, two assertion failures, and zero waiting-human, queued or running sessions. Its with-Skill side showed 35/36 session successes: A01 failed both guards after writing a complete `outputs/valid_user_answer.md` and returning only a completion receipt, with no observed Skill read. Across all sixteen with-Skill evidence session outputs, literal guards passed 30/32 groups across 15/16 tasks; without-Skill outputs passed 31/32 groups across 15/16 tasks, with A14 missing one guard. Each side's twenty positive routing rows had `0/0` response checks. Session success and these raw guard counts do not establish correct Skill loading, explanation semantics or platform-gate acceptance.

The finalized native v2 report, Request `15774` / Coverage `12434`, generated at `2026-11-18T11:27:17.049707+08:00` for commit `79c3079`, supersedes the earlier incomplete interpretation of that session table. It reports **87 total tasks**: the 72 with-Skill/baseline sessions plus **15 negative trigger-only tasks**, which did run. The earlier statement that negatives were excluded was incorrect. Native trigger and TestCase aggregates were both **25/36 (69.44%)** for the positive with-Skill set: nine of sixteen evidence tasks and sixteen of twenty positive routing tasks were detected as loading/triggering the Skill. Native expectation groups passed **18/18**, limited to those nine triggered evidence tasks; this is neither 32/32 evidence coverage nor independent semantic acceptance. The fifteen negative tasks passed **11/15** trigger checks; false positives were creation, grants, internal BFF calls and scheduler operations. Forbidden hits and execution exceptions were both zero. Empty response checks still do not grade answer or routing-explanation quality.

Keep actual entry-point reads separate from native trigger flags and response checks. A recorded Skill name or intention is not a file read; establish actual loading from the candidate tool trace. The v2 A15 pilot has an observed installed `SKILL.md` read, while the full-run A01 sample has none. The finalized report's detected-load totals are not a complete independent audit of every entry-point read. Native capability/API coverage remained **33.33% (failed)**, and original description-expression coverage also failed. These remain unresolved platform-gate results. Supplied synthetic evidence cannot count as live API workflow coverage, and routing-only requests cannot prove live retrieval. Adding a human follow-up would violate the maintained unattended task boundary.

A separate independent review of the sixteen actual with-Skill v2 final responses scored 30/32 original semantic criteria and 14/16 cases with both criteria satisfied. A01 delivered only a receipt; A06 broadened a limited rule in its conclusion despite quoting the correct scope elsewhere. Extra unsupported-claim findings for A05 (uniqueness and cardinality), A06 (scope), and A16 (a time-zone parenthetical) were recorded separately, without adding scoring criteria. The 14/16 criteria-acceptance count is therefore not an all-claims-grounded rate. This review assessed final-response evidence use, not files, execution traces, live retrieval, or Skill benefit.

The actual version `1.1.9` run at commit `cb6e518`, using supplied-evidence v3 and cued-routing v2, completed 80 session-table rows: all 40 with-Skill rows were marked success, while the baseline had 39 successes and one assertion failure. The sixteen with-Skill evidence final answers passed all 32/32 strict native response-check groups. Independent review also accepted 32/32 original semantic criteria across 16/16 cases, but only **10/16 final answers were fully grounded**. Six answers added unsupported claims: A03 inferred an amount inequality and difference meaning; A04 inferred join conditions from shared business keys; A08 invented a JSON source path; A09 added usage contexts; A11 asserted independence or absence of exceptions; A13 interpreted an enum label without a supplied definition. Passing the original criteria did not make these additional claims true, and the criteria and literal checks are not weakened to accept them.

Review of the actual twenty-four positive routing traces found three without an actual instruction-load tool call: date-rule, documented-definition-comparison and original-phrase-5 catalog. Their final answers treated the broad prohibition on executing a Skill and the metadata-only alternative rule as reasons not to load instructions, despite selecting the intended capability. Correct selection and `0/0` response checks do not establish actual loading or a routing pass.

The finalized native v3 report, Request `15780` / Coverage `12444`, generated at `2026-11-18 12:01:00` (Asia/Shanghai) for commit `cb6e518`, did **not** pass overall. Positive trigger and TestCase aggregates were **37/40 (92.50%)**, matching the three positive routing cases without loads; expectation groups passed **32/32**. All fifteen negative trigger-only tasks passed **15/15**. Forbidden hits, execution exceptions and prerequisite exceptions were zero. Original-description expression coverage passed, but native capability/API coverage was **25.00% (failed)**. The earlier v2 **33.33%** API coverage remains a historical result, not the current run's result. Neither native literal checks nor platform bookkeeping replaces the independent all-claims review above, and supplied evidence still does not count as live API coverage.

The actual version `1.1.10` run at commit `dd34d95`, supplied-evidence v4 and cued-routing v3, completed its session rows. The forty applicable installed-Skill cases had actual instruction reads in their traces. Independent review of the sixteen installed-Skill final business answers accepted **30/32 original criteria across 15/16 cases**, but only **14/16 answers were fully grounded**. A10 answered an unrelated Skill-routing request instead of the asked business definition and scope; the production entry point's detailed routing procedure contaminated the business answer. A11 added an unsupported independence assertion. These are actual failures, not reasons to weaken the original criteria or literal guards. The finalized native report, Request `15782` / Coverage `12447`, generated at `2026-11-18T12:26:28+08:00`, passed combination checks with **40/40** positive trigger and TestCase results, **32/32** literal checks and zero Forbidden hits. Overall it still failed: capability/API coverage was **25.00%**, and the positive description-trigger coverage detector was unavailable. Native combination success does not override the independent semantic failures or the baseline interventions below.

Two without-Skill baseline sessions required automatic termination-only operator replies: missing-requested-fact initially refused and requested a legitimate coding task; positive-time-window routing called the task a template and asked what to do. The operator supplied no business answer, credentials or connection configuration, only an instruction to report inability and end without further tools or questions. Installed-Skill cases received no follow-up replies. Exclude both affected cases from a clean unassisted baseline comparison even if a native table later marks success; their original no-followup contract was violated. This is not evidence of a clean baseline gain.

Version `1.1.11` and supplied-evidence v5 replace free-prose answer assembly with bounded local source extraction and rendering, and remove detailed routing algorithms from the production business entry point and interpretation reference. Routing procedures remain only in routing task context and this evaluation-operator reference. Read-only metadata inspection does not authorize executing a business request. SDK/CLI/authentication/endpoints, TSV behavior and routing v3 definitions are unchanged. The new definitions and local fixture-rendering tests are not new model passes. A fresh actual run and independent final-source audit remain required, and no native API-coverage gate is claimed repaired.

The actual `1.1.11` / supplied-evidence v5 A09 trace exposed a separate copy-integrity failure: every copied KnowledgeBaseId lost one `-0000` component (`00000000-4000-8000-000000000201` instead of the supplied `00000000-0000-4000-8000-000000000201`). The altered responses remained structurally consistent with each other, so source extraction alone did not detect the changed identity. The v5 A10 trace exposed a separate delivery failure: complete Markdown appeared in tool stdout and a saved artifact, followed by log/artifact writes and a final completed todo_write, without a complete final assistant answer. Native guards showed 2/2 despite that missing final delivery; those counts are not independent final-answer acceptance. The v5 A14 answer selected only the first sentence of its source Content, omitting the adjacent sentence recording absent applicability, version and effective-date information. An independent blind review of the sixteen v5 final answers accepted **29/32 original criteria across 14/16 cases**, with **13/16 fully grounded answers**. These are measured v5 failures and scores, not a v6 PASS or a repaired native API-coverage result; the finalized native v5 result is recorded separately below.

Version `1.1.12` and supplied-evidence v6 add an optional authoritative batch fingerprint guard to the renderer and require that fixed original fingerprint in each A task. Canonical hashing covers the complete ordered response list before source selection. Each v6 A task also requires optional --full-selected-fields mode because the supplied source fields are short: exact quotes remain checked anchors, while rendering preserves the complete selected field, including adjacent qualifiers and recorded gaps. Default quote-only rendering remains compatible. This does not establish relevance or coverage outside the selected fields and does not authorize selecting unrelated whole responses. A mismatch exits 2 with fixed BatchDigestMismatch and no input echo; the candidate may repair the copy only within the existing two-local-repair budget, then ends without human follow-up. No new job fields, free business prose, cloud calls, SDK dependencies or attestation claims are added. Calls without a supplied digest remain compatible, live_identity_verified stays false, and matching a supplied digest proves neither response authenticity nor semantic correctness. The execution-context change makes the final successful render the last tool step while preserving actual host logging, and prohibits premature todo completion as a substitute for final delivery. All original A questions, raw responses, criteria, checks, Forbidden rules, expected outputs and provenance remain frozen; routing v3 and fifty-four archives are unchanged. These changes need fresh actual execution and independent audit, not a relaxed score.

The finalized native v5 report, Request `15783` / Coverage `12449`, generated at `2026-11-18 13:13:38` and completed at `13:21:02` (Asia/Shanghai) for commit `c24c722`, failed overall. Positive trigger and TestCase results were **40/40**, native literal checks were **32/32**, Forbidden hits and execution exceptions were zero, and original-description expression coverage passed. Capability/API coverage was **23.08%**, while assertion coverage was **0.00%** because the A tasks had no declared native local-process expectations. These native counts do not override the independent v5 final-answer failures above. The separate v6 incremental run is tracked against immutable commit `cee6da5`; no result from that run is asserted here.

Version `1.1.13` and supplied-evidence v7 add exactly one grading-side local-render expectation to each of the sixteen A tasks. The candidate prompts remain byte-identical to v6 at `cee6da5`, and the original business expected-output blocks, questions, raw responses, criteria, literal guards, Forbidden rules and provenance remain exact. Only the names, UUIDs, suite/version metadata and new process expectations change. Routing v3 retains its thirty-nine original definitions and no local business-execution expectation; fifty-four archives remain unchanged.

Each new expectation uses the historically recorded Python-script template format: type cloud_interaction, method bash, command_pattern_regex true. The schema name does not turn a local command into a cloud API call. The pattern requires a literal Python3 knowledge_answer.py render invocation with that case's original --expected-response-sha256 value and --full-selected-fields in the same command. It accepts ordinary relative/absolute and quoted paths, optional -S, standard option ordering, leading cd commands, variable capture and explicit bash/sh -c or -lc wrappers with that same simple inner form. Matching is anchored at the absolute start and consumes the supported prefix grammar, so a semicolon or newline inside a quoted log payload cannot become an invocation boundary. Arbitrary prefix commands, functions, aliases, eval, variable-expanded program names and general shell programs are outside this bounded grammar; unsupported forms require independent trace review rather than a looser match. Log-only command quotations, --help, other scripts, absent flags, a wrong fingerprint or flags split across separate commands do not satisfy it. This bounded command-text check is not a general shell parser, a successful-exit check, OS attestation, job-copy validation, final-answer delivery proof, or semantic acceptance. Actual source-job replay, final assistant response review and access tracing remain independent.

Report the **16 declared local-process checks**, **32 literal guard groups**, **32 semantic criteria**, actual Skill reads and live API coverage separately. The helper-specific process check measures with-Skill conformance: an absent-Skill baseline cannot invoke the installed helper by design. A baseline process miss must not be counted as a business-answer failure or as evidence of Skill benefit or a gain in answer quality. Keep baseline comparisons on the original 32 literal groups and 32 semantic criteria separate, and report the actual native eligibility and check results for both sides honestly. This revision adds no mock, credential, setup, service prerequisite or human step. The known bash format is preferred over an unverified skill_script suggestion, but historical format alignment and local regex tests do not establish that the current native runner will bind or pass these new expectations. A fresh actual A16 platform run must verify native matching and independent final-source quality before any new pass or assertion-coverage improvement is claimed. Local process declarations cannot repair missing live API coverage by themselves.

The sixteen topics and substantive business standards are retained: definitions, calculations, field meaning, grain, association conditions, exceptions, versions, sources, ambiguity, complementary evidence, relevance, empty results, missing dates, conflicting rules, metric dependencies and context. Only the interactive clarification actions in the ambiguity and conflicting-rule cases are changed to a completed enumeration of supported alternatives and unknown applicability. The original API-workflow criteria remain intact in the archive. Optional supporting facts must be accurate when stated, but are not unrelated mandatory slots.

`evals/build_provided_evidence.py` builds the index and platform files deterministically from the archived original definitions and their grading-side index. It selects raw successful response documents by the existing evidence calls and de-duplicates them. It never copies mock command patterns, expected outputs or grading criteria into candidate prompts. Run `python3 -S evals/build_provided_evidence.py --check` to check generated inputs without changing files; omit `--check` only while authoring. This helper does not run candidates, models or APIs, and does not score answers.

Keep the grading-side index, source definitions, expected outputs and scores hidden from candidates. Give a candidate only its generated prompt, the applicable installed Skill, and authorized interpretation references. A full repository mount still exposes grading files: a prompt prohibition is not OS isolation. A host must restrict accessible files/tools and record the actual candidate output and access trace before claiming an uncontaminated result.

Final-answer semantic acceptance is defined by each `expected_output`, independently reviewed against the actual candidate answer and supplied evidence. Semantically equivalent phrasing is valid. Each new task also has nonempty native response checks in the observed `contains_any_count` format, with `min_count` equal to the number of listed values. These strict literal guards check requested source excerpts, exact field names/titles and output sections, without optional keyword alternatives. They do not prove correct relationships, negation, applicability, uncertainty handling or freedom from invented facts. The empty-evidence task can check only its topic and output sections because it has no source clause. Report literal-guard results separately from semantic accuracy. Without an actual completed semantic assessment, semantic accuracy remains ungraded even if every literal guard passes. The definitions do not invent an AgentHub automatic semantic-grader schema. Their explicit target-Skill load instruction and trigger declaration force invocation for fixed-Skill answer-quality evaluation, not Skill discovery or uncued natural-trigger accuracy. A new platform integration run is needed to assess v7 native local-process matching, final delivery and all-claims grounding. Native counts alone do not establish semantic acceptance; each independent review above applies only to its actual run. This suite measures evidence use, not raw retrieval recall, API invocations, SDK readiness, live authorization or real-service ranking. It may change capability coverage and does not promise the former 91.67% coverage or publication-gate acceptance.

The observed AgentHub report labeled empty expectations as `0/0` and assumed a pass. Such platform bookkeeping is not evidence of semantic correctness; without an actual semantic assessment, report answer quality as ungraded.

## Archived API-workflow and component regressions

The original sixteen knowledge-use API workflows and three supplementary capability workflows are preserved in the archived API workflow scenario directory. `evals/knowledge-usage.json` and `evals/platform-coverage.json` retain their original questions, criteria, identities and calls, point to these archived files, and explicitly mark them inactive as platform suites. The three supplementary tasks cover base catalogs and metadata, point catalogs and pagination, and focused derived retrieval. They do not enlarge the sixteen-question answer denominator.

These original workflows still require a host that actually provides connection context, SDK or CLI readiness, synthetic identity, mock interception and network isolation. Their `host_context` and `param_kv` fields do not establish that injection occurred. A mocked preflight response does not prove installation or authentication. Missing prerequisites are setup failures, not answer scores. Any constructed client must use an endpoint permitted by the unchanged endpoint policy; do not enable localhost or disable endpoint validation to make a test run.

Mocks represent logical calls through the normal `context_graph.py` entry point, shared by SDK and CLI modes. Details are reusable and order-independent; `times` describes availability, not a required call count. Preserve original Query, returned composite identities and cursor strings. A final rejection route prevents a configured mock from silently supplying unrelated evidence, but glob routing alone does not enforce authorization, provenance, budgets or network isolation. The host must validate those separately. Complete catalog pagination does not prove complete knowledge content or business rows.

Archived Python-helper expectations use `cloud_interaction.method: bash`, matching the recorded platform-generated Python example; the recorded direct aliyun example uses `aliyun_cli`. These examples are not the complete platform schema. Method alignment and local replay tests do not prove interception, setup readiness, semantic grading compatibility or the cause of historical timeouts.

The earlier fifteen fixtures in the archived component scenario directory remain component regressions covering all five read-only Actions, parameters, catalogs, pagination, focus, errors/retries and deterministic TSV calculations. Older design sets in the legacy design directory remain archived design notes. Neither archive is an additional active answer-evaluation suite.

Local validation runs `python3 -m pytest tests/test_provided_evidence.py tests/test_knowledge_usage.py tests/test_platform_coverage.py tests/test_component_scenarios.py`. It checks evidence export, distinct identities, preserved criteria, optional detail order, returned identities, command routing and shared SDK/CLI response contracts. It does not execute a model or establish AgentHub acceptance.

## Trigger metrics and historical reports

Every routing definition also carries nonempty grading-side forbidden strings covering human or connection requests, nested or alternative business execution and SQL/writes, API/network access, runtime/SDK/CLI/installation, credential/configuration reads, and evaluation/gold access. A correct loading polarity alone cannot establish a passing routing outcome when any forbidden behavior occurs. Assess those behaviors against the actual candidate execution and trace; these declared limits and empty response checks do not themselves prove compliance or grade explanation semantics.

The active trigger definitions are thirty-nine **cued routing-only v3** tasks, separately named `cued-routing-v3-positive-*` and `cued-routing-v3-negative-*`, with new deterministic UUIDs and `R01`-`R39` platform paths. Their context and post-request delivery reminder enforce three ordered steps: internally classify the nested request from installed names and descriptions without replying; if an applicable installed Skill exists, actually read its advertised entry point now using `read_file` or a host read-only Skill-loading tool; then give one final route with the actual load or no-load outcome and stop. This read is explicitly permitted and required, not business-procedure execution. Stopping after metadata alone is insufficient for an applicable installed Skill. Negative intent or unavailable applicable Skill requires no instruction load. Metadata-only identification suffices solely for unrelated alternatives. Read-only business or warehouse knowledge retrieval, supplied-evidence interpretation, definition comparison, unknown facts and knowledge catalogs apply even without a product name. Creation, uploads, editing, grants, internal BFF calls, SQL execution, scheduler operations and runtime execution/diagnosis are excluded. The wrapper does not make excluded intents applicable. The nested request is classification data, not execution authorization. There is no business answer, business-procedure execution, network/API access, SDK/CLI/runtime check, dependency installation, credential read, alternative Skill loading, directory search, or human follow-up. Neither context nor reminder names the target Skill.

`evals/triggers.json` retains the original twenty positive and fifteen negative polarities and leaves thirty-four original requests and rationales unchanged. The former R19 generic asset-listing request was explicitly clarified in v2 as listing visible DataWorks knowledge bases and one base's knowledge-point catalog; its original prompt, rationale and archive identity remain in revision provenance. Four positive requests introduced in v2 cover the current description's metric definitions/calculation rules/fields/relationships/documents, already-supplied Context Graph interpretation, comparison of documented definitions, and unknown facts/gaps. They carry current-description provenance, not invented archived records. All thirty-nine current requests, polarities, rationales and provenance remain unchanged in v3, including their v2 introduction metadata. They need no actual business evidence because candidates classify the nested intent without answering it. Only the business-execution forbidden rule is clarified to permit the required entry-point read; the other five forbidden strings remain exact. All thirty-five original natural-trigger definitions, their registry and source commit/hash index remain byte-identical in the archived natural trigger scenario directory. The nineteen original API-workflow archives also remain unchanged. Cleanup is limited to known superseded generated R35 v1 and R39 v2 paths; no archive is removed. Candidate prompts must not load the grading-side registry or archives. Negative cases must not load the tested Skill; metadata-only identification of another capability does not authorize loading or executing it.

Run `python3 -S evals/build_cued_routing.py --check` to verify deterministic generated routing definitions without modifying files. It runs no model and grades no outcomes. Trigger expectations retain loading polarity; empty response checks do not grade explanation semantics. These new definitions remain `not_run` until actual execution. Report cued routing separately from uncued natural-trigger accuracy, supplied-evidence answer quality, API workflow correctness and SDK availability. The active catalog has **70 tasks**: sixteen supplied-evidence v7 tasks, twenty-four positive routing v3 tasks, fifteen negative routing v3 tasks, and fifteen unattended workflow scenarios. Exclude supplied-evidence tasks when counting routing polarities. These instruction revisions do not establish measured phrase coverage or repair native API coverage.

Trigger recognition is separate from business-answer correctness. Natural business prompts can cause a platform executor to run the entire workflow, even when an expected-output note calls the task trigger-only. A maintained routing-only task must put the stop condition in candidate-visible execution context. If the candidate is explicitly asked to route and load a Skill, report cued routing rather than uncued natural-trigger accuracy. Keep original requests and polarities for comparison; do not claim phrase coverage or trigger success from definitions alone.

The supplied report dated 2026-11-17 21:43 CST selected 78 tasks from historical requests at commit `e75f9bc`; 73 timed out. It passed capability coverage at 91.67%, while execution failed. Several visible samples stopped in runtime checks or setup before retrieval; one source-attribution candidate then read a mock definition and answered from it. Those observations justify self-contained inputs and stricter separation of candidate evidence from grading materials. They do not establish one cause for every timeout.

Earlier forced-load local model results measured synthetic evidence use, not the AgentHub shell executor, discovery, SDK readiness, mock interception or current grading compatibility. Never convert skipped checks, empty response checks, setup failures or definition validation into a platform PASS. Report raw retrieval, supplemented coverage, workflow correctness, supplied-evidence answer quality and trigger routing separately.

## Workflow and isolation boundary

1. The grading side stores the question/scoring file with role=reference and runs prepare.
2. Give the candidate only questions.json in the new directory: question IDs, original prompts, region, base scope, focus objects, and necessary dataset/run/mode identifiers.
3. The host runs the candidate, saving its original text, optional structured facts, and access trace. The grading side runs grade on that actual output.

Prepare rejects every existing output directory, including empty ones. It copies no reference file, gold, must, expected, facts, workbook path, scoring rule, or extension field. Context exports only region, KnowledgeBaseIds, and FocusObjects. The question author remains responsible for prompt contents; the tool cannot detect answers embedded in prompts/IDs.

**Copying question files does not provide isolation.** The host must separately restrict mounts, tools, network, and conversation history so candidates cannot read grading references, source tables, or old answers. Do not mount an entire example directory for a candidate. Roles and traces are submitter declarations. The tool has no trusted-host attestation verifier; even a declared complete/clean trace produces host_isolation=not_verified and pure_api_acceptance=not_qualified, never pure-API acceptance PASS.

api_only means only question context and APIs are intended for the run. api_with_attachments additionally permits task attachments, requires separate assessment, and does not qualify as pure-API acceptance. The report lists reference/scoring-rule/source-workbook access explicitly. Attachment mode does not turn workbook access into API evidence. Missing, empty, or incomplete traces cannot qualify either.

## Minimal file formats

All examples are synthetic. Candidate and trace data below are handwritten demonstrations, not proof of model execution, API access, or isolation. Create a grading directory and save these three JSON documents under the names shown. Prepare creates a separate candidate-visible directory.

`reference.json`:

```json
{
  "schema": "context-graph-reference-v1",
  "role": "reference",
  "dataset_id": "synthetic-demo",
  "run_id": "run-001",
  "mode": "api_only",
  "questions": [
    {
      "id": "q1",
      "prompt": "What is the demo metric threshold?",
      "context": {
        "region": "cn-beijing",
        "KnowledgeBaseIds": [
          "kb-demo"
        ]
      },
      "facts": [
        {
          "subject": "metric-demo",
          "predicate": "threshold",
          "value": {
            "type": "number",
            "value": 8
          },
          "evidence": {
            "KnowledgeBaseId": "kb-demo",
            "Type": "GRAPH",
            "Id": "node-demo"
          }
        }
      ],
      "must": [
        "8",
        "8"
      ]
    }
  ]
}
```

`candidate.json`:

```json
{
  "schema": "context-graph-candidate-v1",
  "role": "candidate",
  "dataset_id": "synthetic-demo",
  "run_id": "run-001",
  "mode": "api_only",
  "input_sha256": "REPLACE_FROM_PREPARE",
  "source": {
    "kind": "model_run",
    "id": "synthetic-output-001"
  },
  "answers": [
    {
      "id": "q1",
      "answer": "The demo metric threshold is 8",
      "facts": [
        {
          "subject": "metric-demo",
          "predicate": "threshold",
          "value": {
            "type": "number",
            "value": 8
          },
          "evidence": {
            "KnowledgeBaseId": "kb-demo",
            "Type": "GRAPH",
            "Id": "node-demo"
          }
        }
      ]
    }
  ]
}
```

Answer is the actual candidate text and may be empty. Facts may be omitted/empty; never substitute reference answers for the candidate. source.kind/source.id record output provenance, such as model_run and the host artifact ID, without secrets or sensitive paths. Candidate top level, answer rows, facts, and evidence accept only the fields shown.

`trace.json`:

```json
{
  "schema": "context-graph-trace-v1",
  "role": "trace",
  "dataset_id": "synthetic-demo",
  "run_id": "run-001",
  "mode": "api_only",
  "input_sha256": "REPLACE_FROM_PREPARE",
  "complete": true,
  "events": [
    {
      "kind": "question_bundle",
      "resource": "questions.json"
    },
    {
      "kind": "api",
      "resource": "RetrieveKnowledgePoints"
    }
  ]
}
```

Each access event contains only kind and nonempty resource. Supported kinds: api, question_bundle, attachment, reference, source_workbook, scoring_rules. Record all accesses, not only successful APIs. Complete means the submitter declares the trace complete, not that the tool verified it. The tool cannot recognize a reference mislabeled as question_bundle or discover omitted accesses; declared_clean means only that the declaration shows no contamination. Output includes trace SHA256/status/reasons, not resource contents.

## Commands

Run from the skill root. Set EVAL_DIR to the grading directory containing the three example JSON files. candidate-input must not already exist:

```bash
EVAL_DIR=/tmp/context-graph-evaluation-demo
python3 evals/evaluate.py prepare \
  --reference "$EVAL_DIR/reference.json" \
  --output-dir "$EVAL_DIR/candidate-input"
```

The returned input_sha256 hashes the **raw UTF-8 bytes** of generated questions.json. The host records it in candidate/trace to bind this input. For handwritten examples only, replace placeholders with the standard-library command below. In real runs, the host sets these bindings while recording actual output; never use it to rewrite answers:

```bash
python3 - "$EVAL_DIR" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

directory = Path(sys.argv[1])
input_hash = hashlib.sha256((directory / "candidate-input/questions.json").read_bytes()).hexdigest()
for name in ("candidate.json", "trace.json"):
    path = directory / name
    value = json.loads(path.read_text(encoding="utf-8"))
    value["input_sha256"] = input_hash
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
python3 evals/evaluate.py grade \
  --reference "$EVAL_DIR/reference.json" \
  --candidate "$EVAL_DIR/candidate.json" \
  --trace "$EVAL_DIR/trace.json" \
  --output "$EVAL_DIR/report.json"
```

Trace is optional; omission reports trace_missing. Output is optional, defaulting to stdout; an explicit path creates a new file and never overwrites reports/inputs. Exit 0 means the offline check finished, **not that the candidate is correct or passed pure-API acceptance**. Invalid input, mixed roles, misaligned provenance, or file conflicts return 1. Input errors use fixed safe messages, never input dumps.

Each input must be a regular file, at most 2 MiB. Reject directories, FIFOs, and other special files. Open nonblocking, check the actual descriptor's type/size, then read within bounds. Platforms lacking nonblocking open fail safely, without a potentially blocking fallback. Reject duplicate JSON keys, NaN, Infinity, overflowing floats, and invalid JSON. Question sets have 1-1000 unique IDs; each question has at most 1000 structured facts. Reference and candidate need different schemas, roles, files, and contents; do not swap roles, reuse paths, or use hard links. Their question-ID sets must match exactly. dataset/run/mode and question-bundle hash must match; changed questions/visible call context invalidate old candidates. Changing internal reference scoring rules does not change the bundle hash but does change reference-file provenance.

This offline helper has been validated only on macOS, not accepted on Linux/Windows. Platforms without O_NONBLOCK reject input.

## Metrics and evidence identities

structured_assertion_coverage has scope=evaluated_structured_assertions_only. total_assertions counts all reference assertions. Matched counts assertions with a matching candidate fact; evaluated counts reference assertions for questions with candidate structured facts. needs_semantic_review separately counts assertions with only text/no automatically checkable facts. Thus total_assertions=evaluated+needs_semantic_review.

Ratio is matched/evaluated, null when nothing is automatically checkable, not factual accuracy 0%. With two reference assertions, one structured match and one text-only candidate: total_assertions=2, evaluated=1, matched=1, needs_semantic_review=1, ratio=1.0. Only the automatically checked subset has 100% coverage; one assertion still needs semantic review. Do not label pending assertions wrong or hide them behind that subset ratio.

Matching rules:

- Subject and predicate must match exactly; never join answers across subjects.
- value.type is number, boolean, text, or id. Compare numbers numerically: 8 does not match 18, string "8", ID "node-8", or boolean; 8 and 8.0 are numerically equivalent. Booleans are not numbers. Keep integer literals as integers. For decimal/exponent notation, accept only safe round trips: the original decimal value must equal the parsed float's shortest decimal representation, checked with Decimal. Accept 0.1/8.0; reject 1e-999, 0.10000000000000001, and 9007199254740993.0 rather than underflowing/rounding into a match. Exact integer 9007199254740993 remains valid; do not silently convert unsupported numbers to strings/other types.
- Text matches exactly by default. Only a reference value with type=text may explicitly add `"aliases": ["example alias"]`. Do not translate, case-fold, or infer aliases automatically. Type=id accepts no aliases; never rewrite city IDs as names.
- Evidence contains exactly KnowledgeBaseId, Type, Id, all matching exactly. Type is GRAPH/WIKI/KNOWLEDGE_CONTENT. Identity validation does not prove that an actual API returned the evidence.

Use Decimal(str(value)) for normalized decimal number comparisons, not Python mixed integer/binary-float equality. Thus 1e23 equals exact integer 100000000000000000000000, not 99999999999999991611392. Swapping reference/candidate number representations preserves the result.

For each question, report matched/not_matched/needs_semantic_review in reference assertion order. If structured candidate facts exist but an assertion has no match, mark not_matched. Without structured facts, mark needs_semantic_review. Wrong subjects, relationships, or evidence cannot match.

References are nonexhaustive. Candidate facts with no matching reference count as ungraded_candidate_facts, not automatically false or proof of complete precision. Structured facts are submitter assertions; the tool does not verify consistency with answer text. Always retain semantic_review=required; completeness, contradictions, organization, and API behavior need semantic/trace review.

Optional must retains separate **legacy coverage**, deduplicating literal terms per question. ASCII numbers/IDs cannot match inside longer ASCII numbers/IDs. This metric does not handle semantics, subjects, evidence, negation, or guarantee tokenization around non-ASCII numeral contexts. It is not a semantic score, retrieval recall, end-to-end accuracy, or factual accuracy, and cannot replace structured/manual review. Without must, its ratio is null.

Keep legacy_hit, reference aliases, structured matching, prepare-visible fields, and statistical definitions unchanged. Without a historical run's original scoring implementation, do not claim the legacy metric reproduces that external report, or relax literal rules to manufacture a perfect score.

## Import an independent semantic-review declaration

grade --semantic-review PATH imports review results actually completed by a human/model; it does not run a reviewer or generate scores. Candidates still cannot read reference/review files. Once candidate output is fixed, the grading side independently reviews intent, required fields, relationship subjects, state interpretations, omissions, and contradictions, then submits the declaration. Reviewer labels do not prove identity, independence, or host isolation. The tool always reports verified_by_tool=false; actual semantics are not verified by this helper, and pure_api_acceptance remains not_qualified.

Without a review file, declared_semantic_review.status=not_provided and mean_score=null. Never rename legacy/structured coverage as a semantic score. Per-question semantic_review=required remains. The following is a **handwritten format demonstration**, not an actual review, score, or acceptance artifact:

```json
{
  "schema": "context-graph-semantic-review-v1",
  "role": "semantic_review",
  "dataset_id": "synthetic-demo",
  "run_id": "run-001",
  "mode": "api_only",
  "input_sha256": "REPLACE_FROM_PREPARE",
  "candidate_sha256": "REPLACE_FROM_CANDIDATE_BYTES",
  "reference_sha256": "REPLACE_FROM_REFERENCE_BYTES",
  "reviewer": {
    "kind": "human",
    "id": "synthetic-reviewer"
  },
  "questions": [
    {
      "id": "q1",
      "status": "reviewed",
      "score": 80,
      "reason": "Handwritten demonstration; no semantic review was actually performed.",
      "factual_errors": 0,
      "missing_required_items": 1
    }
  ]
}
```

Save it as semantic-review.json in the existing demonstration directory. The following binds actual bytes of three files; it generates no scores and rewrites no candidate. Real workflows record these bindings on the grading side during review:

```bash
python3 -S - "$EVAL_DIR" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

directory = Path(sys.argv[1])
path = directory / "semantic-review.json"
review = json.loads(path.read_text(encoding="utf-8"))
for field, name in (("input_sha256", "candidate-input/questions.json"),
                    ("candidate_sha256", "candidate.json"), ("reference_sha256", "reference.json")):
    review[field] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
python3 -S evals/evaluate.py grade --help
python3 -S evals/evaluate.py grade \
  --reference "$EVAL_DIR/reference.json" \
  --candidate "$EVAL_DIR/candidate.json" \
  --semantic-review "$EVAL_DIR/semantic-review.json"
```

Python calls retain grade(reference_path, candidate_path, trace_path=None), with optional fourth semantic_review_path=None. The report adds declared_semantic_review separately without merging/overwriting legacy, structured, or acceptance fields. Review inputs use the same 2 MiB regular-file/nonblocking/duplicate-key/finite-number checks. Errors expose only fixed safe messages, never invalid content.

- Top level accepts only shown fields. dataset/run/mode and all three hashes must match actual grade provenance. Changed candidate/reference bytes invalidate old reviews.
- Reviewer contains only kind=human|model and a nonsecret nonempty id label. Question IDs must exactly cover the original set, with no duplicates, omissions, or extras. Preserve original question order in output.
- Each row has only id/status/score/reason/factual_errors/missing_required_items. Reviewed requires a finite nonboolean score from 0 to 100, a nonempty reason, and nonnegative integer error/omission counts. Reject 100 with any positive error/omission count.
- insufficient_evidence requires score=null. Error/omission counts may be null or known nonnegative integers; do not invent a zero score. Report reviewed/total coverage and unknown_count. With any unknown question, overall mean_score, score_sum, and exact_100 are null; a reviewed subset's 100 cannot become a whole-set score.
- When all questions are reviewed, emit mean_score/score_sum as strings and question_count as the total. Preserve score_sum/question_count as exact numerator/denominator. Use sufficient Decimal precision with downward truncation; never round a repeating mean to 100. exact_100 is true only if every original score is exactly 100 and every error/omission count is zero. For example, 100 and 99.99999999999999 average to string `99.999999999999995`, not 100.

## Synthetic development regressions and execution status

The archived answer-regressions design set covers fields, sets, hops, state boundaries, denominators, description mapping, unknowns, batch reuse, and independent review. It is excluded from the active knowledge-use baseline. Every case remains execution_status=not_run: no model was executed. It contains no original benchmark answers and is not direct grade input. Readable JSON or validator success is not behavioral success. Report model outcomes only after actual execution with saved output/provenance/review. Unit tests are actual offline tool tests, still not model/live acceptance.

Production field/set/calculation validation differs from semantic scoring; use the production answer workflow routed from the skill entry point. Generate contracts/bindings internally, repair original read values at most twice, and let the CLI recompute/render completely. It cannot prove intent, label meaning, or arbitrary natural-language correctness.

## Hashes and report boundaries

Provenance records actual candidate source, raw candidate-byte SHA256 (candidate_sha256), SHA256 of ordered {id, answer} JSON (candidate_text_sha256), and raw reference-byte SHA256 (reference_sha256). Text hashes use the bundle's canonical format: UTF-8, sorted keys, two-space indentation, original non-ASCII text, and one trailing newline. Also record input_sha256 and optional raw trace SHA256.

These hashes identify which candidate/reference/input produced a result and prevent presenting a reference's score as a candidate's score. They do not prove authorship, absence of gold access, or effective host isolation. If historical sessions lack actual candidate text, complete traces, and trusted isolation evidence, reconstructed declarations cannot restore pure-API acceptance.
