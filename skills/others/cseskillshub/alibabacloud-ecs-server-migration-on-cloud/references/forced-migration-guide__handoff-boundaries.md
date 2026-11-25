# Hand-off boundaries and standard wordings

This skill is a narrow, read-only guide for one symptom axis: region / data-center decommission
and forced migration, platform-initiated reboots, and the impact or compensation disputes tied to
a platform action or a billing rule. Neighboring symptoms are recognized and handed off, not
diagnosed here. Exact names of the receiving skills are placeholders to be aligned with the
batch inventory.

## Recognize-and-hand-off table

| Adjacent symptom | How to recognize it | Where it goes |
|---|---|---|
| Pure unsubscribe / downgrade pricing question (no decommission, no platform fault) | "why is my refund 0", "how is cancellation calculated" only | Unsubscription-billing-rules skill (name to align); here only package evidence if it turns into a compensation dispute |
| Security incident response (brute force, scraping, traffic tracing) | main ask is blocking, the attacker's identity, hardening | Security-protection skill (name to align); here only the compensation-request evaluation and hand-off |
| Application-layer fault (customer's own program misbehaving) | cloud monitoring shows the load is the customer's business process | Performance / Cloud Assistant skill (name to align); here give the attribution wording and self-check list, then hand off |
| Written fault certificate, judicial cooperation, regulator complaint | asks for an official letter or to go to a regulator / police | Human / legal channel; the skill only registers the ask and points to the formal route |
| ICP filing, account transfer, other "migration and account" family topics | filing entity, transfer-material keywords | The matching skill (name to align); not implemented here |

## Standard wordings for the boundary lines

- Compensation / adjustment / voucher:
  "Issuing compensation or adjusting a bill needs a human billing or business specialist to
  review and approve. I can assemble the evidence pack and give you the channel, but I cannot
  promise an outcome or an amount."
- Another account's identity:
  "By privacy requirements we cannot provide another user's identity information. If you have
  filed a police report, judicial authorities may obtain it through legal process."
- Attribution that needs back-end diagnosis:
  "Historical per-process and underlying-host diagnosis is not retained or visible to this tool.
  Please provide a Cloud Monitor screenshot and route the case to a human for back-end review."
- Extreme or legal claims:
  "We record this faithfully and handle it through the formal channel."
- In-guest readings:
  "I do not log into or run anything inside your instance. Please run the read-only command and
  paste the output, or hand this to the Cloud Assistant / remote-connection skill."

## Absolute boundary of this skill

- Reads only `DescribeInstances`, in one account and one region, for the customer's own resources.
- Gives step-by-step guidance the customer performs; executes nothing that changes cloud state.
- Never submits, approves, or promises any compensation, voucher, refund, or adjustment.
