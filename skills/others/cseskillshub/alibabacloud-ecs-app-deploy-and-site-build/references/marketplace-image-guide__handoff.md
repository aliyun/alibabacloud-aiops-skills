# Boundary and handoff

The word "image" covers several unrelated things in this product area, so the first
job of this file is deciding whether the request belongs here at all. Route on the
customer's wording, not on the presence of an instance identifier.

## Recognize, then hand off

| Customer wording or symptom | Belongs here? | Handoff channel and script |
|---|---|---|
| "My Docker image will not pull", registry mirror, `nginx` pull failure | No. A container image has nothing to do with Marketplace images, their fees or their restrictions | Container and network support channel. State that the mirror configuration is theirs to change; this skill writes no daemon configuration and submits no ticket. |
| "The SQL Server / panel / database that came with the image will not start" | No. The image attached correctly; the failure is inside it | The vendor support entry on the Marketplace product page, plus a remote connection for the customer's own read-only checks. Ask them to paste the output back; this skill never runs anything in the instance. |
| "Can I mount an ISO and install my own system?" | Partly. The rule is here, the operation is not | Answer: ISO mounting is not supported; an operating system with no listing goes through the custom-image import flow. Hand the operation itself to the image-import channel. |
| Instance will not boot, and the attached image is public | No | Instance-boot troubleshooting channel. Run the read-only check first so the handoff says why the image is ruled out. |
| "Change my public IP" or "convert my bandwidth billing", with the Marketplace-image conversion message | Message here, goal elsewhere | Correct the entry: only the bandwidth billing method needs converting. See `restriction-matrix.md`, the mis-entry trap. |
| Designing resource groups and RAM for an organization | No, only one interaction is here | Account and permissions channel. This package explains why a group-scoped RAM user fails on a Marketplace image, and stops there. |
| Amounts, order counts, refund eligibility, refund arrival | No | Billing route, quoting the order numbers the customer reads from the billing console. This skill states no figure. |
| Executing a cancellation, granting a ticket authorization, approving a refund | No | Human billing and Marketplace route. This skill prints no confirmation on their behalf and never says a cancellation was completed. |

## Standard handoff wording

Adapt the facts, keep the shape:

- **Container:** "What you are describing is a container image pull failure, which is
  separate from Cloud Marketplace images, their charges and their limits. That belongs
  with the container and network support channel; I have not changed any runtime
  configuration, and I cannot."
- **Software inside the image:** "The image itself attached correctly, so this is the
  software the vendor shipped. The support entry on that product page owns it. You can
  also connect to the instance yourself and check that service's own connection
  settings; I only read cloud-side facts and do not run commands inside instances."
- **ISO:** "ECS cannot install from an ISO file. An operating system with no public or
  Marketplace listing goes through the custom-image import flow, which is a separate
  topic from this one."
- **Billing:** "The amount and the order history sit on the billing side, which is
  outside the read-only queries I hold. Please raise a ticket with the instance
  identifier and the order numbers attached. Here is the evidence block to paste."
- **Unrelated boot fault:** "I checked the attached image and it is a public image, so
  this is not the Marketplace-image path. That belongs with instance-boot
  troubleshooting."

## When guidance is not accepted

Some customers find the fixes disproportionate and stop, and some dispute an
attribution no metadata can settle. That is a normal outcome, not a failure to
argue with. When the customer says no, or says the step did not work:

1. Re-read the facts and state anything that changed since the last run.
2. Stop repeating the same step; a second identical suggestion costs the customer time.
3. Offer the ticket route, with the evidence block from the report attached.

Never assume acceptance. Several documented cases in this tier closed on the
assistant's summary alone, with no confirmation from the customer, so a handback is
part of the design rather than an exception.

## What is not to be found in this file

No named sibling skills. The neighbouring-tier list for this batch was not resolved,
so every handoff above is expressed as a channel and a script. Do not invent a skill
identifier when answering a customer.
