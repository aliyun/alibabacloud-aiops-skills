# Endpoint Routing & Region Hard Rules (MANDATORY)

> This file is the sole detailed implementation version of the three Region-related hard rules in [SKILL.md -> Core Workflow](../SKILL.md). The Agent **must** satisfy all constraints below before any `aliyun eflo-controller *` CLI invocation.

---

## 1. Endpoint and Region same-value hard rule

Every `aliyun eflo-controller` CLI invocation **must** explicitly carry the `--endpoint eflo-controller.<region>.aliyuncs.com` parameter, where `<region>` must be replaced with the real Alibaba Cloud Region ID chosen by the user (e.g., `cn-hangzhou` -> `--endpoint eflo-controller.cn-hangzhou.aliyuncs.com`).

`--endpoint` and `--region` must point to the **same** Region; any mismatch routes the request to the wrong gateway and returns `InvalidRegionId` / cross-domain errors.

This rule applies to **all** eflo-controller commands in this skill (Features 1-7, Diagnostic Task Monitoring, Command Quick Reference, and every example in references/*.md).

---

## 2. Region-required hard rule

When the user's request does **not explicitly specify** a Region:

1. It is **strictly forbidden** to run commands with the placeholder `<region>`, **strictly forbidden** to silently default to any concrete value such as `cn-hangzhou` / `cn-wulanchabu`, and **strictly forbidden** to reuse a Region left over from a historical session or the previous task.
2. The Agent **must** first force-ask the user via HITL to pick a concrete Region: it may call `safe_aliyun aliyun eflo-controller describe-regions --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou` to fetch the live list, or present options from the static fallback list in [supported-regions.md](supported-regions.md).
3. Before the user has made a choice, entering any subsequent flow is **forbidden** (including Features 1-7 and `describe-diagnostic-result` polling); even read-only queries require a Region first.
4. Once the user has given a Region, every `aliyun eflo-controller *` command in that session must fill **the same** Region ID into both `--endpoint` and `--region`; switching midway is forbidden.
5. **Sole exception**: `describe-regions` is a discovery-style query and may be called once with the fixed seed `cn-hangzhou` before the user has picked a Region, solely to present options; every other eflo-controller CLI must use the Region **explicitly chosen** by the user.

---

## 3. Multi-Region Enumeration intent hard rule

When the user's request is a **global inventory / cross-region enumeration** intent (trigger phrases include, but are not limited to: "diagnostic results of all my nodes", "list all my diagnostic history", "all diagnostic results / list all", "all my diagnostic tasks", and any other inventory intent not pointing at a specific Region):

1. The inventory CLIs of eflo-controller (`list-clusters` / `list-cluster-nodes` / `list-cluster-hyper-nodes` / `list-diagnostic-results` / `list-syslogs`, etc.) are all **region-level** APIs; no cross-region aggregation endpoint exists. It is **strictly forbidden** to answer after querying only `cn-hangzhou` or any single Region by default.
2. The Agent **must** first clarify the query scope via HITL (two-way pick):
   - **A. Iterate all Regions (recommended for inventory)**: first run `describe-regions` to obtain the account's available Region list, then **invoke the target inventory CLI once per Region**, merge the results, and present a summary table grouped by Region.
   - **B. Specify a single Region**: the user gives one concrete Region and the regular flow applies.
3. Choice A execution rules:
   - A single Region failure must **not** interrupt the whole iteration; the failure reason (`ErrorCode` + brief description) for that Region must be written into the corresponding summary-table row as a placeholder.
   - After all Regions have been iterated, the answer must explicitly note "iterated N Regions, of which M queries succeeded / K failed"; it is **strictly forbidden** to conflate "successfully iterated 0 records" with "iteration did not succeed".
4. Before the user has explicitly chosen A/B, entering any query is **forbidden**; once chosen, the session sticks to that mode.
5. This rule **covers only inventory / enumeration** intents; diagnosis / repair operations on a **specific single resource** still follow the single-Region flow.

---

## 4. Positive and negative examples

```bash
# ✅ Correct: endpoint and region share the same value (Hangzhou production domain)
aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
  --region cn-hangzhou

# ✅ Correct: diagnostic queries require the same consistency
aliyun eflo-controller describe-diagnostic-result \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
  --region cn-hangzhou \
  --diagnostic-id <did>

# ❌ Wrong: missing --endpoint
aliyun eflo-controller list-clusters --region cn-hangzhou

# ❌ Wrong: endpoint and region mismatch (triggers InvalidRegionId)
aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
  --region cn-wulanchabu

# ❌ Wrong: running with the placeholder when the user has not specified a Region
aliyun eflo-controller list-diagnostic-results \
  --endpoint eflo-controller.<region>.aliyuncs.com \
  --region <region>

# ❌ Wrong: user asks "all my diagnostic tasks" (global inventory) but the Agent silently queries only cn-hangzhou
#       — violates the Multi-Region Enumeration intent hard rule
aliyun eflo-controller list-diagnostic-results \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
  --region cn-hangzhou
```
