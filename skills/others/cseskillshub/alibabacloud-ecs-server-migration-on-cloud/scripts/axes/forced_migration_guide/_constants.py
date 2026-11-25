"""Static constants for the alibabacloud-ecs-server-migration-on-cloud: forced-migration-guide skill.

This is a READ-ONLY guidance (RO_GUIDE) skill. It only ever queries cloud facts
through the single read-only action listed in ALLOWED_READ_ACTIONS, and returns
human-followable self-service steps. It never changes cloud resources, never
runs commands inside a customer instance, and never submits billing or
compensation requests.

All knowledge tables that would otherwise be data files are embedded here as
Python string constants (see the delivery rule: scripts/ holds code only).
"""

# ---------------------------------------------------------------------------
# Identity & observability
# ---------------------------------------------------------------------------
SKILL_NAME = "alibabacloud-ecs-server-migration-on-cloud: forced-migration-guide"

# User-Agent prefix. A fresh 32-hex session id is appended per run by _cli.py,
# giving the full template:
#   AlibabaCloud-Agent-Skills/alibabacloud-ecs-server-migration-on-cloud: forced-migration-guide/<32-hex>
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills/" + SKILL_NAME

# ---------------------------------------------------------------------------
# Cloud CLI surface (product codes and API version)
# ---------------------------------------------------------------------------
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"

# The ONLY ECS action this skill auto-invokes. Every other ECS action is a
# write/change action or has an unconfirmed RAM action name and is therefore
# out of the automatic call chain (kept as console-only guidance).
ALLOWED_READ_ACTIONS = ("DescribeInstances",)

# DescribeInstances parameter that carries the bound security groups, used as
# the exposure self-check anchor.
ADDITIONAL_ATTR_SECURITY_GROUPS = "securityGroupIds"

# ---------------------------------------------------------------------------
# CLI hardening
# ---------------------------------------------------------------------------
CLI_TIMEOUT_SECONDS = 30          # per subprocess call timeout (MUST 7.6.1)
CLI_MAX_RETRIES = 3               # retries for transient errors only
CLI_BACKOFF_BASE_SECONDS = 1.0    # exponential backoff base
MAX_INSTANCE_IDS = 100           # cap on instance ids echoed per report

# ---------------------------------------------------------------------------
# Console entry points (from ticket dialogues; verify currency before use).
# External URLs are allowed as absolute links; repo files use relative paths.
# ---------------------------------------------------------------------------
DOC_URLS = {
    "image_from_instance": "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance",
    "copy_image": "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image",
    "create_instance_from_image": "https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-imag",
    "system_events": "https://help.aliyun.com/zh/ecs/user-guide/summary",
    "ecs_sla": "https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud201909241949_62160.html",
    "sla_entry_usercenter": "https://usercenter2.aliyun.com/sla/availabilityhome",
    "sla_entry_billing": "https://billing-cost.console.aliyun.com/sla/availabilityhome",
    "downgrade_refund_rules": "https://help.aliyun.com/zh/user-center/description-of-downgrade-refund-rules",
    "renewal_downgrade": "https://help.aliyun.com/zh/ecs/downgrade-instance-configurations-during-renewal",
    "burstable_billing": "https://help.aliyun.com/zh/ecs/user-guide/billing",
    "expense_by_instance": "https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance",
    "unsubscribe": "https://help.aliyun.com/zh/user-center/cancel-subscription/",
    "refund_destinations": "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations",
    "coupons_view": "https://billing-cost.console.aliyun.com/coupons/coupon",
    "auto_snapshot_policy": "https://help.aliyun.com/zh/ecs/user-guide/create-an-automatic-snapshot-policy-1",
}

# Alibaba Cloud internal (VPC) resolver addresses, quoted from ticket dialogue.
INTERNAL_DNS = ("100.100.2.136", "100.100.2.138")

