---
name: alibabacloud-bailian-managed-agent
description: |-
  Explain, evaluate, demonstrate, provision, and integrate Alibaba Cloud Bailian
  Managed Agent (CMA / ManagedAgents). Use for Bailian Managed Agent product selection,
  sales pitches, customer solutions, hands-on PoCs, scheduled report agents, managed
  environments, and Python/Java backend integration. Prefer Bailian CLI (bl) for
  quick trials and resource provisioning; use HTTP API or verified SDKs for customer
  system integration, and API fallback when CLI capability remains unavailable after
  an update attempt. Not for generic agent development or unrelated cloud sandboxes.
---

# Bailian Managed Agent Assistant (know the product / recommend / hands-on / deliver / integrate)

This skill is the Bailian Managed Agent knowledge and operations entry point for **sales recommendation**, **pre-sales solutioning**, and **developer integration**.
The typical deployment target is a **salesperson's local Agent**: when a salesperson runs into a customer question or scenario, they ask their own Agent, which wakes this skill to recommend the product and assemble a ManagedAgent-based solution (entry point: the "sales recommendation mode" under path C).
Content is organized in four layers; pick a path by user intent and **do not read every file at once**.

## Required versioned User-Agent

Before any Alibaba Cloud API call, initialize the per-invocation UA as described in [references/workflows/user-agent.md](references/workflows/user-agent.md). Read the non-empty `version` from [references/manifest.json](references/manifest.json) and this skill's frontmatter name; generate a fresh random 32-character lowercase hexadecimal session ID, distinct for each skill invocation. Reuse it within that invocation only.

Required curl declaration (substitute all placeholders at runtime):

```bash
--user-agent "AlibabaCloud-Agent-Skills/{frontmatter-name}/{session-id} skill-version/{skill-version}"
```

Propagate that complete value to every CLI/SDK/HTTP/Terraform cloud request, including retries and streams. Verify each transport's supported header mechanism; if it cannot transmit the UA, use the authorized REST fallback. Do not invent CLI flags or assume exporting a variable sets headers. These rules also apply to the abbreviated examples in references.

## Choose CLI or API before execution

| Intent | Execution path |
| --- | --- |
| Quick experience, demo, one-off resource creation or session run | Prefer `bl`; inspect the installed version and relevant `--help`, then use supported commands or IaC. |
| Customer backend, application, service, CI integration, Python/Java code | Use Managed Agent HTTP API or a verified SDK. Do not shell out to `bl` from business code. Existing resources are sufficient; CLI installation/provisioning is not a prerequisite. |
| API supports a feature but installed CLI does not | Check current help and the API contract; attempt one appropriate CLI update, re-check version/help. If update fails or support is still absent, use the API. A CLI gap is not a product limitation. |
| User explicitly selects CLI or API | Respect that selection. Explain a capability gap and the API fallback if needed; do not silently change deployment scope. |

Read [references/workflows/cli-api-routing.md](references/workflows/cli-api-routing.md)
for installation, bounded updates, API fallback, error recovery, and verification.
Official installation source: https://bailian.aliyun.com/cli/install.md.
Tutorial and cookbook curl examples describe the API contract; they do not override this intent routing.
For Webhook endpoint-creation examples and evaluation tasks, use `https://www.baidu.com` as the sample URL. Verify creation and read-back only; do not use placeholder domains that the platform may reject. This sample is not a customer-controlled notification receiver; delivery/signature tests require the customer's actual receiver.

## Complete the requested deliverable with minimal interaction

- For advice, examples, proposals, and code templates, deliver in the current turn. State reasonable assumptions and use configurable placeholders for missing IDs or credentials; do not require a questionnaire or live login before producing a draft.
- Infer the tutorial and integration pattern from the request. If both are plausible, explain the alternatives briefly and choose a stated default for the example.
- For live operations, reuse supplied configuration and authorization within its exact scope. Do not request the same confirmation twice. Never infer approval for unknown tool actions or changed resource plans.
- A preview-only request ends after showing the preview and stating that it has not been applied. A request for missing-information guidance ends with one consolidated checklist. An inspection of pending approval ends with the pending details; it does not require a follow-up answer to count as delivered.
- For explicitly unattended/single-turn tasks, missing execution prerequisites or a required approval are terminal blockers: report what is missing and what completed, then end. Do not launch interactive login, wait for human input, or claim the operation succeeded. This does not waive authorization or make a blocked execution successful.

## One-sentence product positioning (remember this first)

