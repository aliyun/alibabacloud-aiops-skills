# M1 -- ECS Unsubscription & Refund Rules (fixed corpus, CL-C)

Provenance labels used throughout this module (relay them to the customer):

- **[official-doc]** -- stated on an Alibaba Cloud help page; the page was
  reachable at skill build time.
- **[support-position]** -- wording verified only from support-agent replies
  in real handled tickets; no authoritative page located. Relay honestly as
  the support-team position, and let the refund page / human channel be the
  final word.

The machine-readable twin of this corpus is `RULE_TOPICS` in
`scripts/areas/unsubscribe_refund/_constants.py`; query it with
`python3 scripts/areas/unsubscribe_refund/ecs_unsubscribe_refund.py --rules --topic <key>`. Never
paraphrase a limit or a duration from memory -- read it from the script or
this file.

## 1. Eligibility and self-service path

| Rule | Content | Provenance |
|---|---|---|
| Five-day no-reason window | Newly purchased subscription (prepaid) ECS instances can be self-refunded within five days of purchase, full amount; eligibility per instance is finally shown on the refund page | [official-doc] |
| Yearly count | Each user, per product, may use the five-day no-reason full refund on ONE instance per natural year (Jan 1 - Dec 31); in that scenario a subscription ECS instance shares the one-per-year quota with resource packages and reserved instance coupons. No query API exposes the used-count -- the refund page is the checker | [official-doc] |
| Non-full path after the window | Subscription instances outside the window go the non-full refund track: residual value computed by the system from remaining duration and configuration price difference; the refund page shows the exact figure | [official-doc] |
| Self-service entry | PRIMARY, official: Billing & Costs -> Resource Unsubscription, `https://billing-cost.console.aliyun.com/refund/`; inside that page: Unsubscribe Resources tab -> Regular Cloud Resources tab -> filter by product name, instance id and order time. SECONDARY: the legacy refund center `https://usercenter2.aliyun.com/refund/refund`. The CUSTOMER submits -- never the assistant. The console shows these entries under Chinese labels; quote the labels from anchor `unsubscribe-refund__refund-entry` (its title and claim carry them, verified by official-doc citation -- a console page cannot be hash-probed because every probe answers 200 and redirects to login). The English names in this row are working terms, not on-screen labels | [official-doc] (promoted from [support-position]: the two entries used to be listed the other way round, with the legacy one as primary) |
| Request status | Whether an unsubscription request was really submitted has NO query API in the read whitelist. "I asked this morning, is it done?" must be answered by checking the order list `https://billing-cost.console.aliyun.com/order/list` -- verbal/chat requests are not submissions | [support-position] |

## 2. Money mechanics

| Rule | Content | Provenance |
|---|---|---|
| Timing | Refunds normally return within about 2 business days | [support-position] |
| Amount authority | The refund page displays the exact refundable amount; confirm it there before submitting; the credited amount is final ("system computes automatically; the actually credited amount governs") | [official-doc] |
| Dual caliber (skill-internal law) | Any relayed figure carries `ESTIMATE=<consumed reference>` / `AUTHORITATIVE=<refund-page value>` -- a consumed-bill total is NOT "how much you get back" | design rule from ticket evidence |
| Downgrade refunds | Once a downgrade order is paid and effective it cannot be cancelled or revoked; restoring the old spec = upgrade again + pay the difference. Refund from the downgrade is auto-computed, credited-amount authoritative | [support-position] |
| Campaign / combo offers | Discounted products are independent: no paying-the-difference merging between separate campaign SKUs. Re-eligibility for a campaign price after cancel-and-reorder has NO query basis -- degrade, point to the campaign page / human support | [support-position] (single-ticket answer, not automatable) |

## 3. What a refund does to the instance and to gifts