# ---------------------------------------------------------------------------
# Read-only, human-followable guidance blocks, keyed by intent. The entry script
# prints the relevant block after gathering facts. Every step is a console or
# in-guest READ-ONLY action for the customer to perform; the skill performs none.
# ---------------------------------------------------------------------------
GUIDE_MIGRATION = """
INTENT: region / data-center decommission and forced migration (read-only guidance)

What the platform does NOT do for you: a decommission does not move your workload,
and it does not automatically restore your website. You migrate the instance
yourself with a cross-region custom image. Do all five steps in order and keep the
old instance until the new one is verified.

Step 1 - Create a custom image from the source instance (source region):
  Console: ECS > Instances > select instance > More > Disk and Image > Create Custom Image.
  Doc: {image_from_instance}
  Expected result: a new custom image id (m-xxxx) in Available state in the source region.

Step 2 - Copy the custom image to the target region:
  Console: ECS > Images > select the custom image > Copy Image > choose target region.
  Doc: {copy_image}
  Expected result: after the copy task succeeds, the same image id appears in the target region.

Step 3 - Create a new instance from the copied image in the target region:
  Console: ECS > Images > select copied image > Create Instance. Re-create the security
  groups, then attach the application data and configuration.
  Doc: {create_instance_from_image}

Step 4 - Verify the new instance serves your workload BEFORE touching the old one:
  Confirm the service responds on the new public IP, then repoint DNS / EIP / allow-lists.

Step 5 - Only after Step 4 passes, release the old instance:
  Releasing the old instance is irreversible and deletes its data. Do not release until
  the new instance is confirmed working and you have the paid remaining value accounted for.

Completion evidence checklist (collect these to prove the migration is closed):
  [ ] source custom image id (m-xxxx)
  [ ] copy destination region and copied image id
  [ ] new instance id and the image id it is running
  [ ] public reachability test on the new instance (screenshot / curl output you ran)
  [ ] old instance released date (only after the above are green)

Costed notes seen in real tickets (surface these to a human, do not compute a number):
  - System disk has a minimum size limit, and splitting an order may change the price,
    so an identical re-build is not always a 1:1 cost. Residual-value / equal-amount
    vouchers are issued only after a business or billing specialist reviews them.

This skill will NOT: release or stop the old instance for you, order a new instance,
or issue any voucher. Residual-value compensation is a manual business/billing action.
""".format(**DOC_URLS)

GUIDE_INCIDENT = """
INTENT: unplanned reboot / planned maintenance reboot, and availability impact (read-only)

First, classify the notice. This skill has no cloud API to read the platform event on
your behalf, so confirm the event type from YOUR evidence: the SMS / message-center
notice or the ECS console instance-event page. Paste the notice text or a screenshot
back so attribution is not guessed.

Branch A - SystemMaintenance.Reboot (planned maintenance):
  Cause: a latent risk on the underlying host; the platform schedules a reboot window and
  notifies roughly 24-48h ahead. You can usually move the reboot to a low-peak time inside
  the notified window yourself.
  Console: ECS > Instances > select instance > More > Instance Status > Restart, choose the
  scheduled window. Restart has a Normal mode and a Force Restart mode; Force Restart can
  lose unwritten data, so prefer Normal and only force if the guest is unresponsive.

Branch B - SystemFailure.Reboot (unexpected host failure, notified after the fact):
  Cause: an unexpected software/hardware failure on the underlying host; the platform
  restarted and migrated your instance to a healthy host to recover it.
  Follow-up you own: configure application auto-start on boot and add app-level redundancy
  so a single host event does not take the service down.

Availability compensation (SLA) is APPLICATION-BASED, not automatic. Unified wording:
  - You may file a request after the 5th working day of each month for the previous month
    instances that did not meet the availability commitment.
  - The request must be filed within 2 months after the end of the affected month; overdue
    requests are not accepted.
  - SLA terms: {ecs_sla}
  - Entry points seen in tickets (confirm the current authoritative one before submitting):
    {sla_entry_usercenter}  or  {sla_entry_billing}
  - Re-verify: after you submit, paste back the acceptance status so the deadline is tracked.

Read the system event explanation: {system_events}

This skill will NOT reboot or restart your instance, and will NOT prove host health: those
need the ticket back-end diagnosis or your own console evidence. It standardizes the wording,
the deadline math, and the checklist only.
""".format(**DOC_URLS)

