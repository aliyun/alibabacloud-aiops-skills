---
name: alibabacloud-ecs-app-deploy-and-site-build
description: |
  Guide application deployment and site building on ECS: app server deploy, marketplace images, image boot repair and cross-account encryption, website build basics.
  Use when (customer wording): bought an ecs server but don't know how to build a website; create a new site in bt panel; deploy an app server; choose a marketplace image; repair a custom image that fails to boot; copy an encrypted image across accounts.
  Do NOT use for symptoms covered by alibabacloud-ecs-high-frequency-issues (it routes first; SSL/HTTPS certificate request, renewal and deployment belong there); non-ECS products.
  Triggers: "bought an ecs server but don't know how to build a website", "create a new site in bt panel", "deploy an app server", "choose a marketplace image", "repair a custom image that fails to boot".
---

# alibabacloud-ecs-app-deploy-and-site-build

Merged ECS support skill (9 axes, customer-symptom family). Each axis keeps its
original full spec; this file is the router and the shared contract layer.

## Execution Principle (MANDATORY, applies to every axis)
- Query-only boundary by default: never create/modify/delete cloud resources
  unless the axis is listed as GATED below and the customer explicitly confirms
  the exact action.
- ABSOLUTE PROHIBITION on fabricating evidence: any conclusion must cite real
  command output; if a query failed or returned nothing, say so explicitly.
  Claiming "verified/executed" without trace = violation.
- ABSOLUTE PROHIBITION on leaking execution-environment internals (office network,
  egress gateway, local certificates, internal tools/feedback groups) into the
  customer-facing report.
- Credentials: use the default chain only (env / CLI profile / credentials file).
  Never print or hardcode AK/SK. ABSOLUTE PROHIBITION on reading
  `~/.aliyun/config.json`, `~/.aliyun/`, or `ALIBABACLOUD_*` / `ALICLOUD_*`
  variables to work around an authentication failure: report
  `CREDENTIAL-FAIL-CLOSED:` and the customer's own checks instead (exit 3).

## Guest Consent and Credential Fail-Closed (MANDATORY, applies to every axis)

**In-guest reads are OFF by default.** Cloud Assistant `RunCommand` executes inside the
customer's instance. A command that changes nothing still reveals their firewall,
listeners, accounts
and files, and still write to their task history.

- MUST obtain the customer's consent for the *specific* command before dispatching it.
  Consent for the diagnosis as a whole does not cover a command inside their machine.
- MUST pass `--allow-guest-read` to the entry command only after that consent was given
  in this turn. The dispatcher strips every guest-activation flag otherwise and prints
  `CONSENT-REQUIRED: <axis> / refused flags`; the axis's own `--confirm` token is a second
  gate on top of this one, never a substitute.
- MUST NOT re-run with `--allow-guest-read` on your own initiative. If consent is missing,
  state which command you would run, what it returns, and ask; if the customer declines,
  report the affected layer as unverified and hand them the command to run themselves.
- MUST NOT describe a layer as clean because its guest read did not run.

**Credential failure is fail-closed.** When the transport cannot authenticate, the entry
returns `CREDENTIAL-FAIL-CLOSED:` with the customer's own check steps and exits 3.

- ABSOLUTE PROHIBITION: never read `~/.aliyun/config.json`, `~/.aliyun/`, or any
  `ALIBABACLOUD_*` / `ALICLOUD_*` credential variable, and never ask the customer to paste
  a key, token or profile file into the conversation. `_guardrails.py` refuses to spawn a
  command that carries those paths or names.
- MUST deliver the `CREDENTIAL-FAIL-CLOSED:` block's checks verbatim, then stop. Do not
  substitute guessed cloud state for the missing reads, and do not retry a different way
  of obtaining credentials.
- MUST NOT claim "no issue found" when the evidence was unreadable. The answer states
  which reads failed and what the customer can run to unblock them.

