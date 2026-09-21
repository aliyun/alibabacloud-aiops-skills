# Region Required Hard Rule (MANDATORY)

> This file is the sole detailed implementation of [SKILL.md → B-6 Region Required](../SKILL.md). The Agent **must** satisfy all constraints below before any `aliyun eflo-controller *` CLI call.
>
> **Note**: the endpoint is auto-derived by the aliyun CLI from `--region` (standard pattern `eflo-controller.<region>.aliyuncs.com`); an explicit `--endpoint` is **neither needed nor desired**, so the Agent never exposes internal routing details to the user-facing surface.

---

## 1. Region Required Hard Rule

When the user's request does **not** explicitly specify a Region:

1. **Strictly forbidden** to run commands with the placeholder `<region>`, **strictly forbidden** to silently default to any concrete value such as `cn-hangzhou` / `cn-wulanchabu`, **strictly forbidden** to reuse a Region left over from a previous session or task, **strictly forbidden** to persist it in an environment variable as session-level implicit state.
2. **Must** first force a HITL question asking the user to pick a concrete Region: you may call `safe_aliyun aliyun eflo-controller describe-regions --region cn-hangzhou` to fetch the live list, or offer options from the static fallback list in [supported-regions.md](supported-regions.md). **Before presenting options, filter out every test region matching the `*-test-*` pattern**; test regions must **never** appear in user-visible option lists (see [detailed-rules.md Rule 5](detailed-rules.md#agent-output-surface-control)).
3. Until the user has chosen, **no** subsequent flow may start (including Features 1–11, `describe-task` polling, `CreateInstance` ordering); even read-only queries require a Region first.
4. Once the user has given a Region, every `aliyun eflo-controller *` command in that session must explicitly pass the **same** Region ID as `--region`; the Agent must not unilaterally switch Region mid-session — if the user asks to switch → re-run HITL confirmation.
5. **Sole exception**: `describe-regions` is a discovery query (lists available Regions) and may be called once with the fixed seed `cn-hangzhou` before the user has chosen, purely to present options; every other eflo-controller CLI must use the Region **explicitly selected** by the user.

---

## 2. Positive / Negative Examples

```bash
# ✅ Correct: region explicitly specified, endpoint auto-derived by the CLI
aliyun eflo-controller list-clusters --region cn-wulanchabu

# ❌ Wrong: running with the placeholder because the user did not specify a Region (violates Region Required)
aliyun eflo-controller list-clusters --region <region>

# ❌ Wrong: silently defaulting to cn-hangzhou because the user did not specify a Region (violates Region Required)
aliyun eflo-controller list-clusters --region cn-hangzhou

# ❌ Wrong: storing region in an environment variable as session-level implicit state (violates §1.1)
export LJ_REGION=cn-wulanchabu
aliyun eflo-controller list-clusters --region "$LJ_REGION"

# ❌ Wrong: explicitly concatenating --endpoint (violates the SKILL.md A.3-13 anti-pattern of leaking endpoint construction details)
aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-wulanchabu.aliyuncs.com \
  --region cn-wulanchabu

# ❌ Wrong: user asks "which clusters do I have?" (no Region given) and the Agent silently defaults to cn-hangzhou
#       —— violates §1.1 Region Required hard rule
#       Correct approach: HITL asks the user to explicitly pick one Region from the available list, then query with it
aliyun eflo-controller list-clusters --region cn-hangzhou
```
