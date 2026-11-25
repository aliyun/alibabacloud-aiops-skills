#!/usr/bin/env python3
"""Single entry point for ECS key pair and passwordless logon diagnosis.

The agent runs this script and reads its report; it must not hand-write aliyun
commands. Every cloud call happens here, through the whitelisted transport layer
in ``_cli.py``.

Evidence queries (``Describe*``, ``GetCallerIdentity``) mutate nothing and run on
their own. Two calls change state and need a confirmation naming their exact
target on the same run: one published inspection command inside the guest
(``--run-inspection`` plus ``--confirm-inspection``), and one pre-change snapshot
of one disk (``--snapshot-disk-id`` plus ``--confirm-snapshot``). Without the
matching confirmation neither call happens, and the report prints it as a step for
a human instead.

    python3 scripts/keypair_login_diagnosis.py \
        --instance-id i-2ze8fshtf0wkynkjg734 --region-id cn-beijing \
        --symptom passwordless-workbench --entry workbench-passwordless \
        --error-text "Instance logon failed: a temporary SSH key cannot be used"

    python3 scripts/keypair_login_diagnosis.py \
        --instance-id i-2ze8fshtf0wkynkjg734 --region-id cn-beijing \
        --entry local-ssh --run-inspection "sshd -T" --confirm-inspection "sshd -T"

The report carries: the evidence collected (one line per query, failures included),
what ran inside the guest and what came back, the error signature recognised, the
branch conclusion drawn from those two, the manual steps that follow, the handoff
when the symptom belongs elsewhere, and the ``STATUS`` / ``NEXT_ACTION`` tail.

It never changes instance power, never touches a key pair binding, a password or a
security group rule, never runs a command outside the published inspection list,
and never echoes credential material.
"""

import argparse
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import (  # noqa: E402
    CliError,
    mask_secrets,
    new_session_id,
    run_cli,
)
from _constants import (  # noqa: E402
    ACTION_CREATE_SNAPSHOT,
    ACTION_DESCRIBE_ASSISTANT_STATUS,
    ACTION_DESCRIBE_FULL_STATUS,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_RUN_COMMAND,
    AUTHORIZED_KEYS_FACTS,
    CLOUD_ASSISTANT_FACTS,
    CODE_CLI_UNAVAILABLE,
    CODE_CONFIRMATION_REQUIRED,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_NO_PERMISSION,
    CODE_POLICY_REFUSED,
    CONNECTION_ENTRIES,
    CONSOLE_ENTRIES,
    CREDENTIAL_FACTS,
    ERROR_SIGNATURES,
    EXECUTABLE_INSPECTION_COMMANDS,
    GUEST_IN_PROGRESS_STATUSES,
    GUEST_OUTPUT_MAX_CHARS,
    GUEST_POLL_INTERVAL_SECONDS,
    GUEST_READING_RULES,
    GUEST_WAIT_DEFAULT_SECONDS,
    GUEST_WAIT_MAX_SECONDS,
    GUEST_READINGS_LINUX,
    GUEST_READINGS_WINDOWS,
    HANDOFF_TABLE,
    INSPECTION_COMMAND_NAME,
    INSPECTION_DEFAULT_SHELL,
    INSPECTION_SHELL_TYPES,
    INVOCATION_HISTORY_ROWS,
    KEY_PAIR_EFFECT_RULE,
    KEY_PAIR_NAMING_RULES,
    MAX_FIELD_PREVIEW_CHARS,
    NEVER_GRANTED_ACTION_NAMES,
    NO_RESTART_ALTERNATIVE,
    OFFICIAL_DOCS,
    PAGE_SIZE,
    PRODUCT_ECS,
    RAM_POLICY_ACTIONS,
    SKILL_NAME,
    SNAPSHOT_DESCRIPTION,
    SNAPSHOT_FIRST_GATE,
    SNAPSHOT_NAME_PREFIX,
    SNAPSHOT_RISK_NOTES,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    SYMPTOM_TAXONOMY,
    TICKET_QUOTED_LINKS,
    TICKET_QUOTED_LINKS_NOTE,
    WINDOWS_LOGON_FACTS,
)

ENTRY_DESCRIPTIONS = {
    "workbench-passwordless": "console passwordless logon, temporary SSH key",
    "workbench-key": "console logon with a chosen key pair",
    "local-ssh": "ssh from the customer's own workstation",
    "rdp": "Remote Desktop client",
    "vnc": "console VNC session",
    "unknown": "not stated yet",
}

# Lower-cased customer wording mapped onto a symptom class, used only when the
# caller did not pass --symptom. Phrases, not bare words: "key" alone would
# route a disk-encryption or licence question in here by mistake.
SYNONYM_PHRASES = (
    ("passwordless login", "passwordless-workbench"),
    ("temporary ssh key", "passwordless-workbench"),
    ("cannot log in", "passwordless-workbench"),
    ("authorized_keys", "authorized-keys-drift"),
    ("key pair", "keypair-not-effective"),
    ("permission denied (publickey)", "client-key-error"),
    ("unprotected private key", "client-key-error"),
    ("too many authentication failures", "client-key-error"),
    ("0xd07", "windows-rdp-lockout"),
    ("locked out", "windows-rdp-lockout"),
    ("remote desktop", "windows-multi-user"),
    ("passkey", "passkey-third-party"),
    ("fingerprint", "passkey-third-party"),
    ("create key pair failed", "password-reset-failed"),
    ("reset password", "password-reset-failed"),
    ("forgot the password", "credential-lost"),
    ("lost the private key", "credential-lost"),
    ("changed the operating system", "os-change-or-image"),
    ("community image", "os-change-or-image"),
)

# A report built on a broken credential chain is not a degraded report, it is a
# meaningless one, so these codes stop the run instead of continuing.
FATAL_CLI_CODES = (CODE_INVALID_CREDENTIAL, CODE_CLI_UNAVAILABLE, CODE_POLICY_REFUSED)
PERMISSION_CODES = (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY)

RAM_ACTION_BY_NAME = dict(zip(
    (ACTION_DESCRIBE_INSTANCES, ACTION_DESCRIBE_FULL_STATUS,
     ACTION_DESCRIBE_ASSISTANT_STATUS, ACTION_DESCRIBE_INVOCATIONS,
     ACTION_RUN_COMMAND, ACTION_CREATE_SNAPSHOT),
    ("ecs:DescribeInstances", "ecs:DescribeInstancesFullStatus",
     "ecs:DescribeCloudAssistantStatus", "ecs:DescribeInvocations",
     "ecs:run-command", "ecs:create-snapshot")))


class Evidence(object):
    """One row per cloud query attempted, successful or not, with its outcome."""

    def __init__(self):
        self.rows = []
        self.fatal = None
        self.denied = []

    def add(self, step, action, status, detail="", code=""):
        preview = mask_secrets(detail)
        if len(preview) > MAX_FIELD_PREVIEW_CHARS:
            preview = preview[:MAX_FIELD_PREVIEW_CHARS] + "..."
        self.rows.append({"step": step, "action": action, "status": status,
                          "code": code, "detail": preview})
        if status == "failed" and code in PERMISSION_CODES:
            self.denied.append(action)

    @property
    def failed_steps(self):
        return [row["step"] for row in self.rows if row["status"] != "ok"]