GUIDE_BILLING = """
INTENT: fee / refund disputes tied to a platform action or a rule (read-only recompute)

Rule-based recompute (apply the published formula to YOUR numbers; no cloud API is used):
  - Downgrade refund = (order amount actually paid - consumed amount) x (new-vs-old config
    price ratio). The consumed amount uses the official LIST price daily rate x used
    duration, NOT the discounted price you paid. Doc: {downgrade_refund_rules}
  - Unsubscribe (non-full refund) = order amount actually paid - consumed amount, where
    consumed is again at official list price x used duration. Doc: {unsubscribe}
    Renewal-window downgrade is gated by the 15-day-before-expiry window. Doc: {renewal_downgrade}
  - Burstable-performance credit burn: sustained CPU above the baseline consumes earned
    credits, and in unlimited mode extra credit fees are billed. Confirm the hourly figures
    yourself. Doc: {burstable_billing}

Self-service evidence gathering (you pull the numbers; this skill cannot read billing):
  - Bill by instance with an hourly filter: {expense_by_instance}
  - Coupons / vouchers received: {coupons_view}
  - Refund destinations and rules: {refund_destinations}
  - Export the CSV, screenshot the hourly line and the CPU monitor curve.

Escalation evidence pack (hand this to a billing specialist):
  [ ] instance id and the disputed billing period
  [ ] exported hourly cost detail (CSV) and monitor screenshots
  [ ] the order/refund page amount screenshot
  [ ] the notification or open-time you rely on
  [ ] a short timeline of prior tickets/calls

Hard limits to state plainly:
  - Post-paid (pay-as-you-go) consumption that already occurred cannot be refunded, waived,
    or converted to subscription; only a forward change to fixed-bandwidth billing is possible.
  - A manual goodwill voucher is "not compensation, one-time", and it is a specialist decision.
  - A self-service unsubscribe and a negotiated manual refund are mutually exclusive: confirm
    the on-page amount before submitting (submitting may cancel the manual path).
  - The platform does not retain historical per-process CPU, so past usage cannot be re-derived.

This skill will NOT adjust the bill, waive fees, or issue a voucher: those are manual actions.
""".format(**DOC_URLS)

GUIDE_EXPOSURE = """
INTENT: suspected breach / traffic / blame dispute where cloud side shows no platform fault (read-only)

The instance list below reports the security groups each instance is bound to. That binding is
the anchor for an exposure self-check; review those rules in the console (this skill will not
open, read, or change them for you).

Port-exposure self-check (console, read first):
  - Are remote ports (22 / 3389) open to 0.0.0.0/0? Narrow the source CIDR to your office/VPN.
  - Block the specific abusive source IP in the security group as an immediate stop-loss.
  - Turn on an automatic snapshot policy for a data safety net (note: snapshots incur storage
    cost). Doc: {auto_snapshot_policy}

In-guest READ-ONLY self-check commands (you run these and paste the output; this skill never
logs into or runs anything inside your instance):
  Linux:
    top            # see which process is consuming CPU right now (cannot replay history)
    cat /etc/resolv.conf   # check DNS; if public DNS is set and causing egress, switch to the
                           # internal resolvers {internal_dns} yourself
    view your application access logs for who is hitting the service
  Windows (equivalent intent; exact commands were not confirmed in ticket data, confidence medium):
    use Task Manager / Resource Monitor for current per-process CPU, and review IIS/app logs.

Attribution three-way (state the evidence, do not overclaim):
  1) Platform infrastructure fault -> go to the incident/SLA branch above.
  2) Customer application / self-installed program -> the app owner analyzes app-side logs.
  3) External access (attack / scraping / egress abuse) -> security hardening + stop-loss above.

Standard wordings:
  - Another user's identity: Alibaba Cloud cannot disclose another account's identity; if you
    have reported to police, judicial authorities may obtain it through legal process. Only a
    public geo approximation may be shared.
  - Written proof: there is no official "host is healthy" letter; the accepted substitute is a
    Cloud Monitor screenshot plus the ticket reply screenshot sent to the counterparty.

This skill will NOT: prove host health, fetch historical process data, reveal another account,
or decide any compensation.
""".format(auto_snapshot_policy=DOC_URLS["auto_snapshot_policy"],
           internal_dns=" / ".join(INTERNAL_DNS))

GUIDE_BY_INTENT = {
    "migration": GUIDE_MIGRATION,
    "incident": GUIDE_INCIDENT,
    "billing": GUIDE_BILLING,
    "exposure": GUIDE_EXPOSURE,
}

BOUNDARY_STATEMENT = """
BOUNDARY (read-only guide): This skill reads only DescribeInstances (status, region, bound
security groups) inside the current account and the single RegionId you pass. Cross-account
data, platform back-end host diagnosis, system-event delivery, Cloud Monitor history, and any
bill/fee figures are NOT visible to it. Business, approval, compensation, voucher, and
account-adjustment actions are always manual. Anything needing in-guest readings must be run
by the customer and pasted back.
"""

NEXT_ACTION_BY_STATUS = {
    "OK": "Follow the printed self-service steps; collect the completion-evidence checklist; route any compensation/adjustment to a human specialist.",
    "DEGRADED": "Facts were only partially resolved (no matching instance, or credential/event evidence missing). Confirm the RegionId and account ownership, or supply the requested notice/screenshot, then re-run.",
    "FAIL": "The read-only query could not complete. Retry shortly; if it reports a permission error, grant only the listed read action; never place credentials on disk or in chat.",
}
