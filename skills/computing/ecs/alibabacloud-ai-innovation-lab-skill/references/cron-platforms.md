# Scheduled Task Scheduler Implementation (AI Innovation Lab)

The main SKILL.md provides the "scheduling task contract" (platform-agnostic YAML configuration). This document provides specific implementation methods for 5 execution environments, including token injection constraints.

## Scheduling Task Contract (Repeated for Reference)

```yaml
name: "AI尝鲜实验室-周推"
cron:
  "1": "0 10 * * 1"       # Every Monday 10:00
  "2": "0 17 * * 5"       # Every Friday 17:00
  "3": <ask the user>      # User-provided time, convert to 5-field cron
timezone: "Asia/Shanghai"
missed_run_policy: run_latest   # If multiple runs are missed, only run the latest one to avoid weekly report avalanche
delivery: <ask the user>        # DingTalk group robot webhook / system notification / keep in task history
action: |
  Fetch https://www.aliyun.com/daily-act/ecs/ai-innovation-lab, generate this week's recommendation
  markdown following the ai-innovation-lab skill output specification (including welcome intro +
  cloud computing emphasis + official homepage link + statistics sentence +
  table of top 4 items updated in last 30 days + 2 closing interaction sentences).
  If page fetching fails or DOM parsing returns 0 items, automatically fall back to
  https://ai-innovation-lab.oss-cn-beijing.aliyuncs.com/ai-innovation-lab.json,
  take the top 4 service_ids by meta.recommend_order as recommended projects.
  Deliver to user according to delivery configuration upon completion.
```

Select the corresponding implementation based on the current agent:

## ① QoderWork (Default)

Call `qoder_cron` MCP with parameters:

```json
{
  "action": "add",
  "job": {
    "name": "AI尝鲜实验室-周推",
    "schedule": { "kind": "cron", "expr": "0 10 * * 1", "tz": "Asia/Shanghai" },
    "missedRunPolicy": "run_latest",
    "payload": { "kind": "agentTurn", "message": "<content from the action field above>" }
  }
}
```

## ② Hermes Agent

Skills are located at `~/.hermes/skills/`, scheduling uses the `cronjob` tool (or `hermes cron create` CLI). Recommended in-agent invocation:

```
Use the cronjob tool to create:
schedule="0 10 * * 1", timezone="Asia/Shanghai"
preload_skill="ai-innovation-lab"
prompt="<content from the action field above>"
delivery=<user-specified channel>
```

If the user prefers CLI prompt, provide:

```
hermes cron create "0 10 * * 1" --tz Asia/Shanghai --skill ai-innovation-lab --prompt '<action>'
```

### Token Injection Constraints (Hermes)