def _call_ecs(action, params, session_id, timeout, evidence, step):
    """Run one whitelisted ECS query and record the outcome without inventing any."""
    if evidence.fatal is not None and evidence.fatal.code in (
            CODE_INVALID_CREDENTIAL, CODE_CLI_UNAVAILABLE):
        evidence.add(step, action, "skipped",
                     "not attempted: the credential chain or the CLI itself is "
                     "unusable, so a repeat would fail the same way",
                     evidence.fatal.code)
        return None
    try:
        body = run_cli(PRODUCT_ECS, action, params, session_id=session_id,
                       timeout=timeout)
    except CliError as exc:
        evidence.add(step, action, "failed", exc.message, exc.code)
        if exc.code in FATAL_CLI_CODES:
            evidence.fatal = exc
        return None
    evidence.add(step, action, "ok", _summarise(body))
    return body


def _summarise(body):
    """Reduce a response body to one factual line."""
    if body is None:
        return "no body returned"
    if not body:
        return "empty body"
    for container in ("Instances", "InstanceFullStatusSet",
                      "InstanceCloudAssistantStatusSet", "Invocations"):
        items = _unwrap(body, container)
        if items or container in body:
            return "%s entr(y|ies) returned" % len(items)
    if "TotalCount" in body:
        return "TotalCount=%s" % body.get("TotalCount")
    return "response received"


def _unwrap(body, container):
    """Return the list inside an RPC envelope, tolerating either spelling."""
    if not isinstance(body, dict):
        return []
    outer = body.get(container)
    if isinstance(outer, list):
        return outer
    if isinstance(outer, dict):
        for key in sorted(outer):
            if isinstance(outer[key], list):
                return outer[key]
    return []


def collect(args, session_id, evidence):
    """Query the instance, its health, the agent channel and the audit trail."""
    instance_params = {"RegionId": args.region_id,
                       "InstanceIds": json.dumps([args.instance_id]),
                       "PageSize": PAGE_SIZE}
    if args.key_pair_name:
        instance_params["KeyPairName"] = args.key_pair_name
    body = _call_ecs(ACTION_DESCRIBE_INSTANCES, instance_params, session_id,
                     args.timeout, evidence, "instance-facts")
    instances = _unwrap(body, "Instances")
    if args.instance_id:
        # A filtered read that answers with another instance is treated as no
        # answer at all: the diagnosis never moves onto a neighbour record.
        instances = [row for row in instances
                     if str(row.get("InstanceId") or "") == str(args.instance_id)]

    body = _call_ecs(ACTION_DESCRIBE_FULL_STATUS,
                     {"RegionId": args.region_id, "InstanceId.1": args.instance_id,
                      "PageSize": PAGE_SIZE}, session_id, args.timeout, evidence,
                     "health-status")
    statuses = _unwrap(body, "InstanceFullStatusSet")

    body = _call_ecs(ACTION_DESCRIBE_ASSISTANT_STATUS,
                     {"RegionId": args.region_id, "InstanceId.1": args.instance_id,
                      "PageSize": PAGE_SIZE}, session_id, args.timeout, evidence,
                     "assistant-status")
    assistants = _unwrap(body, "InstanceCloudAssistantStatusSet")

    body = _call_ecs(ACTION_DESCRIBE_INVOCATIONS,
                     {"RegionId": args.region_id, "InstanceId": args.instance_id,
                      "IncludeOutput": "false", "PageSize": PAGE_SIZE},
                     session_id, args.timeout, evidence, "execution-history")
    invocations = _unwrap(body, "Invocations")

    return {
        "instance": instances[0] if instances else {},
        "instance_count": len(instances),
        "full_status": statuses[0] if statuses else {},
        "assistant": assistants[0] if assistants else {},
        "invocation_rows": invocations[:INVOCATION_HISTORY_ROWS],
        "invocation_total": len(invocations),
    }


def _address(instance, key):
    value = instance.get(key)
    if isinstance(value, dict):
        value = value.get("IpAddress") or value.get("EipAddress") or []
    if isinstance(value, list):
        joined = ",".join([str(item) for item in value if item])
        return joined or "none recorded"
    return str(value) if value else "none recorded"


def public_address(instance):
    for key in ("PublicIpAddress", "EipAddress"):
        found = _address(instance, key)
        if found != "none recorded":
            return found
    return "none recorded"


def private_address(instance):
    vpc = instance.get("VpcAttributes") or {}
    if isinstance(vpc, dict) and vpc:
        found = _address(vpc, "PrivateIpAddress")
        if found != "none recorded":
            return found
    return _address(instance, "InnerIpAddress")


def operation_locks(instance):
    locks = instance.get("OperationLocks") or {}
    if isinstance(locks, dict):
        locks = locks.get("LockReason") or []
    if isinstance(locks, str):
        locks = [locks]
    return [str(item) for item in locks if item] or ["none"]


def match_signatures(error_text):
    """Return every error signature whose wording appears in the pasted text."""
    if not error_text:
        return []
    probe = error_text.lower()
    hits = []
    for tokens, source, verdict, action, side in ERROR_SIGNATURES:
        for token in tokens:
            if token in probe:
                hits.append({"matched": token, "source": source, "verdict": verdict,
                             "action": action, "fix_side": side})
                break
    return hits


def classify(args, hits):
    """Choose the routing branch: explicit symptom, then signature, then wording."""
    if args.symptom and args.symptom != "unknown":
        return args.symptom
    probe = " ".join([(args.error_text or ""), (args.note or "")]).lower()
    for phrase, symptom in SYNONYM_PHRASES:
        if phrase in probe:
            return symptom
    if hits:
        side = hits[0]["fix_side"]
        if side == "customer-local":
            return "client-key-error"
        if side == "cloud-side":
            return "passwordless-workbench"
        if side == "guest-and-console":
            return "windows-rdp-lockout"
    if args.entry == "workbench-passwordless":
        return "passwordless-workbench"
    if args.entry in ("local-ssh", "workbench-key"):
        return "keypair-not-effective"
    if args.entry == "rdp":
        return "windows-multi-user"
    return "unknown"


def handoff_for(needle):
    """Look a handoff row up by its trigger wording."""
    head = needle.split(",")[0].lower().strip()
    for trigger, boundary, target in HANDOFF_TABLE:
        if head in trigger.lower():
            return {"trigger": trigger, "boundary": boundary, "target": target}
    return {"trigger": needle, "boundary": "outside this tier",
            "target": "human support"}


def guest_readings(os_type):
    if "windows" in (os_type or ""):
        return GUEST_READINGS_WINDOWS
    return GUEST_READINGS_LINUX


def agent_is_online(assistant):
    return str(assistant.get("CloudAssistantStatus") or "").strip().lower() in (
        "true", "1", "online", "running")