| Rule | Content | Provenance |
|---|---|---|
| Retention | After a successful refund the subscription instance enters the "expired after refund" state and retention is PER RESOURCE: vCPU, memory and the fixed public IP are released within 24 hours; cloud disks are released within 15 days. Take a snapshot (or image) before submitting | [official-doc] |
| Disk kept on release | If "release disk with instance" is turned off, the cloud disks are detached and kept when the instance is released; storage charges continue and the data survives on the retained disk | [official-doc] |
| Rescue window | The official advice for an accidental unsubscription is to open the ECS console and renew the unsubscribed instance manually as soon as possible, BEFORE its resources are released. Even then the instance may still suffer data loss or a changed fixed public IP, so present it as a rescue, not as a rollback of the refund | [official-doc] |
| Manual release after expiry | "A 15-day retention window" is TOO COARSE and hides a customer-visible data-loss risk: those 15 days contain two different sub-stages. In the FIRST sub-stage (expired, not yet recycling) the compute resources AND the local disks with their data are still retained, the instance is stopped, and renewing restores it with the expiry date pushed out. In the SECOND sub-stage (expiry recycling) the compute resources are released and the local disks are kept but **their data is already cleared**. From 00:00 on day 16 the compute resources are gone and the local disks and their data are released. A cloud disk with "release disk with instance" turned off converts to pay-as-you-go, is retained, and keeps billing. The owner may release manually after expiry or renew inside the window; route the lifecycle detail itself to expiry-release-retention, this is not the refund state. The two sub-stages have literal console labels in Chinese that the customer reads on screen; quote them from anchor `expiry-release__three-stage-retention`, whose claim is hash-verified against the official page -- this file is English-only by platform rule and its stage names here are working terms, NOT the on-screen labels | [official-doc] (promoted from [support-position]: the coarse 15-day form let a customer believe the data was safe for all 15 days) |
| Gifts voided | Gifts attached to the order (coupons, extended service periods) are voided and cleared after a refund, and an expired voucher is not reusable. The voucher-paid portion does NOT follow one rule, so state the branch and never a single figure or percentage: on an UNSUBSCRIBE the official page says vouchers are refunded in proportion to the payment structure, while a DOWNGRADE refund does not return vouchers at all. These rules fork by scenario, order date and grey-release batch | [official-doc] conflict-hold: no numeric caliber may be quoted |
| Stop vs release | Stopping only shuts down compute; disks, public IP and image keep being charged. Release ends all instance billing permanently. Releasing is a manual console action with its own scheduled-release option | [official-doc] |

## 4. Hand-off boundaries (identify and refer, do not answer here)

| Customer question | Correct destination |
|---|---|
| "How much to renew / any discount path" | `area:renewal-pricing-discount` |
| "Why did this charge appear / reconcile my bill" | `area:billing-attribution-bill-check` |
| "When exactly does an expired instance auto-release" (pure lifecycle) | `area:expiry-release-retention` (this tier keeps only the refund-relevant retention segment) |
| "Overdue / trial about to expire, how to stop billing" | `area:arrears-trial-billing-stop` |
| "Convert subscription to pay-as-you-go" | `area:billing-mode-selection` |
| "Can I resize / is the target spec purchasable" | `area:instance-modify-diagnosis` |
| Disk-full / boot failure / slow IO symptoms drifting into a refund chat | the respective ECS diagnosis tiers |
| Domain / account closure, RDS or other product-line commercial actions | that product line's human ticket (evidence: closure of a related resource required its own separate ticket) |

## 5. Official references

- Unsubscription / refund rules (canonical, verified live at build time;
  the legacy `document_detail/116043.html` citation seen in tickets resolves
  here):
  `https://help.aliyun.com/zh/user-center/cancel-subscription/`
- ECS resource refund instructions (the "expired after refund" state, the
  24-hour release of vCPU / memory / fixed public IP, the 15-day release of
  cloud disks, the "release disk with instance" switch, the manual-renewal
  rescue, and the five-day no-reason one-per-year quota shared with resource
  packages and reserved instance coupons):
  `https://help.aliyun.com/zh/ecs/refund-instructions`
- Refund destinations:
  `https://help.aliyun.com/zh/user-center/user-guide/refund-destinations`
- Release an instance (stop-vs-release, scheduled release):
  `https://help.aliyun.com/zh/ecs/user-guide/release-an-instance`

Relay rule answers with their provenance label; when a customer dispute
turns on an [support-position] line, offer a human ticket instead of
escalating a guess.
