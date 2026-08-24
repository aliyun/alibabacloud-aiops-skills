---
name: alibabacloud-sls-agent-workflow
description: Route and orchestrate Alibaba Cloud Simple Log Service (SLS) work across specialist skills for application integration, index management, exact querying, exploratory analysis, and visualization. Use when the user asks which SLS skill to use, wants an overview of available SLS skills, gives a broad or ambiguous SLS goal, requests an end-to-end workflow spanning two or more supported domains, or needs a selected SLS specialist that is not installed. For a clearly scoped single-domain request with its specialist available, hand off directly without adding an unnecessary workflow.
---

# Alibaba Cloud SLS Agent Workflow

Turn the user's SLS outcome into the smallest capable sequence of specialist skills, carry useful context and evidence between them, and continue until the requested outcome is verified or a concrete gap is reached. This skill coordinates work; it does not duplicate specialist instructions.

## Specialist catalog

Use exact full skill names whenever naming, selecting, installing, or handing off to a specialist.

| Specialist skill | Choose it for | Boundary |
| --- | --- | --- |
| `alibabacloud-sls-sdk-guidance` | SDK selection and installation; application writes, Producer, Consumer, Appender, and programmatic query integration | It provides application integration guidance, not general cloud-resource operations. |
| `alibabacloud-sls-index-config-management` | Independent index inspection, generation, creation, update, deletion, or optimization from log samples and query workloads | Use it for fields already present in delivered data; the current suite does not change upstream collection pipelines. |
| `alibabacloud-sls-query` | Precise index search, SQL, or SPL authoring, explanation, execution, optimization, and query troubleshooting | Prefer it when the user needs a controlled, reproducible statement or exact result. |
| `alibabacloud-sls-data-agent` | Autonomous natural-language data acquisition, multi-step analysis, trends, anomalies, conclusions, and visualizations | Prefer it for exploratory analysis. It does not replace application integration, index management, exact query control, or managed dashboard resources. |

## Route by outcome

- For an explicit single-domain request, select the matching specialist. Load and follow it when the user requests execution or detailed guidance; for a route-only request, return the owner and boundary without adding a workflow.
- For a multi-stage outcome, select only the specialists that contribute to it and order them by dependency. Let verified results determine whether later stages are still needed.
- Apply the catalog boundaries when intents overlap. Give each stage one primary owner, and combine exact querying with exploratory analysis only when both outcomes are useful.

Before executing or handing off a stage, load its specialist skill and defer commands, prerequisites, permissions, confirmations, rollback, and verification to it. Continue into execution when the user requested action and the required authority and context are available; do not stop at a route or plan unless the user asked for guidance or a real blocker remains.

Carry forward only context that helps the next specialist: region, Project, Logstore, source, application language, relevant fields, time range, desired result, decisions already made, and verified evidence. Do not create a workflow-context file unless the user asks for one.

## Progressive references

Read only the reference that matches the active need:

| Need | Reference |
| --- | --- |
| One or more selected specialist skills are unavailable | [Install specialist skills](references/install-specialist-skills.md) |
| Bring application logs from a source to a queryable, analyzed, alert-ready state | [Application log landing](references/workflows/application-log-landing.md) |
| Build or adjust an index and prove the intended queries work | [Index and query readiness](references/workflows/index-query-readiness.md) |

Do not read every workflow reference for a single request.

## Boundaries and completion

- Treat only installed specialist skills as executable. If a selected skill is missing, follow the installation reference before relying on it.
- The current suite has no specialist for host-agent collection, machine groups, collection Pipeline configuration or binding, collector heartbeat, SLS Lens troubleshooting, general standalone Project/Logstore management, managed SLS alert resources, data processing, shipping, or persistent dashboard resources. State the gap instead of inventing a skill or silently implementing its cloud operations in this router. A specialist may still manage a resource when that resource is explicitly within its own documented scope.
- Never request, read, or expose AccessKey ID or AccessKey Secret values.
- Preserve every specialist's approval and safety gates. Earlier approval for the overall goal does not bypass a later specialist's required confirmation.
- Respond in the user's language while keeping skill names, commands, resource identifiers, and product terms intact.
- Lead the final response with what was achieved or what blocks completion. Include concise evidence for claims, identify any unfinished stage, and avoid claiming that a plan, generated query, visualization, or configuration draft is a deployed cloud resource.
