# From Customer Requirements to a Solution (Methodology)

For designing on the spot when the customer scenario does not fully match an existing case.
The goal is a **solution that can enter PoC**, not a pretty slide deck.

## Step 1: establish the known requirements

Use information already supplied. For a proposal or code draft, proceed with explicit assumptions and list unresolved prerequisites; do not stop all useful work for optional details. Ask at most 4 questions when missing facts block an actual operation, in priority order:

1. **What is the deliverable?** What does the Agent ultimately produce (a report / a ticket conclusion / a data row written back to a system / a conversational answer)? Who accepts it, and by what standard is it correct?
2. **Where do inputs come from?** Files / databases / business-system APIs / user input? Volume and frequency?
3. **Which steps need judgment, and which are deterministic rules?** — hand judgment to the Agent; push deterministic rules to code or validation steps whenever possible.
4. **System boundaries and compliance?** Can it egress the network, can data leave the intranet, is a human-confirmation step needed, audit requirements.

When the customer cannot answer, converge by walking one real case through end-to-end — far more effective than abstract discussion.

## Step 2: pick the shape

| Signal | Shape |
| --- | --- |
| Human-initiated, needs multi-turn clarification | Conversational (Session-based integration) |
| Runs on a fixed cycle, unattended | Unattended (Deployment + `schedule`) |
| Triggered by business-system events, results written back | Embedded (the business side calls the Session API, parses the event stream, writes back) |
| A batch of tasks processed concurrently | Batch (multiple concurrent Sessions / multiple Deployments) |

The shape determines the integration approach — see [../integration/patterns.md](../integration/patterns.md).

## Step 3: split the tasks

Principle: **one Agent owns exactly one independently acceptable responsibility**.

- Chain too long (>5 heterogeneous steps) → split into multiple Agents chained by artifacts (files / data), instead of stuffing everything into one giant instruction.
- High-risk actions (payments, outbound sends, data modification / deletion) → a separate step + human or rule confirmation, never merged with judgment steps.
- Repetitive, error-prone multi-step operations → consolidate into a custom skill; more stable than prompt text.

## Step 4: map to resources

Map item by item against the resource model in [../product/concepts.md](../product/concepts.md):

- Needs to read local / customer-provided files → Session mounting (`mount_path` starts with `/uploads/`, the real in-sandbox path is `/mnt/session/uploads/…`, write the real path in the prompt; upload whitelist `.txt` / `.md` / `.json` / `.xlsx` / `.pdf` / `.png` — a customer's `.csv` must be renamed `.txt` first; state this upfront in the solution)
- Needs task working context across MA sessions → use launched MA Memory Store; persistent files can also use cross-session file mounting. Needs user preferences/personalized memory keyed by UserId → consider the separate Bailian Memory Library. Do not conflate the two products; see [concepts](../product/concepts.md#memory-store-working-memory).
- Needs to call third-party or customer systems → Tool / MCP + credential injection (high-sensitivity secrets go into a Vault with only placeholders visible in the sandbox; non-sensitive config uses the session environment variables `environment_variables`; the selection layering is in [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md))
- Needs scheduling → the Deployment's `schedule` + `initial_events`
- Needs model selection → the skill `bailian-model-recommend`

**Do not write unverified capabilities into the solution** (e.g. items marked "to be verified" in concepts.md) — verify first, or flag them as pending confirmation.

## Step 5: scope the PoC

A customer-facing solution must include a minimal loop verifiable in 1-2 weeks:

```
PoC goal: <one scenario + a quantifiable acceptance bar, e.g. "≥ 90% extraction accuracy on 10 real documents">
Out of scope: <explicitly strike what will not be done this phase, to prevent scope creep>
Customer must provide: <N data samples / one test account / one API doc>
Deliverables: <agents.yaml + one reproducible run record + a results comparison table>
```

## Step 6: write the solution

A fixed three-part structure (the three parts customers care about most):

1. **Reusable as-is**: what is product capability out of the box + parts already validated by existing cases.
2. **Needs customization**: what must be tailored to the customer's systems / data, with rough effort magnitude.
3. **Preconditions**: what the customer must provide first, or work cannot start.

When execution is requested, use [provision.md](provision.md) for a CLI trial, or API/SDK for customer system integration. A proposal request alone does not authorize provisioning.

## Common design mistakes

| Mistake | Consequence | The right way |
| --- | --- | --- |
| One Agent wraps the whole flow | Failures hard to locate, hard to accept | Split by independently acceptable responsibilities |
| Deterministic rules handed to the model | Fluctuating quality, unexplainable | Rules in code / validation steps |
| Treating CLI provisioning as a prerequisite for all code | Blocks customers who already have resources or only need a template | Use verified API contracts and configurable IDs for code; smoke-test existing resources only when authorized |
| Matching cases by industry label | Customer system and data differences get ignored | Match by business scenario + capability shape |
| Promising unverified capabilities in the solution | Delivery-deadline breach | Write only capabilities that are documented or field-tested |
