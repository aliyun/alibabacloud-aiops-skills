#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-execution guardrails shared by this package's entry dispatcher.

Two boundaries are enforced here, before any axis code runs and again on the
child's own output:

1. In-guest reads are OFF by default. Anything delivered through Cloud
   Assistant `RunCommand` executes inside the customer's machine, so it needs a
   consent the customer gave in this turn. The only accepted proof is the
   caller passing `--allow-guest-read` (or `ECS_GUEST_CONSENT=1`); without it the
   axis's guest-activation flags are stripped and a `CONSENT-REQUIRED:` notice is
   printed. The cloud-side reads still run, so a forgotten flag degrades the
   answer instead of blocking it.

2. Credential failure is fail-closed. When the transport reports a
   credential-class error the run stops with `CREDENTIAL-FAIL-CLOSED:` plus the
   checks the customer can run themselves, and exits 3. Nothing in this package
   reads `~/.aliyun/config.json` or the `ALIBABACLOUD_*` environment variables;
   `credential_probe_tokens()` refuses to spawn a command that would.

Pure functions here are covered by tools/test_guardrails.py.
"""

import os
import re
import subprocess
import sys
import threading

CONSENT_FLAG = "--allow-guest-read"
CONSENT_ENV = "ECS_GUEST_CONSENT"
BOUNDARY_ENV = "ECS_CREDENTIAL_BOUNDARY"
EXIT_CREDENTIAL_UNAVAILABLE = 3
EXIT_PROBE_REFUSED = 126

# Error strings the CLI/SDK emit when the default credential chain itself is
# unusable. NoPermission / ImplicitDeny are deliberately absent: those mean the
# identity is fine and the policy is short, which is a different answer.
# API error codes that prove the credential chain itself is unusable. A code only
# counts inside an error sentence: these skills also *print* the same names in
# advisory text ("identity check failed (NoPermission / InvalidAccessKeyId / ...)")
# and in "no credential conclusion was drawn" summaries, so a bare substring match
# would stop healthy runs.
CREDENTIAL_ERROR_CODES = (
    "invalidaccesskeyid",
    "signaturedoesnotmatch",
    "invalidsecuritytoken",
    "securitytokenexpired",
    "invalidcredential",
)
CREDENTIAL_ERROR_CONTEXT = re.compile(
    r"(?i)(error|exception|failed|failure|denied|invalid|expired|notfound|"
    r"unable|cannot|could not|not found)")

# Prose-only failures (no API code) specific enough not to fire on guidance text.
CREDENTIAL_PROSE_MARKERS = (
    "unable to locate credentials",
    "could not be found in the credentials file",
    "the specified profile does not exist",
    "unknown profile",
    "default profile was not found",
    "no credential configured",
    "credential is not configured",
    "no credentials configured",
    "missing credentials",
)

# Tokens that mean "read the customer's stored credentials". A command carrying
# any of them is refused before spawn. The skills resolve credentials through the
# CLI's own chain; reading the files is never necessary and always a leak risk.
_PROBE_TOKENS = (
    ".aliyun/config.json",
    "aliyun/config.json",
    "~/.aliyun",
    "/.aliyun/",
    "ALIBABACLOUD_ACCESS_KEY_ID",
    "ALIBABACLOUD_ACCESS_KEY_SECRET",
    "ALIBABACLOUD_SECURITY_TOKEN",
    "ALIBABACLOUD_SESSION_TOKEN",
    "ALICLOUD_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEY",
)

# ---------------------------------------------------- delivered-output masking
# Everything the tools print is copied into a customer-facing answer, so raw
# account UIDs, Cloud Assistant InvokeIds and session ids must never leave the
# process. 2026-10-26 measurement (15 live runs): 9/15 answers carried the raw
# 16-digit UID, 1/15 an InvokeId, 1/15 a 32-hex session id. Masking at this
# boundary is the single choke point every package shares.
_UID_RE = re.compile(r'(?<!\d)(1\d{15})(?!\d)')
_INVOKE_RE = re.compile(r'\bt-([a-z0-9]{6,})\b')
_SESSION_RE = re.compile(r'\b([0-9a-f]{32})\b')


def sanitize_identifiers(text):
    """Mask UID / InvokeId / session id in tool output; keep the last 4 chars.

    Idempotent: an already-masked value (`****6705`) has no 16-digit run left,
    so re-applying is a no-op. Non-identifiers (12- or 17-digit numbers, short
    run ids) are untouched.
    """
    if not text:
        return text
    text = _UID_RE.sub(lambda m: '****' + m.group(1)[-4:], text)
    text = _INVOKE_RE.sub(lambda m: 't-****' + m.group(1)[-4:], text)
    text = _SESSION_RE.sub(lambda m: '****' + m.group(1)[-4:], text)
    return text


# --------------------------------------------------- customer-facing answer view
# 2026-10-27 measurement (P-01b / Q-02c, post-P0 reruns): identifiers were masked
# but the delivered answers still opened with the tool's own log preamble and carried
# `Executed checks` tables quoting `scripts/axes/...`, `STATUS: DEGRADED` and
# `[EVIDENCE]`. Those are the tool's own plumbing, not the customer's report, so
# stdout is now composed as an answer block: verdict line first, then only the
# readable facts. Everything else stays in the internal log.
_DROP_LINE_RES = (
    re.compile(r'^\s*==.*==\s*$'),
    re.compile(r'^\s*(?:MUST-LEAD|RULE-LEAD|WITHHELD-LEAD|REPORT-LEAD|VERDICT-JSON)\b'),
    re.compile(r'^\s*skill\s+\S+\s*\|'),          # "skill <slug> | intent ..." banner
    re.compile(r'^\s*\[_cli\]'),                        # per-run session-id echo
    re.compile(r'^\s*SESSION[-_ ]?ID\b', re.I),
    re.compile(r'^\s*"?session_id"?\s*[:=]', re.I),
    re.compile(r'^\s+(?:StatusCode|Code|Message|Detail|Data|Recommend|RequestId|HostId)\s*:'),
    re.compile(r'^\s+Data\s*$'),
)
_SCRIPT_PATH_RE = re.compile(r'(?:\.?/)?scripts/[A-Za-z0-9_./-]+(?:\.py)?')
_CUSTOMER_LABELS = (
    ('[EVIDENCE]', 'Evidence:'),
    ('[FINDING]', 'Finding:'),
    ('[RISK]', 'Risk:'),
    ('[HUMAN STEP]', 'Customer step:'),
    ('[HANDOFF]', 'Handoff:'),
    ('[WARN]', 'Not read:'),
)

_CUSTOMER_WORDS = {
    'INSUFFICIENT-EVIDENCE': 'not enough evidence yet',
    'UNCONFIRMED': 'not confirmed',
    'Inconclusive': 'not conclusive from these reads',
    'AUTO-DEFAULT': 'inferred',
    'acs_ecs_dashboard': 'ECS basic monitoring',
    'CPUUtilization': 'CPU utilization',
}
_CUSTOMER_WORD_RE = re.compile(
    r'\b(?:%s)\b' % '|'.join(sorted(_CUSTOMER_WORDS, key=len, reverse=True)))
_CLI_FAIL_CMD_RE = re.compile(
    r'\baliyun\s+[a-z0-9-]+\s+[A-Za-z][A-Za-z0-9-]*\s+failed\s*:')
_SDK_TAIL_RE = re.compile(
    r'\s*(?:Error:\s*)?(?:request execution failed:\s*)+.*?SDKError\s*:?\s*$')
_REQUEST_ID_RE = re.compile(r'\s*request id:\s*[0-9A-Za-z-]{8,}', re.I)


def customer_line(line):
    """One report line as the customer may see it (no internal markers/paths)."""
    text = sanitize_identifiers(line.rstrip())
    text = _SCRIPT_PATH_RE.sub('the skill entry point', text)
    for marker, label in _CUSTOMER_LABELS:
        text = text.replace(marker, label)
    text = _CLI_FAIL_CMD_RE.sub('the read failed:', text)
    text = _SDK_TAIL_RE.sub('', text)
    text = _REQUEST_ID_RE.sub('', text)
    text = _CUSTOMER_WORD_RE.sub(lambda m: _CUSTOMER_WORDS[m.group(0)], text)
    return text


_STATUS_RE = re.compile(r'^\s*STATUS\s*:')
_NEXT_RE = re.compile(r'^\s*NEXT_ACTION\s*:\s*')


def customer_view(lines, lead=None, machine_status=True):
    """Compose the answer block: verdict first, then the readable facts.

    Returns a string ending in a newline. Blank runs collapse to one blank line so
    the block stays scannable after the internal section banners are dropped.

    `machine_status=False` also removes the agent-facing contract lines from the
    answer: `STATUS:` and `NEXT_ACTION:` are dropped (their content is already in
    the facts / in SKILL.md). Measured 2026-10-27: with the tokens present, legs
    pasted `STATUS: DEGRADED` into the customer answer as if it were a diagnosis
    result. Both stay on stderr for the agent. Packages whose own evals assert
    `STATUS/NEXT_ACTION` keep the default.
    """
    body = []
    for raw in lines or []:
        raw = (raw or '').rstrip()
        if not raw.strip():
            if body and body[-1] != '':
                body.append('')
            continue
        if any(r.search(raw) for r in _DROP_LINE_RES):
            continue
        if not machine_status and (_STATUS_RE.search(raw) or _NEXT_RE.search(raw)):
            continue
        body.append(customer_line(raw))
    while body and body[-1] == '':
        body.pop()
    out = []
    if lead:
        out.append(sanitize_identifiers(lead))
        if body:
            out.append('')
    out.extend(body)
    if not out:
        return ''
    return '\n'.join(out) + '\n'


CUSTOMER_CREDENTIAL_STEPS = (
    "Customer-executable checks (run these in your own shell; never paste a "
    "secret into the chat):",
    "  1) aliyun sts get-caller-identity     # must print your AccountId",
    "  2) aliyun configure list            # which profile is in use, and its source",
    "  3) role-based login: the role must allow sts:AssumeRole for this identity",
    "  4) SSO: re-run your company login helper, then repeat step 1",
    "  5) aliyun version                   # CLI must be recent enough for plugin mode",
)


def parse_consent(argv, granted=False, environ=None):
    """Return (argv_without_the_flag, effective_consent).

    Consent is granted by the explicit flag, `--allow-guest-read=1`, or the
    environment value `ECS_GUEST_CONSENT=1` set by a supervising caller. The env
    path exists so the dispatcher can propagate one decision to every child
    without re-plumbing argv.
    """
    ev = os.environ if environ is None else environ
    out = []
    for tok in argv or []:
        if tok == CONSENT_FLAG:
            granted = True
        elif tok == CONSENT_FLAG + "=1":
            granted = True
        elif tok == CONSENT_FLAG + "=0":
            granted = False
        else:
            out.append(tok)
    if str(ev.get(CONSENT_ENV, "")).strip().lower() in ("1", "true", "yes", "on"):
        granted = True
    return out, bool(granted)


def gate_guest_flags(argv, activation, granted):
    """Strip guest-activation flags unless the customer consented.

    `activation` is the flag names that make this axis deliver a command into the
    instance. A stripped flag takes its value with it (space-separated form), so
    `--guest-command 'df -h'` cannot leave a dangling `df -h` behind.
    Returns (kept_argv, dropped_flag_names).
    """
    if granted or not activation:
        return list(argv or []), []
    if isinstance(activation, str):
        activation = (activation,)
    activation = set(activation)
    kept, dropped = [], []
    i = 0
    argv = list(argv or [])
    while i < len(argv):
        tok = argv[i]
        name = tok.split("=", 1)[0]
        if name in activation:
            dropped.append(name)
            if "=" not in tok and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
            i += 1
            continue
        kept.append(tok)
        i += 1
    return kept, dropped


def consent_notice(axis, dropped):
    return "\n".join((
        "CONSENT-REQUIRED: in-guest (Cloud Assistant) reads are OFF by default.",
        "  axis          : %s" % axis,
        "  refused flags : %s" % " ".join(dropped),
        "  Nothing was delivered into the instance. Tell the customer which exact",
        "  read-only command you want to run there and why, then re-run with",
        "  %s plus the axis's own confirmation token. Cloud-side" % CONSENT_FLAG,
        "  (Describe/Get) evidence below was still collected and is unaffected.",
    ))


def consent_env(granted, base=None):
    env = dict(os.environ if base is None else base)
    env[CONSENT_ENV] = "1" if granted else "0"
    env[BOUNDARY_ENV] = "1"
    return env


def is_credential_error(text):
    """True when one output line proves the credential chain is unusable.

    Deliberately narrower than "mentions a credential": the suite's own reports
    enumerate InvalidAccessKeyId in next-action text and say things like "no
    credential conclusion was drawn at all", and matching those would fail a run
    that merely found its target missing.
    """
    line = text or ""
    low = line.lower()
    if any(marker in low for marker in CREDENTIAL_PROSE_MARKERS):
        return True
    if any(code in low for code in CREDENTIAL_ERROR_CODES):
        return bool(CREDENTIAL_ERROR_CONTEXT.search(line))
    return False


def credential_error_line(lines):
    """First child line that proves the credential chain is unusable, or None."""
    for line in lines or []:
        if is_credential_error(line):
            return line.strip()[:400]
    return None


def credential_fail_closed(hit, axis=None, exit_code=None):
    head = "CREDENTIAL-FAIL-CLOSED: the aliyun CLI default credential chain cannot authenticate this run."
    facts = []
    if axis:
        facts.append("  axis       : %s" % axis)
    if exit_code is not None:
        facts.append("  axis exit  : %s" % exit_code)
    if hit:
        facts.append("  transport  : %s" % hit)
    body = [
        head,
        "  No cloud write was attempted. This skill did NOT fall back to reading",
        "  `~/.aliyun/config.json` or the ALIBABACLOUD_* environment variables.",
    ]
    body.extend(facts)
    body.append("")
    body.extend(CUSTOMER_CREDENTIAL_STEPS)
    body.append("")
    body.append(
        "Then re-run with the same parameters. Until step 1 succeeds the answer "
        "must state that cloud evidence could not be read; do not fill the gap "
        "from memory.")
    return "\n".join(body)


# ------------------------------------------- instance offer (core mechanism port)
# A customer id this run could not read is the one failure they can settle by
# choosing rather than restating. The duty sits at the dispatcher, where every
# axis answer is composed, and is withheld on runs that read nothing at all.
TARGET_ABSENT_PHRASE_RE = re.compile(
    r"(?i)(invalidinstanceid|invalidregionid|does not exist|no such instance|"
    r"returned an empty list|no instance\b|not found|cannot see|can not see|"
    r"is not visible|target-not-found)")
# Two further spellings the axes use for the same failure. They are accepted only
# when the line also names an instance, because "not visible"/"not returned" show up
# in explanatory prose and in field-level gaps that say nothing about this target.
TARGET_ABSENT_STRONG_RE = re.compile(r"(?i)(not returned|not visible)")
_INSTANCE_ID_TOKEN_RE = re.compile(r"\bi-[a-z0-9]{4,}\b")
TARGET_INSTANCE_HINT_RE = re.compile(r"(?i)(instance|invalidregionid)")

INSTANCE_OFFER_LIMIT = 3


def target_not_found_line(lines, target_id=None):
    """The run's own words saying the instance it was pointed at is not there.

    Keyed on what the run printed rather than on an exit code: the axes spell one
    failure several ways and return 0, 1, 2 or 3 for it, and the customer is owed
    the candidate list whichever spelling appeared. The softer spellings are read
    only when the same line points at an identifier - the id asked for, an
    i-... token, or the words "instance id" - so a sentence about instances in
    general never claims this run could not read the customer's.
    """
    for line in lines or []:
        if not TARGET_INSTANCE_HINT_RE.search(line):
            continue
        if TARGET_ABSENT_PHRASE_RE.search(line):
            return line.strip()
        if TARGET_ABSENT_STRONG_RE.search(line):
            low = line.lower()
            named = target_id and str(target_id) in line
            if (named or _INSTANCE_ID_TOKEN_RE.search(line)
                    or 'instance id' in low):
                return line.strip()
    return None


_INSTANCE_TARGET_FLAGS = ("--instance-id", "--instance-ids", "--instance-ref",
                          "--instance-id-a", "--instance-id-b")
_MISSING_INSTANCE_REASON = re.compile(
    r"(?i)\bMissing\s+(--instance-id|--instance-ids|--instance-ref|"
    r"--instance-id-a|--instance-id-b)\b")
_ARG_REQUIRED = re.compile(
    r"(?i)\berror:\s*the following arguments are required:\s*(.+?)\s*$")


def missing_instance_arg(err_lines):
    """True when the run names a missing instance target flag.

    The customer gave no instance to point the answer at; when the region is known
    the dispatcher owes them a choice from the online list, not a bare ask for an id.
    A missing region or mode flag does not trigger an instance listing.
    """
    for line in err_lines or []:
        match = _ARG_REQUIRED.search(line)
        if match:
            named = re.split(r"[ ,]+", match.group(1).strip())
            if any(token in _INSTANCE_TARGET_FLAGS for token in named):
                return True
        if _MISSING_INSTANCE_REASON.search(line):
            return True
    return False


def instance_offer_block(candidates, region=None, state='candidates', total=None,
                         had_target_id=True):
    """What an unreadable instance owes the customer: choices, not a dead end.

    `state` is `candidates` (rows were read), `empty` (the list read answered nothing
    for this credential and region) or `unavailable` (the list itself could not be
    read). An empty list is never rendered as "you have no instances" - it is a
    statement about this credential and region. Candidates are offered to be chosen
    from: the instance the customer named is never rewritten into one of them, and
    no id is invented here.
    """
    where = " in region %s" % region if region else " in the region this run queried"
    if had_target_id:
        head = ("Instance not readable%s: this run could not read the instance you named, "
                "so it asserts nothing about that instance." % where)
    else:
        head = ("No instance readable%s: this run found no instance to point the answer "
                "at, so it asserts nothing about any one of them." % where)
    out = [head]
    rows = [row for row in (candidates or []) if row]
    if state == 'candidates' and rows:
        shown = rows[:INSTANCE_OFFER_LIMIT]
        rest = (total - len(shown)) if isinstance(total, int) else 0
        out.append("Instances this credential lists%s (%d shown%s). Reply with the one "
                   "you mean - none of them is assumed to be yours, and the id you gave "
                   "stays unchanged unless you say so."
                   % (where, len(shown),
                      ", %d more not shown" % rest if rest > 0 else ""))
        out.extend("  - %s" % row for row in shown)
    elif state == 'empty':
        out.append("The instance list readable%s returned nothing to choose from. That "
                   "describes this credential and this region, not your account: check "
                   "the console region, or sign in with the account that owns the "
                   "instance, then give me the id you see there." % where)
    else:
        out.append("No candidate list could be read%s, so none is offered here. List the "
                   "instances in the ECS console%s, then give me the id you see - a "
                   "region mismatch reads exactly like a missing instance."
                   % (where, where))
    out.append("If the id you confirm still reads as missing, we stop here and hand "
               "this to an ECS specialist with the readings above.")
    return out


def region_sightings_block(instance_id, found_region=None, scanned=0,
                           total_regions=0, stop_reason=None):
    """How a bounded account-wide existence check reports one instance id.

    The check answers exactly one question - where this credential can read the
    id it was pointed at - and never moves the diagnosis target by itself. A
    partial sweep says not-checked, never not-found, and a stop names its
    reason. No region is claimed that this run did not query.
    """
    ident = str(instance_id or '').strip() or 'the instance you named'
    out = []
    if found_region:
        out.append("Region check: %s is readable in %s (checked %d of %d regions "
                   "on the built-in sweep list). Confirm it is the instance you mean "
                   "and re-run with --region-id %s; this run does not switch the "
                   "region by itself." % (ident, found_region, scanned, total_regions,
                                          found_region))
        return out
    if stop_reason:
        out.append("Region check: %s was not readable in the %d of %d regions this "
                   "sweep completed (%s). Regions not reached were not checked, "
                   "not called empty." % (ident, scanned, total_regions, stop_reason))
        return out
    out.append("Region check: %s was not readable in any of the %d regions on the "
               "built-in sweep list; regions outside that list were not covered. "
               "The id is either mistyped, outside this account, or the instance "
               "has been released; the readings above stand for the region this "
               "run queried." % (ident, total_regions))
    return out


def credential_probe_tokens(argv):
    """Tokens that would read stored credentials; refused before spawn."""
    hits = []
    for tok in argv or []:
        for probe in _PROBE_TOKENS:
            if probe in tok:
                hits.append(tok[:120])
                break
    return hits


def run_stream(cmd, timeout_s=600, env=None, sink=None, echo=True):
    """Run a child with an argument list, stream its output, return (rc, lines).

    Streaming is kept (the agent must not stare at a blank terminal for minutes)
    while every line is captured, because the credential decision and the report
    lead both have to be derived from what the child actually printed. A watchdog
    kills the child past the deadline, reported as 124 like `subprocess.run`.

    `echo` is True (sys.stdout, the historical behaviour), False/None (silent) or a
    stream object. The core dispatcher passes False and prints the customer-view
    answer block itself, so the raw child report never lands on stdout.
    """
    refused = credential_probe_tokens(cmd)
    if refused:
        msg = ("CREDENTIAL-PROBE-REFUSED: refusing to spawn a command that reads "
               "stored credentials: %s" % ", ".join(refused))
        print(msg, file=sys.stderr, flush=True)
        if sink is not None:
            sink.append(msg)
        return EXIT_PROBE_REFUSED, [msg]
    destination = sys.stdout if echo is True else (echo or None)
    try:
        # The deadline is enforced by the watchdog below (Popen has no timeout
        # parameter): it kills the child at timeout_s, so the call cannot hang.
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,  # noqa: timeout
                                stderr=subprocess.STDOUT, bufsize=1,
                                universal_newlines=True, errors="replace",
                                env=env)
    except FileNotFoundError as exc:
        msg = "entry could not be started: %s" % exc
        print(msg, file=sys.stderr, flush=True)
        return 2, [msg]
    killer = threading.Timer(timeout_s, proc.kill)
    killer.start()
    lines = []
    try:
        for line in proc.stdout:
            # Delivery hygiene: the agent copies stdout into the answer, so the
            # mask happens here rather than relying on the leg to redact.
            text = sanitize_identifiers(line.rstrip("\n"))
            lines.append(text)
            if sink is not None:
                sink.append(text)
            if destination is not None:
                destination.write(text + ("\n" if line.endswith("\n") else ""))
                destination.flush()
    finally:
        killer.cancel()
    rc = proc.wait()
    if rc < 0:
        msg = "axis entry timed out (%ds)" % timeout_s
        print(msg, file=sys.stderr, flush=True)
        lines.append(msg)
        return 124, lines
    return rc, lines
