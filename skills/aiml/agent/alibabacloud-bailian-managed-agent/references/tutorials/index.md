# Hands-on Tutorial Index (by Capability)

> Tutorial sources: the official whitepaper appendix + the official API docs + field tests of the official Python SDK + practice cases contributed by users. **Tutorials 01-07 are currently documented.**
> **This directory is organized by capability / action verb — one tutorial per capability, covered thoroughly.** When the user wants "how a complete business scenario lands end-to-end"
> (build a morning-report bot, notify me when done, multi-role division of labor for proposals) → switch to [../cookbook/index.md](../cookbook/index.md) (scenario playbooks, field-tested with REST/curl).
> When the user asks "how do I" and neither side has matching content: explain the coverage, then improvise minimal steps with product capabilities
> ([../product/overview.md](../product/overview.md)) + the CLI pipeline ([../workflows/provision.md](../workflows/provision.md)),
> and suggest the user contribute the scenario as a tutorial. New tutorials use [_template.md](_template.md).

## Capability → tutorial mapping

Match by the **action verb** in the user's request. When one request hits multiple rows, teach the lowest difficulty first.

| Capability / request | Tutorial | Difficulty | Prerequisites |
| --- | --- | --- | --- |
| First touch / live demo for a customer (create Agent → attach Skill → run session → collect artifacts) | [01-ai-native-quickstart.md](01-ai-native-quickstart.md) | Beginner | A local Agent that supports the CLI (Qoder / Claude Code / Codex etc.); an Alibaba Cloud account |
| Attach an official Skill (e.g. frontend-design) | [01-ai-native-quickstart.md](01-ai-native-quickstart.md) step 3 | Beginner | Same as above |
| Understand a session's event stream (`message` / `tool_call` / `session_status`) | [01-ai-native-quickstart.md](01-ai-native-quickstart.md) step 4 | Beginner | Same as above |
| Wire the Agent into your own business system / write calling code / want API examples | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) | Intermediate | Tutorial 01, or resources already created via the CLI with a session run working |
| "Streaming or async?" / unsure which integration shape / presenting the selection at an architecture review | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) step 3 (split into **strong- / weak-interaction** macro scenarios first, then pick the shape) | Intermediate | An API key and workspace ID |
| "How do I reference the CLI's Agent in code?" / where does `agent_id` come from | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) step 1 | Intermediate | An API key and workspace ID |
| Build a streaming chat UI (SSE passthrough to the frontend) | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) Shape A (strong interaction) | Intermediate | Same as above |
| Convert long-running tasks to async (submit a ticket number, poll in the background) | [02-integrate-to-your-system.md](02-integrate-to-your-system.md) Shape B (weak interaction) | Intermediate | Same as above |
| Scheduled unattended batch runs (Deployment + cron) | [04-scheduled-deployment.md](04-scheduled-deployment.md) | Advanced | Tutorial 01, plus one manual run already working |
| Have the Agent read my data files / upload files for the Agent to analyze | [03-mount-files.md](03-mount-files.md) | Beginner | An API key and workspace ID; a working Agent |
| Agent says "file not found" after mounting / how to write the mount path | [03-mount-files.md](03-mount-files.md) step 5 | Beginner | Same as above |
| Uploaded file not usable immediately / file scan status | [03-mount-files.md](03-mount-files.md) step 3 | Beginner | Same as above |
| How to collect scheduled-task results / prevent double processing | [04-scheduled-deployment.md](04-scheduled-deployment.md) step 5 | Advanced | An existing Deployment |
| Pause a scheduled task temporarily / change config / archive | [04-scheduled-deployment.md](04-scheduled-deployment.md) step 6 | Advanced | Same as above |
| Pre-install dependencies the base image lacks / cargo·go declarations not taking effect | [05-environment-packages.md](05-environment-packages.md) | Advanced | An API key and workspace ID |
| Open up sandbox egress / how to set the environment scope | [05-environment-packages.md](05-environment-packages.md) steps 4-5 | Advanced | Same as above |
| Customer asks about sandbox CPU / memory / duration specs | [05-environment-packages.md](05-environment-packages.md) FAQ | Advanced | — |
| Human approval for high-risk actions / handling `requires_action` | [06-tool-approval.md](06-tool-approval.md) | Expert | Tutorial 02 (able to send and receive events) |
| Task "finished but no result" / session stuck at idle | [06-tool-approval.md](06-tool-approval.md) step 1 | Expert | Same as above |
| Proactively interrupt a runaway session / implement a "stop" button | [06-tool-approval.md](06-tool-approval.md) step 5 | Expert | Same as above |
| Multi-agent collaboration / formations / multiple Agents dividing work | [07-multiagent-coordinator.md](07-multiagent-coordinator.md) | Expert | Tutorial 02; at least one single-agent Agent already working |
| "Which member is doing what" in a formation / member outputs mixed into one pot | [07-multiagent-coordinator.md](07-multiagent-coordinator.md) step 5 | Expert | Same as above |
| How to create a coordinator-type Agent | [07-multiagent-coordinator.md](07-multiagent-coordinator.md) step 3 (**no such type exists** — a normal Agent plus `multiagent` is all it takes) | Expert | Same as above |
| Formation dispatching is inaccurate / want routing rules | [07-multiagent-coordinator.md](07-multiagent-coordinator.md) step 3 (**no routing field** — edit the coordinator's prompt) | Expert | Same as above |
| Attach MCP toolkits (including web search) / config & credential injection (session env vars + Vault) / Agent version rollback / Webhook notifications / custom MCP and Skill packaging | _No capability tutorial in this directory yet — see the "capability → which playbook has end-to-end practice" reverse-lookup table in [../cookbook/index.md](../cookbook/index.md)_ | | |

<!-- Documentation example (numbers 01-07 are taken; new tutorials start at 08):
| Custom Skill packaging and mounting | [Custom MCP and Skills cookbook](../cookbook/07-custom-mcp-and-skills.md) | Advanced | Tutorial 01 |
-->

## Composition patterns

Standard recipes when combining multiple capabilities. Each pattern states the **assembly order** and the **key traps**, so users don't rework by assembling in the wrong order.

| Pattern | Capabilities involved | Assembly order | Key traps |
| --- | --- | --- | --- |
| Agent + official Skill + builtin tools producing files | Agent / Skill / `write` / Files API to collect artifacts | Get the bare conversation working with `session run` first → attach the Skill and run again → collect artifacts last | Skill names must be looked up via `skill-list`; custom skills must be `active` before mounting; collect artifacts via the Files API (the `download_file` builtin tool is officially decommissioned) |
| Scheduled report pipeline (the shared recipe of documented solutions) | Deployment / Vault / `bash` / `read` / `write` / MCP | Manually `session run` one full output first → add the Deployment schedule → wire up push last | Run `plan` before the schedule goes live, to avoid double-triggering with an existing external cron; put analysis logic in scripts, not prompts. Full walkthrough: [../cookbook/02-production-four-building-blocks.md](../cookbook/02-production-four-building-blocks.md) |
| CLI-provisioned resources + business-system integration (the most common full landing path) | Agent / Environment / Session / Event / File / Deployment | Tutorial 01 via the CLI → grab remote IDs → verify the chain with curl → switch to code → production self-check | IDs are not interchangeable: the CLI uses logical names, code uses `agent_`/`env_` remote IDs; mount paths in prompts need the `/mnt/session/uploads` prefix |
| Data analysis pipeline (install deps + mount data + run on schedule) | Environment packages / File / Deployment | Create the environment and verify deps first ([05](05-environment-packages.md) step 3) → mount one dataset and run manually ([03](03-mount-files.md)) → add the schedule ([04](04-scheduled-deployment.md)) | Order matters: mounting data before deps are installed makes errors unattributable (missing package vs. wrong path); `config.type` is immutable after creation |
| Production integration with approval (taking an Agent with write operations live) | Event stream / `requires_action` / `tool_approval_response` | Get the event loop working per [02](02-integrate-to-your-system.md) first → add the approval branch ([06](06-tool-approval.md)) → wire up the approval UI / ticketing last | The event loop must branch three ways on `stop_reason.type`; checking only `idle` silently deadlocks; approval timeouts need a fallback strategy |
| Multi-agent formation + approval (the highest-complexity combination) | multiagent.coordinator / SessionThread / `tool_approval_response` | Run each member standalone first → create the coordinator ([07](07-multiagent-coordinator.md)) → split events by the top-level `thread_id` → targeted approvals carry `session_thread_id` at the event top level | Formation troubleshooting costs multiples of a single agent; assembling unvalidated members is blind debugging; a targeted approval without `session_thread_id` lands on the wrong thread |
| _(more to be documented)_ | | | |

> Combinations that already have field-tested end-to-end playbooks are cheaper to cite directly: the production four building blocks (MCP + Vault + Deployment + HITL) in
> [../cookbook/02-production-four-building-blocks.md](../cookbook/02-production-four-building-blocks.md); multi-agent + thread observation in
> [../cookbook/04-multi-agent-custom-proposals.md](../cookbook/04-multi-agent-custom-proposals.md);
> scheduled + notify-on-done in [../cookbook/06-webhook-event-notifications.md](../cookbook/06-webhook-event-notifications.md).

<!-- Documentation example:
| Knowledge + tools + schedule | file mounting / tool calls / Deployment schedule | Get one conversational turn working → add tools → add the schedule last | Run plan before the schedule goes live, to avoid double-triggering with an existing external cron |
-->

## Tutorial delivery rules (follow when teaching a tutorial)

1. **Confirm prerequisites first**; resolve a missing `bl` install or login before starting (see the skill `bailian-protocol`).
2. **Advance one step at a time**; each step ships a copy-pasteable command or a config snippet that can be written to disk as-is.
3. **Give a verification method per step** (what output to expect / which command to check with); never push several steps before verifying.
4. For `apply` / `destroy`: run `plan` to show the diff first; add `--yes` only after the user confirms.
5. If a tutorial's command flags disagree with `bl <command> --help`, **`--help` wins** — report the drift (the tutorial needs an update).
6. When the user's environment differs substantially (different provider, existing `agents.yaml`, different region), explain the differences and adapt the steps — don't copy blindly.

## Related files

- New-tutorial template → [_template.md](_template.md)
- Find full playbooks by business scenario → [../cookbook/index.md](../cookbook/index.md)
- Unclear on concepts → [../product/concepts.md](../product/concepts.md)
- Resource provisioning pipeline → [../workflows/provision.md](../workflows/provision.md)