Hermes authentication tokens (e.g., `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / `TOOL_GATEWAY_USER_TOKEN` / `DASHSCOPE_API_KEY` and other provider keys) are automatically loaded from `~/.hermes/.env` into worker processes spawned by the cron scheduler — **no need** to manually pass `--env` in the `hermes cron create` command.

If this skill requires business-layer tokens (e.g., `GATEWAY_TOKEN`), inject via one of the following two methods:

- Declare `required_environment_variables: [GATEWAY_TOKEN]` in the skill's `SKILL.md` frontmatter, and Hermes will automatically forward these variables to Docker terminal sessions
- Or set `TERMINAL_DOCKER_FORWARD_ENV='["GATEWAY_TOKEN"]'` in `~/.hermes/.env` to explicitly list them

Never write tokens in plaintext in the `hermes cron create` command string itself — use `.env` for configuration and variable names for references. This is the official Hermes approach. Reference: [Hermes Environment Variables Documentation](https://hermes-agent.nousresearch.com/docs/zh-Hans/reference/environment-variables).

## ③ OpenClaw

Scheduling uses `openclaw cron add` CLI / equivalent tool:

```
openclaw cron add \
  --name "AI尝鲜实验室-周推" \
  --schedule "0 10 * * 1" \
  --tz Asia/Shanghai \
  --on-miss run-latest \
  --prompt "<content from the action field above>"
```

### Token Injection Constraints (OpenClaw)

Before execution, sniff the `GATEWAY_TOKEN` environment variable:

- Non-empty → append `--env GATEWAY_TOKEN=$GATEWAY_TOKEN` at the end of the command (if the user's OpenClaw version uses header authentication, equivalently change to `--header "Authorization: Bearer $GATEWAY_TOKEN"`)
- Empty → output as-is, and prompt the user: "If OpenClaw gateway calls require authentication, please `export GATEWAY_TOKEN=<your-token>` before executing this command"

Never write tokens in plaintext in the cron command string itself — only reference `$GATEWAY_TOKEN` and let the runtime resolve it. The same applies to direct `openclaw run` calls: if token is detected, add `--env GATEWAY_TOKEN=$GATEWAY_TOKEN` to the command, otherwise don't.

If there are equivalent tool calls within the agent, pass the same fields according to their schema.

## ④ QwenPaw

Create via the local console `qwenpaw app` (default `http://127.0.0.1:8088/`) "Scheduled Task Calendar View", or `qwenpaw cron` (specific subcommands subject to `qwenpaw --help`). Guide the user:

> QwenPaw's scheduled tasks are in the console → calendar view. Create a task with cron `0 10 * * 1`, timezone Asia/Shanghai, and paste the action content above as the prompt. I have the content ready, just copy it.

## ⑤ Fallback (Any Agent)

If the current agent does not belong to any of the above categories, or if the automatic creation flow for the above platforms fails, enter this fallback strategy. Display the following text directly to the user, guiding them to operate manually:

---

Unable to automatically create the scheduled task for you (an exception may have occurred during the automatic creation process). However, most agents support scheduled tasks. You can try manually using the following methods:

First, look for entries like "定时任务", "Scheduled Task", "Cron", or "周期任务" in your current agent's operation page (console, settings page, tool panel, etc.). If found, click in and paste the prompt below to create the scheduled recommendation task.

If you cannot find the relevant entry in the interface, you can also ask your current agent directly in the conversation:

> "xxx agent, do you support creating scheduled tasks? How should I create one?"

(Replace xxx with the name of the agent you are using.) The agent will tell you whether it supports scheduled tasks and the specific operation method. Once confirmed, send the prompt below to complete the creation.

---

**Prompt (can be pasted into the scheduled task configuration page, or sent directly to the agent):**

```
Please help me create a scheduled task:
- Task name: AI尝鲜实验室-周推
- Cron: 0 10 * * 1 (Every Monday 10:00 AM)
- Timezone: Asia/Shanghai
- Task content:
  Fetch https://www.aliyun.com/daily-act/ecs/ai-innovation-lab, generate this week's recommendation
  markdown following the ai-innovation-lab skill output specification (including welcome intro +
  cloud computing emphasis + official homepage link + statistics sentence +
  table of top 4 items updated in last 30 days + 2 closing interaction sentences).
  If page fetching fails or DOM parsing returns 0 items, automatically fall back to
  https://ai-innovation-lab.oss-cn-beijing.aliyuncs.com/ai-innovation-lab.json,
  take the top 4 service_ids by meta.recommend_order as recommended projects.
  Deliver to user according to delivery configuration upon completion.
```

## Post-Creation Notification and Changes

Regardless of which platform is used, after successful creation, tell the user three things:

1. Task name (fixed "AI尝鲜实验室-周推") and next trigger time.
2. **How to modify**: In QoderWork, say "change to every Friday 5 PM"; in Hermes / OpenClaw, use `<agent> cron edit <id>`; in QwenPaw, change the time in the calendar view.
3. **How to cancel**: In QoderWork, say "cancel weekly recommendation"; in Hermes / OpenClaw, use `cron remove <id>`; in QwenPaw, delete the task.
