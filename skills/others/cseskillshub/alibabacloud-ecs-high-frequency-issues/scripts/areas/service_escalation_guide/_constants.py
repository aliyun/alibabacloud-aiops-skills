#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS Service Escalation Guide
==========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads, writes, caches or
prints any AccessKey / SecretKey / STS token; authentication is resolved
exclusively by the aliyun CLI default credential chain. No credential
handling exists anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
every static reference table (trigger dictionary, handoff matrix, material
field spec, promise patterns, limitations wording) is embedded here as
Python constants. There are no data files in this skill.

Content policy (tier rule, see SKILL.md Absolute Rules 3-5):
  * NO deadlines, NO escalation outcomes, NO compensation or responsibility
    findings anywhere in the output data below;
  * NO invented console paths, URLs, hotline numbers or service-plan terms:
    channel guidance stays generic and explicitly defers verification to the
    official console / human support;
  * technical and commercial symptoms are only ROUTED (handoff matrix), never
    diagnosed, by this skill.
"""

SKILL_NAME = "alibabacloud-ecs-service-escalation-guide"

# ---------------------------------------------------------------------------
# API / endpoint metadata (the CLI carries its own API metadata; these values
# are informational and used for defense-in-depth command construction only)
# ---------------------------------------------------------------------------
STS_ENDPOINT = "sts.aliyuncs.com"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
# Region used purely to reach the central STS service; NEVER used to guess a
# region for customer evidence (the entry script requires an explicit one).
STS_TRANSPORT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Timeouts and limits
# ---------------------------------------------------------------------------
# Per-call timeout (seconds) for every aliyun CLI subprocess invocation.
DEFAULT_CLI_TIMEOUT = 60
# Page size for DescribeInstances pagination (API max is 100; 50 is plenty).
PAGE_SIZE = 50
# Hard guardrail on the number of pages fetched per evidence run.
MAX_PAGES = 10
# DescribeInstanceStatus accepts a bounded id list per call; chunk at this.
MAX_IDS_PER_STATUS_CALL = 50

# Instance-id shape guard: ids that do not match are reported as invalid and
# excluded from the query instead of being sent to the API.
INSTANCE_ID_PATTERN = r"^i-[a-z0-9-]{4,40}$"

# ---------------------------------------------------------------------------
# Demand-area screening dictionary (English customer wording; this skill's
# user-facing content is English-only per platform rule 4.1.2)
# ---------------------------------------------------------------------------
# Phrases that mark the "follow-up / escalation" area (ticket progress stuck).
ESCALATION_TERMS = [
    "no response",
    "no reply",
    "not replied",
    "never replied",
    "nobody is following up",
    "no one is following up",
    "no one followed up",
    "no progress",
    "is stuck",
    "still not handled",
    "hasn't been handled",
    "has not been handled",
    "still no update",
    "heard nothing",
    "chase my ticket",
    "follow up on my ticket",
    "push my ticket",
    "expedite",
    "escalate my ticket",
    "escalate the ticket",
    "ticket progress",
    "status of my ticket",
    "repeatedly submitted",
    "submitted again",
    "raised it many times",
    "days and nothing",
    "waiting since",
    "\u5de5\u5355",
    "\u50ac\u5355",
    "\u50ac\u4e00\u4e0b",
    "\u52a0\u6025",
    "\u6ca1\u4eba\u5904\u7406",
    "\u65e0\u4eba\u5904\u7406",
    "\u6ca1\u4eba\u56de\u590d",
    "\u65e0\u4eba\u56de\u590d",
    "\u6ca1\u6709\u56de\u590d",
    "\u672a\u56de\u590d",
    "\u8fd8\u6ca1\u5904\u7406",
    "\u8fd8\u6ca1\u7ed9\u6211\u5904\u7406",
    "\u8fdb\u5ea6",
    "\u56de\u7535\u8bdd",
    "\u5c3d\u5feb\u56de\u590d",
    "\u591a\u4e45\u56de\u590d",
    "\u53cd\u9988\u7684\u95ee\u9898",
]

# Phrases that mark the "service complaint" area.
COMPLAINT_TERMS = [
    "complain",
    "complaint",
    "file a complaint",
    "service attitude",
    "attitude is terrible",
    "rude",
    "unacceptable",
    "satisfaction",
    "bad experience with support",
    "apology",
    "hold accountable",
    "report the engineer",
    "lodge a grievance",
    "\u6295\u8bc9",
    "\u4e3e\u62a5",
    "\u6001\u5ea6",
    "\u6076\u52a3",
    "\u6577\u884d",
    "\u592a\u8fc7\u5206",
    "\u5403\u76f8",
    "\u7d22\u8d54",
    "\u8d54\u507f",
    "\u5c65\u804c",
    "\u6076\u610f\u963b\u65ad",
    "12315",
    "\u5de5\u4fe1\u90e8",
]

# Technical areas: (area key, trigger terms, handoff target, handoff note).
# Detection here is ONLY for routing; this skill never diagnoses them.
TECHNICAL_ROUTES = [
    (
        "disk-capacity",
        ["disk full", "disk-full", "disk is full", "no space left",
         "cannot write", "write fails", "inode", "too many small files"],
        "area:disk-expand-diagnosis",
        "disk/filesystem capacity or inode usage inside the guest",
    ),
    (
        "disk-expand",
        ["expansion did not take effect", "expand not effective",
         "disk still shows", "partition not extended",
         "extended volume not visible"],
        "area:disk-expand-diagnosis",
        "disk expansion / partition or volume not effective",
    ),
    (
        "instance-state",
        ["cannot start", "can't start", "won't start", "stuck starting",
         "stuck stopping", "intermediate state", "doesn't boot",
         "won't boot", "start or stop is stuck"],
        "area:instance-state-diagnosis",
        "instance lifecycle-state anomaly (start/stop/boot)",
    ),
    (
        "disk-io",
        ["disk io slow", "io is slow", "slow disk", "disk latency",
         "iops too low", "throughput below spec", "io hang"],
        "area:resource-bottleneck",
        "disk IO performance",
    ),
    (
        "purchase-inventory",
        ["out of stock", "sold out", "no inventory", "cannot buy",
         "resource unavailable when purchasing"],
        "area:instance-modify-diagnosis",
        "resource inventory / purchase or specification change",
    ),
]

# Adjacent process areas: same shape as TECHNICAL_ROUTES.
ADJACENT_ROUTES = [
    (
        "punishment-appeal",
        ["violation penalty", "penalized my account", "banned",
         "blocked for violation", "appeal the punishment", "appeal notice"],
        "area:punishment-appeal-guide",
        "violation punishment and appeal (an appeal is NOT a ticket chase)",
    ),
    (
        "refund",
        ["refund", "unsubscribe", "give me my money"],
        "area:unsubscribe-refund",
        "unsubscription / refund (commercial action, never done here)",
    ),
    (
        "invoice-contract",
        ["invoice", "contract", "billing statement document"],
        "invoice / contract process (no skill owns it; the console finance "
        "flow, otherwise a human ticket)",
        "invoice / contract process",
    ),
    (
        "account-transfer",
        ["account transfer", "transfer the account", "change account owner"],
        "the Alibaba Cloud account ownership transfer process (console ticket; no skill here performs it)",
        "account ownership transfer process",
    ),
    (
        "business-callback",
        ["call me back", "phone me", "phone call", "business manager",
         "account manager", "human agent call"],
        "the customer's account manager or a console ticket asking for a callback (no callback is promised here)",
        "business contact / callback demand (no callback is promised here)",
    ),
    (
        "product-suggestion",
        ["feature request", "product suggestion", "improvement suggestion",
         "you should add"],
        "product feedback process (no published skill owns it; the console "
        "feedback flow, otherwise a human ticket)",
        "product suggestion / feedback submission",
    ),
    (
        "invalid-ticket",
        ["test ticket", "submitted by mistake", "wrong ticket",
         "ignore that ticket"],
        "closing the ticket in the console with a note (no diagnosis is needed)",
        "test / misfiled ticket handling",
    ),
]

# ---------------------------------------------------------------------------
# Expectation discipline: promise-shaped wording the script flags so the
# agent can reword the demand into a deliverable request (rule: the skill
# must never carry, restate as fact, or relay an undeliverable commitment).
# ---------------------------------------------------------------------------
PROMISE_PATTERNS = [
    (r"\bguarantee", "remove the guarantee demand; ask for a concrete, "
                      "deliverable step such as one progress update today"),
    (r"\bcompensat\w*", "drop compensation wording from the package; "
                        "monetary outcomes are decided only by human "
                        "commercial processes"),
    (r"\brefund", "refund demands belong to the unsubscribe/refund area, "
                  "not to a follow-up or complaint package"),
    (r"\bwithin\s+\d+\s*(minutes?|hours?|days?|business|working)",
     "replace the demanded deadline with a deliverable expectation such as "
     "'a first progress update before end of today'"),
    (r"\b(sue|lawyer|legal action|media exposure)\b",
     "de-escalate the wording; keep only facts, impact and a deliverable "
     "request in the package"),
    (r"\b(penalize|fire|punish)\s",
     "remove accountability demands; the complaint package states impact "
     "and asks for a review, nothing more"),
    (r"\bpromise\b", "the package must ask, not extract promises; reword to "
                     "'request' / 'confirm next checkpoint with support'"),
]

# ---------------------------------------------------------------------------
# Material field spec (build-package). label -> (flag, core?)
# "core" fields feed the MISSING INPUTS list: a half package is still emitted
# when they are absent (decision-tree step 4: never replace output by
# interrogation).
# ---------------------------------------------------------------------------
PACKAGE_FIELDS = {
    "escalate": [
        ("ticket_id", "--ticket-id", True,
         "Support ticket number as pasted by the customer (pass-through "
         "text; this skill cannot query the ticket system to verify it)"),
        ("submitted_at", "--submitted", True,
         "First submission time, customer-stated, e.g. '2026-09-15 10:20 +08'"),
        ("waited_so_far", "--waited", True,
         "Elapsed wait, customer-stated, e.g. '3 days'"),
        ("replies_so_far", "--replies", False,
         "One-line summary of any replies received ('none' is valid)"),
        ("business_impact", "--impact", True,
         "Concrete business impact and urgency evidence"),
        ("expected_outcome", "--expectation", True,
         "Deliverable expectation (the script flags promise-shaped wording)"),
        ("affected_resources", "--impact-resources", False,
         "Instances/regions affected, as stated by the customer"),
    ],
    "complaint": [
        ("complaint_subject", "--subject", True,
         "What the complaint is about: timeliness / outcome / attitude / "
         "other; pass one of those words"),
        ("ticket_id", "--ticket-id", False,
         "Related support ticket number if any (pass-through text)"),
        ("fact_timeline", "--submitted", True,
         "Key dates of the service history, customer-stated"),
        ("replies_so_far", "--replies", False,
         "Communication history so far, one line"),
        ("business_impact", "--impact", False,
         "Impact of the service issue itself"),
        ("expected_outcome", "--expectation", True,
         "Deliverable expectation for the complaint handling"),
    ],
}

# ---------------------------------------------------------------------------
# Verbatim limitations block appended to every package (rule set: no ticket
# access, no promises, customer-stated sources).
# ---------------------------------------------------------------------------
LIMITATIONS_BLOCK = [
    "LIMITATIONS OF THIS GUIDE (read-only, guide-type):",
    "- This guide cannot view or change support tickets: no ticket-status "
    "query, no expediting, no priority change, no withdrawal, no submission "
    "on your behalf.",
    "- Every timeline/progress fact above is customer-stated; nothing in it "
    "is verified against any ticket system.",
    "- No handling deadline, escalation result, responsibility finding, "
    "compensation or refund outcome is promised or implied anywhere in this "
    "package.",
    "- Official support entry points and service-plan terms must be "
    "confirmed in the official console or with human support; this package "
    "intentionally quotes no unverified path, URL or time limit.",
]

# ---------------------------------------------------------------------------
# Generic self-help next steps (channel entries deliberately NOT named;
# see SKILL.md Absolute Rule 5 and the tier evidence gaps).
# ---------------------------------------------------------------------------
GUIDANCE_STEPS = [
    "Follow up on the ORIGINAL ticket thread through the official support "
    "entry of the console you normally use (confirm the current entry there; "
    "this guide deliberately does not quote button paths).",
    "Paste the prepared package as your follow-up message: ticket number, "
    "customer-stated timeline, business impact, deliverable expectation.",
    "Avoid opening duplicate tickets to 'speed things up': parallel tickets "
    "split the context and are generally counter-productive.",
    "If a wide-scale service incident may be behind the wait, check the "
    "public service-status announcements yourself; it is the only progress "
    "proxy this guide can point to (the guide reads no systems itself).",
    "For a complaint, submit the complaint package through the official "
    "feedback entry of the same console, or ask the human support channel "
    "for the complaint route; keep a copy of your timeline.",
    "Anything beyond these steps (expediting, reassignment, tier upgrades, "
    "compensation) is decided by human support processes; request it, and do "
    "not accept commitments from this guide because it makes none.",
]

# ---------------------------------------------------------------------------
# Evidence appendix note (what the two read-only queries do and do NOT say).
# ---------------------------------------------------------------------------
EVIDENCE_NOTE = (
    "The read-only ECS queries above evidence RESOURCE facts (existence, "
    "region, zone, type, lifecycle state) at the query time shown. They "
    "carry no information whatsoever about ticket acceptance, queue "
    "position, replies or handling progress."
)