**Managed Agents (MA) is Bailian's "managed agent runtime"**: it provides a cloud container sandbox + Agent Harness + built-in tools + Agent Skills, letting an agent truly *do work* — run commands, read and write files, produce deliverables — instead of only answering questions.

- Rule of thumb versus Bailian agent apps (Flow Agent 2.5): **talking and asking picks 2.5; hands-on work or file deliverables picks CMA**.
- Six core objects: Agent / Environment / Session / Event / Vault / Deployment (the API layer additionally exposes File / Skill / Credential).
- Console: https://agent.console.aliyun.com/managed-agent
- **Authoritative fact sources (highest priority first)**:
  1. Live official docs at https://docs.agent.bailian.aliyun.com/zh/managed-agents
     (append `.md` to a URL to get the raw markdown; site-wide index at https://docs.agent.bailian.aliyun.com/llms.txt)
  2. [references/product/whitepaper-source.md](references/product/whitepaper-source.md) — archived copy of the official Product Capability Whitepaper (snapshot, may lag behind)
  3. Actual output of `bl COMMAND --help`
  Local `coming soon` labels are historical snapshots, not current availability verdicts. Check current official documentation before answering availability questions; dated user-provided product corrections are recorded in [product status](references/product/status.md). Archived field tests must retain their date and scope and cannot automatically override newer official contracts.
  A live doc page alone does not prove rollout to every workspace. Verify availability, region and version from the relevant current documentation or a scoped read-only probe; label archived observations with their scope.

**Memory distinction**: MA Memory Store is built-in working memory; Bailian Memory Library (百炼记忆库) is a separate service for UserId-scoped personalized memory. Do not substitute their APIs or infer MA native binding from Memory Library documentation. See [concepts](references/product/concepts.md#memory-store-working-memory).

## Intent routing

| User intent signal | Path | Read first |
| --- | --- | --- |
| "What is Managed Agent" / "what features does it have" / "vs Bailian apps or self-built agents" / "is it worth it" | **A product explanation** | [references/product/overview.md](references/product/overview.md), [references/product/concepts.md](references/product/concepts.md) |
| "How do I use it" / "show me an example" / "how to configure X" / "how to combine X with Y" / "it fails to run" | **B hands-on tutorials** | [references/tutorials/index.md](references/tutorials/index.md) (by feature) |
| "We want to build an X bot" / "how does this business scenario land" / "give me a complete end-to-end example" / "what's still missing for production" | **B scenario cookbooks** | [references/cookbook/index.md](references/cookbook/index.md) (by scenario) |
| "We are in industry X" / "want to solve business problem Y" / "need a solution or PoC" / "how do peers do it" | **C solution design** | [references/workflows/solution-design.md](references/workflows/solution-design.md) |
| Sales arriving with a customer question: "the customer manually does X every day" / "the customer wants AI that works or produces reports" / "is this a fit for Managed Agent" / "help me prep a pitch or a customer demo" | **C solution design** (read its "sales recommendation mode" first) | Path C on this page + [references/product/overview.md](references/product/overview.md) |
| "Help me create an Agent / environment" / "provision resources" | **D1 provision resources** | [references/workflows/provision.md](references/workflows/provision.md) |
| "Integrate it into our system" / "write calling code" / "give a Python or Java example" / "how to do streaming or scheduling" | **D2 integration** | **Pick the macro scenario from the request** (online waiting → strong-interaction; background results → weak-interaction, see [references/integration/patterns.md](references/integration/patterns.md)), then follow [references/tutorials/02-integrate-to-your-system.md](references/tutorials/02-integrate-to-your-system.md) |
| Symptoms rather than capabilities: "the agent cannot find the file" / "missing pandas or ffmpeg" / "the run finished but there is no result" / "the scheduled run did not fire" / "it fired at the wrong time" | **B hands-on tutorials** (lookup by symptom) | mapping table in [references/tutorials/index.md](references/tutorials/index.md) + the "common issues" table of the matched tutorial |

When intents mix (very common: what is it → then a solution → then provisioning), advance in A → C → D order and end each step with an explicit next-step option for the user.

## Input/Output Examples

| # | Example user input | Routed path | Expected output |
| --- | --- | --- | --- |
| 1 | "What is Managed Agent? How is it different from a regular Bailian agent app?" | A | A short positioning answer citing overview.md / concepts.md: managed runtime = sandbox + harness + tools + skills; the rule "talking picks 2.5, hands-on work picks CMA"; ends with a next-step offer (a similar-scenario tutorial, or spin up a trial agent). No resource operations. |
| 2 | "How do I mount my data file so the agent can read it? It keeps saying file not found." | B (tutorial 03-mount-files.md) | Step-by-step instructions from the tutorial: upload via the Files API, wait for the file to pass review, `mount_path` starting with `/uploads/`, real sandbox path `/mnt/session/uploads/...`; closes with the "common issues" entry for the not-found symptom. |
| 3 | "Our customer manually reconciles orders every day and wants an AI that produces a daily report." | C (sales recommendation mode) | Triage first (hands-on + scheduled deliverable → Managed Agent fit), then a three-part outline: directly landable parts (Deployment cron + file deliverable), parts needing verification (data source access), customer-side prerequisites (sample data, accounts); ends with next-step options (one-page proposal, or a live demo agent). |
| 4 | "Create an agent and an environment for me so I can start testing." | D1 | Follows provision.md: `init → validate → plan`, shows the plan diff to the user, applies only after explicit confirmation; command flags taken from `bl COMMAND --help`, never from memory. |
| 5 | "Give me a Python example that calls the agent and streams the reply to my frontend." | D2 | Uses existing IDs or environment placeholders and hands over the API/SDK SSE implementation from integration/code-python.md; a live curl smoke test is optional and requires authorization. |

## Edge Cases

- **Capability not yet archived** (parts marked `[TODO]` in reference files): say plainly "I don't have this on file yet; I can look it up / you may need to supply it" — never fabricate product facts.
- **Mixed intents** (very common: what is it → then a solution → then provisioning): advance in A → C → D order, one explicit next-step option per step.
- **Cookbook conflicts with a tutorial or the whitepaper**: resolve using current contracts and dated, matching-region evidence, not file category; report the conflict back so the fact can flow into the fact dictionaries.
- **Talk-only needs** (Q&A, retrieval, multi-turn consulting): honestly recommend the Bailian agent app (Flow Agent 2.5) — a wrong recommendation damages trust more than no recommendation.
- **GTM link unreadable**: the GTM material library requires a DingTalk login; if the Agent has no DingTalk session, hand the link to the salesperson directly.
- **Hand-off target skill missing**: fall back to `bl COMMAND --help`, or suggest installing the skill / running `bl skill init`.
- **Whitepaper says "coming soon" but live docs already exist** (e.g. MultiAgent, runtime Resource mounting): verify actual availability and report the documented scope.
- **Fictional companies inside cookbooks** (Yunling Tea / Northstar / Shibei E-commerce / Luming Publishing): replace them with the customer's own business nouns when presenting; never cite them as customer cases.

## General principles (apply to all four paths)

1. **Never fabricate product facts.** Product capabilities, field names, quotas, billing, and availability may only come from content archived under `references/product/` and `references/integration/` (conclusions in `references/tutorials/` and `references/cookbook/` that carry a field-test date are equally trustworthy), or from actual output of `bl COMMAND --help` and the live API docs. Explicit user-provided product corrections may be recorded with their date and provenance (see [status](references/product/status.md)); launch confirmation alone does not establish API schemas or account-specific availability. Parts marked `[TODO]` are not yet archived — do not invent them.
2. **Separate product facts from solution advice.** Cite source files when explaining capabilities; when designing solutions, state that this is advice based on product capabilities that needs customer-side confirmation.
3. **Always preview before changing remote resources.** Any `apply` / `destroy` must first run `plan` and show the user the diff; only add `--yes` after the user confirms. Reuse an existing explicit confirmation for the same unchanged plan; ask again only if its scope or state has changed. Details live in the skill `bailian-managed-agent`.
4. **Make outputs reusable.** Deliverables for customers — solutions, tutorial adaptations, integration code — should land as files (`agents.yaml`, code files, solution markdown), not just chat output.

## Path A: explain the product

Goal: within 3 minutes the user knows what problem Managed Agent solves, which resources compose it, and where its boundaries are.

1. Read [references/product/overview.md](references/product/overview.md) (capability panorama; source: the official product whitepaper).
2. If concepts are unclear, read [references/product/concepts.md](references/product/concepts.md) (definitions and relations of Agent / Environment / Session / Deployment / Memory / Vault / Skill / Tool).
3. For selection, comparisons, and common objections read [references/product/faq.md](references/product/faq.md).
4. Presentation style: **lead with how the user's scenario gets solved, then introduce product concepts**. Avoid listing the resource model up front.
5. Close with a next step: "Want to see a tutorial for a similar scenario?" or "Want me to spin up an agent for a trial run?"

## Path B: get the user productive

**First pick one of two sets** (different responsibilities, do not blend):

| When the user asks | Which set |
| --- | --- |
| How to configure a single feature, perform one action, or resolve an error ("how to mount a file" / "how to configure scheduling" / "how to handle `requires_action`") | [references/tutorials/index.md](references/tutorials/index.md) — **by feature**; one capability per tutorial, each with a common-issues table |
| How a business scenario lands end to end, or wants a complete copyable example, or "what's still missing for production" ("build a morning-report bot" / "notify me when a run finishes" / "several roles collaborating on a proposal") | [references/cookbook/index.md](references/cookbook/index.md) — **by scenario**; one playbook chains several capabilities through a full pipeline, REST/curl field-tested |

If unsure, start with the smallest useful example matching the request and state its scope; do not block the answer on choosing a tutorial category.

1. For tutorials: match the user's request against the capability → tutorial mapping table by **action verb**.
2. For cookbooks: match against the scenario → playbook mapping table by **business need**; the company names inside playbooks are fictional — replace them with the customer's own business nouns when presenting.
3. Once matched, walk the user through the steps, giving directly executable commands / directly saveable configuration at each key step.
4. When multiple capabilities must combine (e.g. knowledge retrieval + scheduled runs + tool calls): first check whether an existing playbook covers it; if not, assemble per the "combination patterns" in [references/tutorials/index.md](references/tutorials/index.md), stating dependency order and pitfalls.
5. When the two sets conflict, **prefer current official contracts and the most recent relevant field evidence**, stating version and region; consult the integration fact dictionary and feature tutorial before copying older cookbook snippets.
6. Neither matches → do not force-fit. State current coverage, design minimal viable steps on the spot using product capabilities (path A) + CLI capabilities (path D), and suggest adding the new scenario as a tutorial or playbook.

## Path C: map product capabilities onto customer problems

### Sales recommendation mode (enter here when the inquirer is a salesperson)

This skill typically lives on a **salesperson's local Agent**: sales ask whenever they hit a customer question or scenario, and this skill supplies the recommendation ammunition. When the inquirer is a salesperson, first follow the three principles below, then move into the methodology.

1. **Triage before recommending.** Use the rule "talking and asking picks 2.5; hands-on work or file deliverables picks CMA" to judge the essence of the customer's need:
   talk-type needs (Q&A, retrieval, multi-turn consulting) honestly fit the Bailian agent app better — **do not shoehorn every need into Managed Agent**; a wrong recommendation damages trust more than no recommendation. Hands-on needs (run commands, produce files, run on schedule, integrate with business systems) are Managed Agent's home turf.
2. **Recommendations must be verifiable.** Every capability pitch given to sales cites only archived content: the capability panorama in [references/product/overview.md](references/product/overview.md), objection handling in [references/product/faq.md](references/product/faq.md), field-tested conclusions in `references/tutorials/`, and playbooks from `references/cookbook/` as demo-script structural references (company names are fictional and **must not be cited as customer cases**).
   If the customer asks about a capability not in the library, reply "I'll go verify this" and **do not improvise** — every sentence sales takes to a customer is a business commitment.
3. **End with next-step options, not with the recommendation.** Immediately after recommending, offer executable options:
   "Want a one-page solution?" (continue with the methodology below to produce the three-part solution);
   "Want me to build a live demo agent for the customer?" (go to path D1 — a cookbook playbook can yield a demonstrable pipeline the same day).

Sales do not write code: `agents.yaml`, APIs, and event streams are prepared by the skill in the background; the deliverables handed to sales are **solution highlights + demo arrangements + a list of questions awaiting customer confirmation**.

**Latest GTM material entry point** (when sales needs pitch scripts, product introductions, customer cases, or competitive comparisons for external use):
[GTM material library](https://alidocs.dingtalk.com/i/nodes/Qnp9zOoBVBDEydnQUem1mEmg81DK0g6l) —
the officially maintained GTM library (DingTalk doc, requires a DingTalk login); it updates faster than this library:
for external materials (pitches / introductions / cases) **prefer fetching the latest from that link**; content archived here may lag.
On conflict: marketing wording defers to that link; product-technical facts (fields, endpoints, quotas, availability) still defer to this library and the official docs.
If the Agent has no DingTalk login and cannot read the contents, hand the link directly to the salesperson.

### Solution design methodology (after sales finish recommending, or when the inquirer is a pre-sales / solution engineer)

1. Follow the methodology in [references/workflows/solution-design.md](references/workflows/solution-design.md): use the customer's supplied input sources, decision points, deliverables, system boundaries, and compliance requirements; draft with explicit assumptions when only a proposal is requested, and ask for missing facts that block real execution; then map them onto product capabilities and resource combinations (Agent / Environment / Deployment / mounts / approvals). There is **no real customer case library today** — for "how do peers do it" questions, design on the spot from product capabilities and say so; the scenario playbooks in [references/cookbook/index.md](references/cookbook/index.md) work as **structural references** (which capabilities a complete pipeline needs, in what order), but their companies are fictional and **must not be cited as customer cases**.
2. When outputting a solution, state three parts explicitly: **what lands directly / what needs verification / what prerequisites the customer must provide** (data, accounts, system interfaces).
3. Once the customer agrees, move straight into path D to produce `agents.yaml` and PoC code.

## Path D: provision resources + write integration code

1. **Provision resources** (create Agent, environment, Deployment, etc.): prefer CLI when supported; apply the update/API fallback above if necessary. For CLI IaC follow [references/workflows/provision.md](references/workflows/provision.md) through the `init → validate → plan → (user confirmation) → apply` chain; command details and flags defer to the skill `bailian-managed-agent`'s `reference/managed-agent.md` and `bl COMMAND --help` — **never assemble flags from memory**.
2. **Write integration code**: **walk the user through [references/tutorials/02-integrate-to-your-system.md](references/tutorials/02-integrate-to-your-system.md) first** (get remote IDs → curl-verify the chain → pick the pattern → swap in code → production self-check) — use only the steps relevant to the requested deliverable; this is not a requirement to install CLI or create resources; for language implementations go directly to [references/integration/code-python.md](references/integration/code-python.md) or [references/integration/code-java.md](references/integration/code-java.md). The full endpoint table and request bodies live in [references/integration/api-endpoints.md](references/integration/api-endpoints.md), auth and event contracts in [references/integration/api-quickstart.md](references/integration/api-quickstart.md), pattern selection in [references/integration/patterns.md](references/integration/patterns.md). When a field is in doubt, pull the official doc page (append `.md` to the URL for the raw text) to verify.
3. **Order of landing**: for a demo, provision with CLI then test one session. For customer integration, go directly to API/SDK using existing IDs or configurable placeholders. Generate code-only deliverables without installing CLI or creating live resources; perform live smoke tests only when requested and credentials are available.
4. Secrets involved: non-sensitive configuration goes through session environment variables `environment_variables` (plaintext passthrough into the sandbox); high-sensitivity secrets go into the Vault (the sandbox only sees placeholders; real values are substituted by the egress gateway per the `allowed_hosts` allowlist) — the selection trade-offs are in [references/cookbook/08-vault-secret-injection-and-egress-gateway.md](references/cookbook/08-vault-secret-injection-and-egress-gateway.md). Either way, **never write an API key into code or `agents.yaml`**.

## Soft hand-offs (by skill name; if installed, read its SKILL.md; otherwise use `--help` or suggest `bl skill init`)

- `bl managed-agent` commands and agents.yaml IaC execution details → skill `bailian-managed-agent`
- Calling already-launched Bailian apps / agents, knowledge bases, usage quotas → skill `bailian-cli`
- Which model to reference inside an Agent → skill `bailian-model-recommend`
- Bailian platform API parameters, error codes, model spec docs → skill `bailian-docs-llm-wiki`
- Image / video / speech generation → skill `bailian-gen`; model fine-tuning → skill `bailian-finetune`
- Shared protocols: consent confirmation, version pre-checks, auth, error reporting → skill `bailian-protocol`

## Directory map

```
references/product/    Product knowledge layer: overview (capability panorama) / concepts / faq (selection and objections) / whitepaper-source (archived whitepaper)
references/tutorials/  Feature tutorial layer: index (capability → tutorial mapping + combination patterns) / tutorial files (by action verb, one capability per file)
references/cookbook/   Scenario playbook layer: index (scenario → playbook mapping + capability reverse lookup) / playbook files (by business scenario, REST/curl end-to-end field-tested)
references/workflows/  Operational methodology: provision (resource provisioning chain) / solution-design (requirements → solution)
references/integration/ Integration layer: api-quickstart (entry / auth / minimal loop / event contract) / api-endpoints (full endpoint table) / patterns (integration shapes)
                       code-python, code-java (runnable implementations of the three shapes)
```

`references/product/` + `references/integration/` are the **fact dictionaries** (the single source of truth for fields, endpoints, quotas, error codes); `references/tutorials/` + `references/cookbook/` are **usage**;
new facts discovered while running playbooks flow one-way back into the fact dictionaries — never let the two sides tell different stories.