def analyse(args, facts, hits, branch):
    """Turn the collected evidence into findings, guidance and handoffs."""
    findings = []
    guidance = []
    handoffs = []
    instance = facts["instance"]
    assistant = facts["assistant"]
    online = agent_is_online(assistant)

    if not instance:
        findings.append("No instance matched %s in %s, so no credential conclusion "
                        "was drawn at all." % (args.instance_id, args.region_id))
        guidance.append("Confirm the instance id, the region and the owning account "
                        "first: a wrong region or a different account looks exactly "
                        "like a broken credential.")
        handoffs.append(handoff_for("overdue balance, a released instance, resources "
                                    "invisible in this account"))
        return findings, guidance, handoffs

    state = str(instance.get("Status") or "unknown")
    if state != "Running":
        findings.append("The instance is %s. No logon path works in that state, so "
                        "the credential symptom is downstream of it." % state)
        guidance.append("The owner brings it to Running from %s first. That is a "
                        "customer-executed change, and %s"
                        % (CONSOLE_ENTRIES["instance_list"], SNAPSHOT_FIRST_GATE))
    for lock in operation_locks(instance):
        if lock != "none":
            findings.append("The instance carries an operation lock: %s." % lock)
            findings.append("An operation lock can stop credential work outright; "
                            "clear it through account and billing support before "
                            "retrying anything in this tier.")

    health = facts["full_status"].get("HealthStatus") or {}
    health_name = str(health.get("Name") or health.get("Code") or "")
    if health_name and health_name.lower() not in ("ok", "normal", "running"):
        findings.append("Reported health status is %s, an instance-level condition "
                        "rather than a credential one." % health_name)
        handoffs.append(handoff_for("the instance will not boot, or is stuck between "
                                    "states"))

    if online:
        findings.append("Cloud Assistant reports normally (version %s, last heartbeat "
                        "%s), so the passwordless channel is healthy and the cause "
                        "sits further down the chain."
                        % (assistant.get("CloudAssistantVersion") or "not returned",
                           assistant.get("LastHeartbeatTime") or "not returned"))
    else:
        findings.append("Cloud Assistant is not reporting from this instance. Console "
                        "passwordless logon and an online password reset both depend "
                        "on it, which explains either symptom on its own.")
        findings.append(CLOUD_ASSISTANT_FACTS[0])
        guidance.append("Use a fallback that does not need the agent: %s, or a "
                        "password logon through %s."
                        % (CONSOLE_ENTRIES["vnc"],
                           CONSOLE_ENTRIES["instance_credential"]))
        guidance.append("Agent repair and a reboot are customer-executed; review "
                        "status and history at %s first, snapshot before any reboot."
                        % CONSOLE_ENTRIES["cloud_assistant"])

    for hit in hits:
        findings.append("Recognised wording in the customer's error text (%s): %s"
                        % (hit["matched"], hit["verdict"]))
        guidance.append("Action for that message: %s" % hit["action"])

    branch_handlers = {
        "passwordless-workbench": _branch_passwordless,
        "keypair-not-effective": _branch_keypair,
        "client-key-error": _branch_client,
        "credential-lost": _branch_credential_lost,
        "password-reset-failed": _branch_reset_failed,
        "windows-rdp-lockout": _branch_windows,
        "windows-multi-user": _branch_windows,
        "authorized-keys-drift": _branch_drift,
        "os-change-or-image": _branch_image,
        "passkey-third-party": _branch_passkey,
        "credential-entry-vnc": _branch_vnc_failing,
        "unknown": _branch_unknown,
    }
    branch_handlers.get(branch, _branch_unknown)(args, facts, findings, guidance,
                                                handoffs)

    if args.entry == "vnc" and branch != "credential-entry-vnc":
        guidance.append("The stated path is VNC, which ignores keys and passwords "
                        "entirely: a VNC failure is a system-level signal and should "
                        "be separated from the credential story before anything else.")

    for symptom_key, label, reference in SYMPTOM_TAXONOMY:
        if symptom_key == branch:
            guidance.append("Decision tree and wording for this symptom (%s): %s"
                            % (label, reference))
            break
    return findings, guidance, handoffs


def _branch_passwordless(args, facts, findings, guidance, handoffs):
    findings.append("Branch: %s" % CLOUD_ASSISTANT_FACTS[1])
    if agent_is_online(facts["assistant"]):
        findings.append("With the agent online, the remaining candidates are a wedged "
                        "guest, an sshd that refuses the temporary key, or a target "
                        "account that cannot be resolved inside the instance.")
        guidance.append("Ask whether a resource problem is visible at the same time "
                        "(slow commands, other services down). If yes, that is the "
                        "real problem and the logon failure is its symptom.")
        handoffs.append(handoff_for("disk IO or IOPS saturated, the system wedged, "
                                    "several symptoms at once"))
    else:
        findings.append("Branch: %s" % CLOUD_ASSISTANT_FACTS[3])


def _branch_keypair(args, facts, findings, guidance, handoffs):
    findings.append("Effect rule applied by this skill: %s" % KEY_PAIR_EFFECT_RULE)
    guidance.append("Establish whether the console restart happened; this script "
                    "cannot read it. Recorded answer: %s." % args.restart_done)
    guidance.append(NO_RESTART_ALTERNATIVE)
    guidance.append("Create or import at %s, then bind through %s. Naming rules: %s"
                    % (CONSOLE_ENTRIES["key_pair"],
                       CONSOLE_ENTRIES["instance_credential"],
                       "; ".join(KEY_PAIR_NAMING_RULES)))
    findings.append("One more check that costs nothing: %s" % CREDENTIAL_FACTS[3])
    if args.key_pair_name:
        findings.append("The key pair filter %s returned %s instance(s) in this "
                        "region and account." % (args.key_pair_name,
                                                facts["instance_count"]))


def _branch_client(args, facts, findings, guidance, handoffs):
    guidance.append("Everything in this branch runs on the customer's own workstation, "
                    "which this skill never touches. Ask them to report the identity "
                    "file the client offers and the user name, recorded here as %s."
                    % (args.username or "not stated"))
    guidance.append("A wrong user name produces the same refusal as a wrong key: the "
                    "candidates on a Linux instance are root, ecs-user and the stock "
                    "image user, so confirm it before touching any key file.")


def _branch_credential_lost(args, facts, findings, guidance, handoffs):
    for fact in CREDENTIAL_FACTS[:2]:
        findings.append(fact)
    guidance.append("Two console-side recoveries: bind a freshly created key pair at "
                    "%s, or reset the password at %s."
                    % (CONSOLE_ENTRIES["key_pair"],
                       CONSOLE_ENTRIES["instance_credential"]))
    guidance.append("While recovering access, the same review should cover exposure: "
                    "%s" % CONSOLE_ENTRIES["security_group"])


def _branch_reset_failed(args, facts, findings, guidance, handoffs):
    findings.append(CREDENTIAL_FACTS[2])
    if facts["instance"].get("KeyPairName") or args.key_pair_name:
        findings.append("A key pair binding is recorded for this instance, so a "
                        "password reset alone may leave password logon refused: %s"
                        % CREDENTIAL_FACTS[3])
    findings.append("Recent execution history for this instance: %s record(s), "
                    "latest status %s. A failure inside the guest shows up there."
                    % (facts["invocation_total"],
                       _invocation_status(facts["invocation_rows"])))
    guidance.append("Try the online reset first, it needs no restart. If it fails at "
                    "the key pair step again, the offline path requires a console "
                    "restart, so %s" % SNAPSHOT_FIRST_GATE)
    guidance.append("If any other path still reaches the guest, changing the password "
                    "from inside the system avoids the restart entirely and is the "
                    "shorter route.")


