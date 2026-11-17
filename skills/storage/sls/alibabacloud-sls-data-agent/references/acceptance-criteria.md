# Acceptance criteria

Evaluate the selected workflow using the current scripts and [execution interfaces](api-reference.md). The executable scenarios, resource-binding instructions, and validation limits are in [evals](../evals/README.md).

## Workflow selection and resource information

- Explicit DataAgent requests and existing Chat continuations use DataAgent Chat, including when the request also mentions a Project or Logstore.
- When neither the request nor existing context identifies a model or Project/Logstore, use DataAgent Chat and complete its required resource information.
- Explicit Context Model/Source Model requests and identified Project/Logstore analysis use the model workflow. A missing parameter is completed within that workflow.
- Reuse complete resource information from the request and existing context. Read the resource examples only when information is missing or incomplete; recording resources in AGENTS.md is optional.

## DataAgent Chat

- Use the confirmed DataAgent resource name and Chat service region. Reuse the selected target and thread for follow-ups.
- Read the complete JSON result and handle `completed`, `interactive`, `failed`, and `unknown` according to the workflow.
- Forward the actual user's interaction result, preserve pending interactions, and serialize continuation calls. Do not invent confirmations or interaction answers.
- An unknown or interrupted result is investigated through the recovery workflow; it does not justify automatically resending the original request or interaction result.
- Progress is enabled by default on stderr and can be disabled with `--no-progress`. Stdout remains one complete JSON result. Disabling progress preserves business results and necessary diagnostics.
- Stop a remote request only when the user explicitly asks, using the existing stop workflow. Local read interruption does not establish that the remote turn stopped.

## Context Model reads

- Use the selected model name/UUID, read overview and get as needed, and retain the original definitions and adoption rules.
- Resolve the selected Schema or source to physical query locations. Read the returned schema and all datasource candidates; choose the query scope using the existing workflow rules.
- Distinguish missing members from definitions omitted by the output budget. Recover required definitions before using them.
- Use the model endpoint only for model calls. Query logs at their resolved physical locations.

## Source Model preparation and reads

- Preserve the original status-plus-node-query checking order, generation-state decisions, SQL fallback, clarification, and management/HIL paths.
- An element count of zero alone does not establish that the model is absent. Preserve service errors and incomplete responses rather than interpreting them as usable model definitions.
- Read definitions through overview/get for the selected Project and Logstore scope. Source Models do not provide Context resolve or example-query selectors.
- Do not perform a model write unless the user explicitly requests it through the prescribed management/HIL flow.

## Query accuracy and delivery

- Build queries from confirmed definitions and constraints without changing metric meaning, filters, units, or literals.
- Inspect indexes and small log samples when required by the workflow. Keep actual execution locations and the resolved time window.
- Check `meta` and `logs`, completeness, errors, and output limits. Incomplete, empty, failed, or unexecuted queries cannot establish unsupported conclusions.
- Record executed analysis queries and their actual results in non-overwriting evidence files. Export only selected, validated records.
- Deliver supported conclusions, executed SQL, data sources, and actual time ranges. Use charts only when appropriate, reuse accepted results, and preserve the query meaning and window.

## Evaluation evidence

- A syntactically valid case or passing local fixture demonstrates only the behavior it exercised.
- Live execution requires operator-confirmed resources and working credentials for the actual CLI/SDK identities. Test configuration alone does not prove authorization.
- Verify Chat results by their JSON status and model results by their model/query evidence. Do not require a specific numeric result or a successful root-cause conclusion unless a controlled fixture establishes it.