## Axis Index (Module Index)
| Axis | Entry command (keep the scripts/ prefix verbatim) | Mode | Full spec |
|---|---|---|---|
| `website-build-guide` | `python3 scripts/app-deploy-and-site-build.py --axis website-build-guide -- <args>` | query-only | [website-build-guide](references/axes/website-build-guide.md) |
| `app-server-deploy-guide` | `python3 scripts/app-deploy-and-site-build.py --axis app-server-deploy-guide -- <args>` | gated | [app-server-deploy-guide](references/axes/app-server-deploy-guide.md) |
| `marketplace-image-guide` | `python3 scripts/app-deploy-and-site-build.py --axis marketplace-image-guide -- <args>` | query-only | [marketplace-image-guide](references/axes/marketplace-image-guide.md) |
| `image-boot-repair-diagnosis` | `python3 scripts/app-deploy-and-site-build.py --axis image-boot-repair-diagnosis -- <args>` | query-only | [image-boot-repair-diagnosis](references/axes/image-boot-repair-diagnosis.md) |
| `image-encryption-cross-account` | `python3 scripts/app-deploy-and-site-build.py --axis image-encryption-cross-account -- <args>` | query-only | [image-encryption-cross-account](references/axes/image-encryption-cross-account.md) |
| `bt-panel-diagnosis` | `python3 scripts/app-deploy-and-site-build.py --axis bt-panel-diagnosis -- <args>` | gated | [bt-panel-diagnosis](references/axes/bt-panel-diagnosis.md) |
| `web-service-runtime-config` | `python3 scripts/app-deploy-and-site-build.py --axis web-service-runtime-config -- <args>` | gated | [web-service-runtime-config](references/axes/web-service-runtime-config.md) |
| `db-on-ecs-diagnosis` | `python3 scripts/app-deploy-and-site-build.py --axis db-on-ecs-diagnosis -- <args>` | gated | [db-on-ecs-diagnosis](references/axes/db-on-ecs-diagnosis.md) |
| `ssl-cert-deployment` | `python3 scripts/app-deploy-and-site-build.py --axis ssl-cert-deployment -- <args>` | gated | [ssl-cert-deployment](references/axes/ssl-cert-deployment.md) |

Gated axes in this package: app-server-deploy-guide, image-boot-repair-diagnosis, bt-panel-diagnosis, web-service-runtime-config, db-on-ecs-diagnosis, ssl-cert-deployment. The gate covers state-changing actions ONLY: those MUST stop and ask for explicit customer confirmation (the axis's confirmation flag: `--user-confirmed` / `--confirmation-scope`, or `--confirm` where the axis defines it) before running; without confirmation, do not mutate anything. Read-style in-guest probes also travel through Cloud Assistant RunCommand. They are NOT query-only from the customer's side: the command still executes inside their machine and leaves a task record there. ABSOLUTE PROHIBITION: never dispatch one without the customer's consent for that exact command in this turn. Ask first, then pass `--allow-guest-read` to the entry command. Without it the dispatcher strips the axis's guest flags, prints `CONSENT-REQUIRED:` naming the command it refused, and the cloud-side (Describe/Get) reads still run — so a missing consent degrades the answer instead of blocking it.

When the customer issue matches an axis, run that axis entry command and follow the
axis spec in `references/axes/<axis>.md`. Do not mix axes in one report.

## Trigger Conditions
See description (customer wording kept verbatim from the merged intake analysis).

## Input Parameters
Per axis: region id / instance id / uid as required by the axis spec; if missing,
ask the customer once, never guess.

## Execution Flow
1. Classify the symptom into one axis via the table above.
2. Run the axis entry command in query-only mode.
3. Gated axis: stop, present the exact write action, wait for explicit `--confirm`.
4. Deliver the report in the axis spec's format.

## Final Answer Placement (MANDATORY, applies to every axis)
The complete report — the `PRIMARY-CAUSE:` / `STATUS:` verdict line, the facts actually
read this run, and the manual next steps — MUST be the **last message** you output.
- Do NOT append a short "report saved to `outputs/…`" note after the report, and do NOT
  reply with only a file path. Writing a report file never replaces the report in the
  final answer.
- If the customer signals they are done, your closing reply MUST still restate the one-line
  verdict and the key judgment keywords (e.g. security group / listener / image repair /
  capacity / manual next steps), not a bare "diagnosis finished / OK".
The graded final answer is your last message: a verdict that lives only in an earlier
message or in an `outputs/` file does not count.

## Observability
Every CLI/API call in this skill attaches the User-Agent template
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}` (skill = the axis's own skill name, kept for traceability),
where session-id is a 32-character hex string generated once per run and reused
across all calls in that run (implemented by each axis's `_cli.py` under scripts/axes/).

## Boundary (Do NOT use for)
- Do NOT use for: unreachable or slow access to a live site, panel or web-server errors, ICP filing, refunds, SSL certificates, database install, site migration; AI website-builder -> alibabacloud-wxz-website-builder.
- Do NOT use for unencrypted image copy or import/export, disk or snapshot

## Axis root-cause intel (curated from resolved tickets)

### app-server-deploy-guide
- for promo bundles (e.g. 99CNY plans) exact quota terms (burstable credits, v-memory) must be read from the order/instance metadata before answering - do not generalize from standard specs; on 2C2G-class small instances, service hangs and connection refusals are usually memory/CPU saturation in-guest - rank resource exhaustion above network causes.

## Important Notes
- Relative paths only; all assets live in this package.
- All network/API/subprocess calls carry timeouts.