def _branch_windows(args, facts, findings, guidance, handoffs):
    for fact in WINDOWS_LOGON_FACTS:
        findings.append(fact)
    guidance.append("Releasing the lock is human-side: one successful VNC logon, or "
                    "the console send-command path at %s."
                    % CONSOLE_ENTRIES["send_command"])
    guidance.append("The usual origin is 3389 reachable from the internet. Reviewing "
                    "and narrowing it to the customer's own address is the actual fix, "
                    "and it is a network policy change the owner approves at %s."
                    % CONSOLE_ENTRIES["security_group"])
    for command, proves in guest_readings("windows")[:2]:
        findings.append("Reading that settles it, run by a human: %s shows %s"
                        % (command, proves))


def _branch_drift(args, facts, findings, guidance, handoffs):
    for fact in AUTHORIZED_KEYS_FACTS[:3]:
        findings.append(fact)
    findings.append("Audit trail first, conclusion second: %s invocation record(s) "
                    "visible to this account, latest status %s."
                    % (facts["invocation_total"],
                       _invocation_status(facts["invocation_rows"])))
    findings.append("Anything not covered by that trail happened outside the cloud "
                    "audit, so naming a cause without the file readings would be a "
                    "guess. The report stays DEGRADED for exactly that reason.")
    guidance.append("Collect the readings for the key file and its directory, plus any "
                    "automation the customer runs, then compare before concluding.")


def _branch_image(args, facts, findings, guidance, handoffs):
    findings.append(CREDENTIAL_FACTS[4])
    findings.append("After an image swap the old binding went with the previous system "
                    "disk, so a stale key pair expectation is not a platform fault.")
    guidance.append("Rebind at %s and expect the restart step, so %s"
                    % (CONSOLE_ENTRIES["instance_credential"], SNAPSHOT_FIRST_GATE))
    if args.image_origin == "community-other-linux":
        findings.append("A community image flagged as Others Linux sits outside console "
                        "credential management once it is swapped onto an existing "
                        "instance: the reset and binding controls are unavailable by "
                        "design.")
        guidance.append("That case needs an engineer to attach a repair disk and "
                        "change the credential offline, which is a human-approved "
                        "change with a reboot risk, not a retry of the console path.")
        handoffs.append(handoff_for("base files such as the default shell are missing "
                                    "and every command fails"))


def _branch_passkey(args, facts, findings, guidance, handoffs):
    findings.append("Not an ECS credential capability: a passkey needs a biometric "
                    "sensor or a platform authenticator that a cloud instance does "
                    "not have, and the target site's own rules decide acceptance.")
    guidance.append("Say what is missing and stop there; a workaround offered without "
                    "verification raises expectations the platform cannot meet.")
    handoffs.append(handoff_for("a passkey, security key, fingerprint or face logon "
                                "to a third-party website"))


def _branch_vnc_failing(args, facts, findings, guidance, handoffs):
    findings.append("VNC is reported failing too, and VNC needs neither a key nor a "
                    "password, so the problem sits below the credential layer.")
    guidance.append("Confirm the instance is Running and reachable, then treat this as "
                    "a system problem: the credential branch stays closed until the "
                    "system path works again.")
    handoffs.append(handoff_for("the instance will not boot, or is stuck between "
                                "states"))
    handoffs.append(handoff_for("disk IO or IOPS saturated, the system wedged, "
                                "several symptoms at once"))


def _branch_unknown(args, facts, findings, guidance, handoffs):
    findings.append("The symptom could not be classified from the supplied wording, so "
                    "only the standing facts above are asserted.")
    guidance.append("Collect the four intake elements before concluding: instance and "
                    "region, operating system, which logon path, and the exact error "
                    "text. See references/login-decision-tree.md.")


def _invocation_status(rows):
    if not rows:
        return "none on record"
    first = rows[0] if isinstance(rows[0], dict) else {}
    return str(first.get("InvocationStatus") or first.get("InvokeStatus") or "unknown")


def _clip(text):
    text = text or ""
    if len(text) <= GUEST_OUTPUT_MAX_CHARS:
        return text
    return text[:GUEST_OUTPUT_MAX_CHARS] + "\n  ...[truncated by this skill]"


def _inspection_shell_type(args, reported_os):
    """Pick the Cloud Assistant script type for one confirmed reading."""
    if args.inspection_shell != "auto":
        return INSPECTION_SHELL_TYPES[args.inspection_shell]
    probe = (reported_os or args.os_type or "").lower()
    for family, script_type in INSPECTION_DEFAULT_SHELL.items():
        if family in probe:
            return script_type
    return INSPECTION_SHELL_TYPES["shell"]


def _invocation_result(rows, invoke_id):
    """Take the status and output of the invocation this run dispatched."""
    row = {}
    for item in rows:
        if isinstance(item, dict) and str(item.get("InvokeId") or "") == invoke_id:
            row = item
            break
    if not row:
        for item in rows:
            if isinstance(item, dict):
                row = item
                break
    status = str(row.get("InvocationStatus") or row.get("InvokeStatus") or "")
    output = ""
    for instance_row in _unwrap(row, "InvokeInstances"):
        if not isinstance(instance_row, dict):
            continue
        status = str(instance_row.get("InvocationStatus") or status)
        output = str(instance_row.get("Output") or "")
        break
    return status, output


def run_inspection(args, reported_os, evidence):
    """Class B: dispatch ONE published reading, then read its result back.

    Refused unless the command is on the inspection list and the caller repeated
    that exact command as this run's confirmation. One command per call, so a
    second reading needs a second confirmed call.
    """
    command = args.run_inspection
    if not command:
        return {"requested": False}
    result = {"requested": True, "command": command, "ran": False,
              "outcome": "", "detail": "", "invoke_id": "",
              "invocation_status": "", "output": "", "shell_type": ""}
    if command not in EXECUTABLE_INSPECTION_COMMANDS:
        result["outcome"] = "refused"
        result["detail"] = ("not one of the published inspection readings, so it was not "
                            "dispatched; it is listed for a human to run instead")
        return result
    if args.confirm_inspection != command:
        result["outcome"] = "unconfirmed"
        result["detail"] = ("no confirmation repeating this exact command, so nothing ran "
                            "inside the guest; state what the command reads and re-run "
                            "with --confirm-inspection carrying it")
        return result
    script_type = _inspection_shell_type(args, reported_os)
    result["shell_type"] = script_type
    encoded = base64.b64encode(command.encode("utf-8")).decode("ascii")
    body = None
    try:
        body = run_cli(PRODUCT_ECS, ACTION_RUN_COMMAND, {
            "RegionId": args.region_id,
            "Type": script_type,
            "CommandContent": encoded,
            "ContentEncoding": "Base64",
            "Name": INSPECTION_COMMAND_NAME,
            "Description": "One confirmed non-mutating logon credential reading.",
            "InstanceId.1": args.instance_id,
            "Timeout": str(args.guest_wait),
        }, session_id=args.session_id, timeout=args.timeout, confirmation=encoded)
    except CliError as exc:
        evidence.add("guest-inspection", ACTION_RUN_COMMAND, "failed", exc.message,
                     exc.code)
        result["outcome"] = "failed" if exc.code != CODE_CONFIRMATION_REQUIRED \
            else "unconfirmed"
        result["detail"] = exc.message
        return result
    evidence.add("guest-inspection", ACTION_RUN_COMMAND, "ok",
                 "one confirmed reading dispatched")
    result["ran"] = True
    result["outcome"] = "dispatched"
    invoke_id = str((body or {}).get("InvokeId") or "")
    result["invoke_id"] = invoke_id or "not returned"
    return read_back(args, invoke_id, result, evidence)


def read_back(args, invoke_id, result, evidence):
    """Poll the dispatched reading until it ends or the wait budget runs out."""
    params = {"RegionId": args.region_id, "InstanceId": args.instance_id,
              "IncludeOutput": "true", "ContentEncoding": "PlainText",
              "PageSize": PAGE_SIZE}
    if invoke_id:
        params["InvokeId"] = invoke_id
    deadline = time.monotonic() + args.guest_wait
    while True:
        try:
            body = run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS, params,
                           session_id=args.session_id, timeout=args.timeout)
        except CliError as exc:
            evidence.add("guest-readback", ACTION_DESCRIBE_INVOCATIONS, "failed",
                         exc.message, exc.code)
            result["outcome"] = "unread"
            result["detail"] = ("the reading was dispatched but this skill could not read "
                                "it back: %s" % exc.message)
            return result
        rows = _unwrap(body, "Invocations")
        status, output = _invocation_result(rows, invoke_id)
        evidence.add("guest-readback", ACTION_DESCRIBE_INVOCATIONS, "ok",
                     "invocation status %s" % (status or "not returned"))
        result["invocation_status"] = status or "not returned"
        if output:
            result["output"] = _clip(mask_secrets(output))
        if status and status.lower().replace(" ", "") not in GUEST_IN_PROGRESS_STATUSES:
            result["outcome"] = "returned"
            result["detail"] = "the reading completed; the output is above"
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result["outcome"] = "still running"
            result["detail"] = ("the reading has not finished within %ss, so nothing "
                                "beyond its dispatch status is claimed"
                                % args.guest_wait)
            return result
        time.sleep(min(GUEST_POLL_INTERVAL_SECONDS, max(1, int(remaining))))


def create_prechange_snapshot(args, evidence):
    """Class C: the pre-change snapshot, on a confirmation naming that one disk."""
    disk_id = args.snapshot_disk_id
    if not disk_id:
        return {"requested": False}
    result = {"requested": True, "disk_id": disk_id, "created": False,
              "snapshot_id": "", "detail": ""}
    if not disk_id.startswith("d-"):
        result["detail"] = ("not shaped like a disk id, so no call was made; the console "
                            "path is %s" % CONSOLE_ENTRIES["snapshot"])
        return result
    if args.confirm_snapshot != disk_id:
        result["detail"] = ("no confirmation naming this disk, so no snapshot was taken; "
                            "state the billing consequence and re-run with "
                            "--confirm-snapshot carrying that disk id")
        return result
    try:
        body = run_cli(PRODUCT_ECS, ACTION_CREATE_SNAPSHOT, {
            "RegionId": args.region_id,
            "DiskId": disk_id,
            "SnapshotName": SNAPSHOT_NAME_PREFIX + args.session_id[:8],
            "Description": SNAPSHOT_DESCRIPTION,
        }, session_id=args.session_id, timeout=args.timeout, confirmation=disk_id)
    except CliError as exc:
        evidence.add("prechange-snapshot", ACTION_CREATE_SNAPSHOT, "failed",
                     exc.message, exc.code)
        result["detail"] = exc.message
        return result
    evidence.add("prechange-snapshot", ACTION_CREATE_SNAPSHOT, "ok",
                 "snapshot requested for %s" % disk_id)
    result["created"] = True
    result["snapshot_id"] = str((body or {}).get("SnapshotId") or "not returned")
    result["detail"] = ("billable storage: note the id and delete it when the change "
                        "window closes")
    return result


def guest_channel_note(inspection, snapshot):
    """One line saying what actually ran, so no reader has to infer it."""
    parts = []
    if inspection.get("requested"):
        parts.append("guest reading: %s" % (inspection.get("outcome") or "not stated"))
    else:
        parts.append("no guest reading was requested, so nothing was dispatched")
    if snapshot.get("requested"):
        parts.append("pre-change snapshot: %s"
                     % ("created" if snapshot.get("created") else "not taken"))
    else:
        parts.append("no snapshot was requested")
    return "; ".join(parts)


def never_granted_note():
    """The D-class boundary, printed so no reader has to infer it from silence."""
    return ("Never issued from here, only explained as a console path: %s. A request "
            "for one of them is a hand-off to a human with the evidence above, not a "
            "parameter to guess." % ", ".join(NEVER_GRANTED_ACTION_NAMES))


def permission_gap_lines(evidence):
    """Name the exact action that was refused, plus the minimal policy pointer."""
    lines = []
    for action in sorted(set(evidence.denied)):
        ram_action = RAM_ACTION_BY_NAME.get(action, "sts:GetCallerIdentity")
        lines.append("%s was refused. Grant that single action to the identity in use; "
                     "the exact statement is in references/ram-policies.md. No "
                     "wildcard policy is needed or offered." % ram_action)
    return lines


def limitations(args, facts, evidence):
    notes = [
        "Facts that exist only inside the guest, namely the public key actually "
        "present, its file permissions and the live sshd options, are invisible to "
        "the evidence queries: one confirmed reading, or a human running the "
        "published list, is the only way to get them.",
        "Security group rule content is not read here: only the bound group "
        "identifiers come back, so reachability of 22 or 3389 is something the "
        "customer tests from their own network.",
        "Whether a console restart followed a binding cannot be queried; it is asked, "
        "and an unanswered question keeps the report DEGRADED.",
        "No monitoring metric is read, so a wedged guest is offered as a candidate "
        "branch and handed to the IO tier, never asserted as the cause.",
        "A snapshot request carries the disk id the operator supplied: this build "
        "cannot list disks, because no disk inventory action is whitelisted.",
        "Key pair inventory, binding changes and password resets are console-side "
        "guidance in this build: their actions have no verified parameter or policy "
        "contract for this tier, so nothing is called on the customer's behalf.",
    ]
    for step in evidence.failed_steps:
        notes.append("Evidence step %s returned nothing, so every conclusion that "
                     "depends on it is marked unproven rather than assumed." % step)
    return notes


def build_report(args, facts, hits, branch, findings, guidance, handoffs, evidence,
                 status, inspection, snapshot):
    """Assemble the report body as a dict, then render it."""
    instance = facts["instance"]
    assistant = facts["assistant"]
    return {
        "skill": SKILL_NAME,
        "session_id": args.session_id,
        "identity": args.identity_tag,
        "inputs": args.declared_inputs,
        "instance": {
            "instance_id": instance.get("InstanceId") or args.instance_id,
            "region_id": args.region_id,
            "status": instance.get("Status") or "unknown",
            "os_type": instance.get("OSType") or args.os_type or "unknown",
            "os_name": instance.get("OSName") or "unknown",
            "image_id": instance.get("ImageId") or "unknown",
            "key_pair_name": (instance.get("KeyPairName") or args.key_pair_name
                              or "not returned by this query"),
            "private_ip": private_address(instance),
            "public_ip": public_address(instance),
            "operation_locks": operation_locks(instance),
            "expired_time": instance.get("ExpiredTime") or "not applicable",
        },
        "cloud_assistant": {
            "status": assistant.get("CloudAssistantStatus") or "not returned",
            "version": assistant.get("CloudAssistantVersion") or "not returned",
            "last_heartbeat": assistant.get("LastHeartbeatTime") or "not returned",
            "last_invoked": assistant.get("LastInvokedTime") or "not returned",
        },
        "branch": branch,
        "error_signatures": hits,
        "evidence": evidence.rows,
        "findings": findings,
        "manual_guidance": guidance,
        "handoff": handoffs,
        "permission_gaps": permission_gap_lines(evidence),
        "channel_state": guest_channel_note(inspection, snapshot),
        "inspection": inspection,
        "snapshot": snapshot,
        "guest_readings": [{"command": command, "proves": proves}
                           for command, proves in guest_readings(
                               instance.get("OSType") or args.os_type)],
        "guest_reading_rules": list(GUEST_READING_RULES),
        "risk_notes": [SNAPSHOT_FIRST_GATE, never_granted_note()]
                      + list(SNAPSHOT_RISK_NOTES),
        "limitations": limitations(args, facts, evidence),
        "documentation": [{"title": title, "url": url} for title, url in OFFICIAL_DOCS],
        "unverified_links": [{"note": TICKET_QUOTED_LINKS_NOTE,
                             "items": [{"title": t, "url": u}
                                       for t, u in TICKET_QUOTED_LINKS]}],
        "status": status,
        "next_action": "",
    }


GATED_UNFINISHED_OUTCOMES = ("unconfirmed", "refused", "failed", "unread", "still running")


def gated_pending_note(inspection, snapshot):
    """Turn an unfinished class B or class C call into one concrete next step."""
    outcome = inspection.get("outcome") or ""
    if inspection.get("requested") and outcome in GATED_UNFINISHED_OUTCOMES:
        if outcome == "unconfirmed":
            return ("Announce what %s reads and that it changes nothing, then re-run "
                    "with --confirm-inspection carrying that exact command; until then "
                    "treat it as a step for a human."
                    % inspection.get("command"))
        if outcome == "refused":
            return ("Keep %s out of the executed set: it is not a published reading, so "
                    "print it for a human and stay on the evidence already collected."
                    % inspection.get("command"))
        return ("Report the %s outcome for %s as the finding it is, then either re-run "
                "the reading or hand the guest inspection to a human; never claim a "
                "reading that did not come back."
                % (outcome, inspection.get("command")))
    if snapshot.get("requested") and not snapshot.get("created"):
        return ("State the billing consequence for disk %s, then re-run with "
                "--confirm-snapshot carrying that disk id, or have a human take the "
                "snapshot in the console before any restart-dependent step."
                % snapshot.get("disk_id"))
    return ""


def next_action(payload):
    if payload["permission_gaps"]:
        return ("Attach the refused Describe action named in PERMISSION GAPS using the "
                "statement in references/ram-policies.md, then re-run this script; do "
                "not widen it to a product-wide policy.")
    if payload["status"] == STATUS_FAIL:
        return ("Re-check the instance id, the region and the owning account, fix the "
                "reported credential problem, then re-run this script before any "
                "credential conclusion.")
    if payload["evidence"] and any(row["status"] != "ok" for row in payload["evidence"]):
        return ("Re-run the failed evidence step, and until it returns treat any "
                "conclusion that depends on it as unproven.")
    pending = gated_pending_note(payload["inspection"], payload["snapshot"])
    if pending:
        return pending
    if payload["handoff"]:
        return ("Hand the case over to the target named in HANDOFF with this evidence "
                "list attached, and keep the credential branch closed until they "
                "report back.")
    return ("Send the customer the numbered MANUAL GUIDANCE steps, ask the single "
            "question the branch still depends on, and re-run this script once they "
            "have acted.")


def render_text(payload):
    out = []
    out.append("=== ECS LOGON CREDENTIAL DIAGNOSIS =================================")
    out.append("skill       : %s" % payload["skill"])
    out.append("session id  : %s" % payload["session_id"])
    out.append("identity    : %s" % payload["identity"])
    out.append("target      : %s in %s" % (payload["instance"]["instance_id"],
                                           payload["instance"]["region_id"]))
    out.append("")
    out.append("DECLARED INPUTS")
    for name in sorted(payload["inputs"]):
        out.append("  %-19s %s" % (name + ":", payload["inputs"][name]))
    out.append("")
    out.append("INSTANCE FACTS")
    for key in ("status", "os_type", "os_name", "image_id", "key_pair_name",
                "private_ip", "public_ip", "operation_locks", "expired_time"):
        out.append("  %-15s %s" % (key + ":", payload["instance"][key]))
    out.append("")
    out.append("CLOUD ASSISTANT CHANNEL")
    for key in sorted(payload["cloud_assistant"]):
        out.append("  %-15s %s" % (key + ":", payload["cloud_assistant"][key]))
    out.append("")
    out.append("EVIDENCE COLLECTED")
    out.extend(_evidence_lines(payload["evidence"]))
    if payload["permission_gaps"]:
        out.append("")
        out.append("PERMISSION GAPS")
        for line in payload["permission_gaps"]:
            out.append("  - %s" % line)
    out.append("")
    out.append("BRANCH: %s" % payload["branch"])
    out.append("")
    out.append("FINDINGS")
    for index, item in enumerate(payload["findings"], start=1):
        out.append("  %d. %s" % (index, item))
    out.append("")
    out.append("MANUAL GUIDANCE")
    for index, item in enumerate(payload["manual_guidance"], start=1):
        out.append("  %d. %s" % (index, item))
    out.append("")
    out.append("RISK NOTES")
    for index, item in enumerate(payload["risk_notes"], start=1):
        out.append("  %d. %s" % (index, item))
    if payload["handoff"]:
        out.append("")
        out.append("HANDOFF")
        for item in payload["handoff"]:
            out.append("  - when: %s" % item["trigger"])
            out.append("    why : %s" % item["boundary"])
            out.append("    to  : %s" % item["target"])
    out.append("")
    out.append("GUEST INSPECTION (class B, needs a per-command confirmation)")
    inspection = payload["inspection"]
    if not inspection.get("requested"):
        out.append("  - nothing requested on this run, so nothing was dispatched")
    else:
        out.append("  - command      : %s" % inspection.get("command"))
        out.append("  - outcome      : %s" % inspection.get("outcome"))
        out.append("  - dispatched   : %s" % ("yes" if inspection.get("ran") else "no"))
        if inspection.get("shell_type"):
            out.append("  - script type: %s" % inspection["shell_type"])
        if inspection.get("invoke_id"):
            out.append("  - invoke id  : %s" % inspection["invoke_id"])
        if inspection.get("invocation_status"):
            out.append("  - invocation : %s" % inspection["invocation_status"])
        out.append("  - note         : %s" % inspection.get("detail"))
        if inspection.get("output"):
            out.append("  - output (credential-scrubbed):")
            for line in inspection["output"].splitlines():
                out.append("      %s" % line)
    out.append("")
    out.append("PRE-CHANGE SNAPSHOT (class C, needs a confirmation naming the disk)")
    snapshot = payload["snapshot"]
    if not snapshot.get("requested"):
        out.append("  - nothing requested on this run; the snapshot gate below still applies")
    else:
        out.append("  - disk    : %s" % snapshot.get("disk_id"))
        out.append("  - created : %s" % ("yes" if snapshot.get("created") else "no"))
        if snapshot.get("snapshot_id"):
            out.append("  - id      : %s" % snapshot["snapshot_id"])
        out.append("  - note    : %s" % snapshot.get("detail"))
    out.append("")
    out.append("CHANNEL STATE ON THIS RUN")
    out.append("  %s" % payload["channel_state"])
    out.append("")
    out.append("PUBLISHED IN-GUEST READINGS")
    for row in payload["guest_readings"]:
        out.append("  - %s" % row["command"])
        out.append("      proves: %s" % row["proves"])
    for rule in payload["guest_reading_rules"]:
        out.append("  * %s" % rule)
    out.append("")
    out.append("LIMITATIONS")
    for index, item in enumerate(payload["limitations"], start=1):
        out.append("  %d. %s" % (index, item))
    out.append("")
    out.append("DOCUMENTATION")
    for row in payload["documentation"]:
        out.append("  - %s: %s" % (row["title"], row["url"]))
    for block in payload["unverified_links"]:
        out.append("  %s" % block["note"])
        for row in block["items"]:
            out.append("  - %s: %s" % (row["title"], row["url"]))
    out.append("")
    out.append("STATUS: %s" % payload["status"])
    out.append("NEXT_ACTION: %s" % payload["next_action"])
    return "\n".join(out)


def _evidence_lines(rows):
    lines = []
    for row in rows:
        lines.append("  %-5s %-20s %-32s %s"
                     % (row["status"].upper()[:4], row["step"], row["action"],
                        row["detail"] or "-"))
    return lines


def declared_inputs(args):
    """Every input, and whether the caller supplied it or a default filled it."""
    return {
        "instance_id": args.instance_id,
        "region_id": "%s (supplied)" % args.region_id,
        "symptom": args.symptom + ("" if args.symptom != "unknown"
                                   else " (default: classify from the evidence)"),
        "entry": "%s (%s)" % (args.entry, ENTRY_DESCRIPTIONS[args.entry]),
        "error_text": (mask_secrets(args.error_text)[:120]
                       or "not supplied, so signature matching was skipped"),
        "username": args.username or "not supplied",
        "os_type": args.os_type or "taken from DescribeInstances when it returns",
        "key_pair_name": args.key_pair_name or "not supplied",
        "restart_done": "%s (asked, never queried)" % args.restart_done,
        "image_origin": args.image_origin,
        "vnc_works": args.vnc_works,
        "note": (mask_secrets(args.note)[:80] or "not supplied"),
        "timeout_seconds": str(args.timeout or "30 (built-in default)"),
        "output_format": args.output_format,
        "guest_inspection": (args.run_inspection
                             or "not requested, so the reading list is guidance only"),
        "guest_inspection_confirmed": (
            "yes, for that same command"
            if args.run_inspection and args.confirm_inspection == args.run_inspection
            else ("no, so nothing was dispatched inside the guest"
                  if args.run_inspection else "not applicable")),
        "inspection_shell": ("%s (chosen from the reported operating system)"
                             if args.inspection_shell == "auto" else args.inspection_shell),
        "guest_wait_seconds": str(args.guest_wait),
        "snapshot_disk_id": args.snapshot_disk_id or "not requested",
        "snapshot_confirmed": (
            "yes, for that same disk"
            if args.snapshot_disk_id and args.confirm_snapshot == args.snapshot_disk_id
            else ("no, so no snapshot was taken"
                  if args.snapshot_disk_id else "not applicable")),
        "granted_actions_considered": ", ".join(RAM_POLICY_ACTIONS),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="keypair_login_diagnosis.py",
        description=("Collect logon-credential evidence for one ECS instance and "
                     "report the findings with manual guidance. Evidence queries run "
                     "on their own; the two state-changing calls are opt-in and each "
                     "needs a confirmation naming its exact target on the same run."),
    )
    parser.add_argument("--instance-id", required=True,
                        help="target instance id, for example i-2ze8exampleinstance")
    parser.add_argument("--region-id", "--region", dest="region_id", required=True,
                        help="region id of that instance, for example cn-hangzhou")
    parser.add_argument("--symptom", default="unknown",
                        choices=[key for key, _, _ in SYMPTOM_TAXONOMY],
                        help="symptom class taken from the customer wording")
    parser.add_argument("--entry", default="unknown", choices=list(CONNECTION_ENTRIES),
                        help="which logon path was attempted")
    parser.add_argument("--error-text", default="", dest="error_text",
                        help="the exact error text the customer sees, verbatim")
    parser.add_argument("--username", default="",
                        help="log-on user name used, for example root or ecs-user")
    parser.add_argument("--os-type", default="", choices=["", "linux", "windows"],
                        help="override the operating system reported by the API")
    parser.add_argument("--key-pair-name", default="", dest="key_pair_name",
                        help="filter the instance list by this key pair name")
    parser.add_argument("--restart-done", default="unknown", dest="restart_done",
                        choices=["yes", "no", "unknown"],
                        help="whether a console restart followed the binding")
    parser.add_argument("--image-origin", default="unknown", dest="image_origin",
                        choices=["public", "marketplace", "community-other-linux",
                                 "custom", "unknown"],
                        help="where the current image came from")
    parser.add_argument("--vnc-works", default="unknown", dest="vnc_works",
                        choices=["yes", "no", "unknown"],
                        help="whether VNC logon succeeds, which splits the layers")
    parser.add_argument("--note", default="",
                        help="one line of customer wording, used for routing only")
    parser.add_argument("--run-inspection", default="", dest="run_inspection",
                        help=("one published inspection reading to dispatch inside the "
                              "guest; anything outside that list is refused and printed "
                              "as guidance instead"))
    parser.add_argument("--confirm-inspection", default="", dest="confirm_inspection",
                        help=("repeat the --run-inspection command verbatim to approve "
                              "that one dispatch; it never covers a second command"))
    parser.add_argument("--inspection-shell", default="auto", dest="inspection_shell",
                        choices=["auto", "shell", "bat", "powershell"],
                        help=("Cloud Assistant script type for the reading; auto takes it "
                              "from the reported operating system"))
    parser.add_argument("--guest-wait", type=int, default=GUEST_WAIT_DEFAULT_SECONDS,
                        dest="guest_wait",
                        help=("seconds to wait for the dispatched reading to finish, "
                              "capped by this skill"))
    parser.add_argument("--snapshot-disk-id", default="", dest="snapshot_disk_id",
                        help=("disk id, for example d-2ze8exampledisk, to snapshot before "
                              "a restart-dependent step"))
    parser.add_argument("--confirm-snapshot", default="", dest="confirm_snapshot",
                        help=("repeat --snapshot-disk-id verbatim to approve that one "
                              "billable snapshot"))
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the per-call timeout in seconds")
    parser.add_argument("--output", dest="output_format", default="text",
                        choices=["text", "json"], help="report format")
    args = parser.parse_args(argv)
    args.guest_wait = min(max(args.guest_wait, GUEST_POLL_INTERVAL_SECONDS),
                          GUEST_WAIT_MAX_SECONDS)
    return args


def resolve_identity(args, evidence):
    """Ask the cloud who is calling: half of these tickets are the wrong account."""
    try:
        from sts_token import derive_uid_tag, get_caller_identity
        body = get_caller_identity(session_id=args.session_id, timeout=args.timeout)
        tag = derive_uid_tag(body)
        evidence.add("caller-identity", "GetCallerIdentity", "ok", tag)
        return tag
    except CliError as exc:
        evidence.add("caller-identity", "GetCallerIdentity", "failed", exc.message,
                     exc.code)
        if exc.code in FATAL_CLI_CODES:
            evidence.fatal = exc
        return "unknown (%s)" % exc.code


def decide_status(evidence, facts, branch, inspection, snapshot):
    if evidence.fatal is not None or not facts["instance"]:
        return STATUS_FAIL
    if evidence.failed_steps:
        return STATUS_DEGRADED
    if gated_pending_note(inspection, snapshot):
        return STATUS_DEGRADED
    if branch in ("authorized-keys-drift", "unknown"):
        return STATUS_DEGRADED
    return STATUS_OK


def gated_findings(inspection, snapshot):
    """What the gated calls proved on this run, in the report's own words."""
    notes = []
    if inspection.get("requested"):
        if inspection.get("output"):
            notes.append("The confirmed guest reading %s completed; its output is in the "
                         "GUEST INSPECTION section and is the only in-guest fact this run "
                         "holds." % inspection.get("command"))
        else:
            notes.append("No in-guest fact was obtained: the requested reading %s ended "
                         "%s, so every in-guest conclusion below stays unproven."
                         % (inspection.get("command"),
                            inspection.get("outcome") or "not stated"))
    if snapshot.get("requested"):
        notes.append("Pre-change snapshot of %s: %s"
                     % (snapshot.get("disk_id"),
                        ("created as %s, so a restart-dependent step may follow"
                         % snapshot.get("snapshot_id"))
                        if snapshot.get("created")
                        else ("not taken (%s)" % snapshot.get("detail"))))
    return notes


def _run_selftest():
    """Offline regression locks for the pure login-triage cores: address and
    lock extraction from DescribeInstances (the nested {group:{IpAddress:[]}} /
    {LockReason:[...]} shapes) and the wording->branch router. A wrong branch or
    a dropped address sends the customer to the wrong fix, so behaviour is pinned
    here with no cloud call. Expected values were read off the live functions.
    Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    def args(**kw):
        base = dict(symptom="", error_text="", note="", entry="")
        base.update(kw)
        return argparse.Namespace(**base)

    # address extraction: prefer the nested group, fall back across EIP / inner.
    inst = {"PublicIpAddress": {"IpAddress": ["47.1.1.1"]},
            "EipAddress": {"IpAddress": ""},
            "VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["172.16.0.9"]}},
            "InnerIpAddress": {"IpAddress": []}}
    expect("public_address: nested PublicIpAddress.IpAddress wins",
           public_address(inst) == "47.1.1.1")
    expect("public_address: falls back to EipAddress when public list empty",
           public_address({"PublicIpAddress": {"IpAddress": []},
                           "EipAddress": {"IpAddress": "8.8.8.8"}}) == "8.8.8.8")
    expect("private_address: VPC nested, else inner fallback",
           private_address(inst) == "172.16.0.9"
           and private_address({"VpcAttributes": {}, "InnerIpAddress": {"IpAddress": ["10.0.0.2"]}}) == "10.0.0.2")
    expect("address markers: absent -> 'none recorded'",
           public_address({}) == "none recorded" and private_address({}) == "none recorded")

    # operation locks: list of reason strings, a bare string, and the none marker.
    expect("operation_locks: reason list, single string, and empty -> ['none']",
           operation_locks({"OperationLocks": {"LockReason": ["security", "financial"]}}) == ["security", "financial"]
           and operation_locks({"OperationLocks": "security"}) == ["security"]
           and operation_locks({"OperationLocks": {"LockReason": []}}) == ["none"]
           and operation_locks({}) == ["none"])

    # signature matching drives classify: a known token maps to its verdict,
    # unrelated or empty wording returns no hits (caller then asks).
    expect("match_signatures: known publickey-rejection wording produces a verdict",
           any(h["matched"] == "permission denied (publickey)" and h["verdict"]
               for h in match_signatures("Permission denied (publickey)")))
    expect("match_signatures: unrelated and empty -> []",
           match_signatures("totally unrelated hello") == [] and match_signatures("") == [])

    # classify priority: explicit symptom > synonym phrase > signature side > entry.
    expect("classify: explicit symptom short-circuits",
           classify(args(symptom="keypair-not-effective"), []) == "keypair-not-effective")
    expect("classify: synonym wording routes to its symptom",
           classify(args(error_text="authorized_keys mismatch"), []) == "authorized-keys-drift")
    expect("classify: signature fix_side maps to the right branch",
           classify(args(error_text="x"), [{"fix_side": "customer-local"}]) == "client-key-error"
           and classify(args(error_text="x"), [{"fix_side": "guest-and-console"}]) == "windows-rdp-lockout")
    expect("classify: entry choice is the last deterministic router",
           classify(args(entry="rdp"), []) == "windows-multi-user"
           and classify(args(entry="workbench-key"), []) == "keypair-not-effective")
    expect("classify: nothing matched -> unknown (never guesses a branch)",
           classify(args(), []) == "unknown")
    return rc


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    args = parse_args(argv)
    args.session_id = new_session_id()
    args.declared_inputs = declared_inputs(args)
    evidence = Evidence()
    args.identity_tag = resolve_identity(args, evidence)

    facts = collect(args, args.session_id, evidence)
    hits = match_signatures(args.error_text)
    if args.vnc_works == "no":
        branch = "credential-entry-vnc"
    else:
        branch = classify(args, hits)
    findings, guidance, handoffs = analyse(args, facts, hits, branch)

    inspection = run_inspection(args, (facts["instance"] or {}).get("OSType"), evidence)
    snapshot = create_prechange_snapshot(args, evidence)
    findings.extend(gated_findings(inspection, snapshot))
    status = decide_status(evidence, facts, branch, inspection, snapshot)

    payload = build_report(args, facts, hits, branch, findings, guidance, handoffs,
                           evidence, status, inspection, snapshot)
    payload["next_action"] = next_action(payload)
    if args.output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload))
    if status == STATUS_OK:
        return 0
    return 1 if status == STATUS_DEGRADED else 2


if __name__ == "__main__":
    sys.exit(main())
