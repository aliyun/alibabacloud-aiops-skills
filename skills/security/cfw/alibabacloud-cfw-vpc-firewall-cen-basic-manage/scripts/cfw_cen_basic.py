#!/usr/bin/env python3
"""Operational driver for Cloud Firewall VPC border firewalls on CEN Basic Edition.

This script exists because the workflow has three incompatible asynchronous
contracts, two server-side results that persist and can be read stale, and a set of
error codes whose messages say the opposite of what happened. Encoding that once is
more reliable than re-deriving it on every run.

Subcommands:
  list      List Basic-edition slots, optionally filtered by CEN or region.
  detail    Read one slot, including the shared regional firewall VPC and the ENI.
  precheck  Run the pre-access check and wait for a fresh verdict.
  attach    Configure VPC access, then wait for the provisioning task.
  switch    Open or close diversion for one slot.
  rename    Rename a firewall. This is the only editable field.
  remove    Remove VPC access, with a last-in-region warning.
  zones     List the legal primary and standby zone pairs for a region.

Design rules this script enforces, all of them for a reason that is documented in
references/workflow.md:

* Every row read back is asserted to be `TransitRouterType == "Basic"`, because
  `--transit-router-type` is case sensitive and silently drops the filter when the
  value is wrong.
* Mutating subcommands read the current state first and decline or short-circuit
  rather than issuing a call that is guaranteed to error, because none of these
  actions is idempotent and none accepts a client token.
* Asynchronous waits snapshot the previously stored identifier and ignore any poll
  that returns it, because both the task and the precheck verdict persist
  server-side and a naive poll reports the previous run as instant success.
* Timeouts follow the official guide rather than observed test timings, which were
  an order of magnitude faster on a lightly routed CEN.

Output: one JSON object on stdout. Diagnostics and progress go to stderr, so stdout
stays machine readable.

Environment:
  SKILL_SESSION_ID   32-character lowercase hex, required, reused across the session.

The skill version is read from references/manifest.json and is the only permitted
source for the User-Agent version segment; a missing or malformed manifest stops the
run.

Nothing here is interactive. Every wait is bounded and the process exits non-zero on
failure.

Usage:
  SKILL_SESSION_ID=<32-hex> python3 scripts/cfw_cen_basic.py list --region cn-shanghai
  SKILL_SESSION_ID=<32-hex> python3 scripts/cfw_cen_basic.py precheck \\
      --cen-id cen-xxxx --vpc-id vpc-xxxx --region cn-shanghai
  SKILL_SESSION_ID=<32-hex> python3 scripts/cfw_cen_basic.py --dry-run attach \\
      --cen-id cen-xxxx --vpc-id vpc-xxxx --region cn-shanghai \\
      --vswitch-id vsw-xxxx --name my-firewall
"""
import argparse
import atexit
import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta

SKILL_NAME = "alibabacloud-cfw-vpc-firewall-cen-basic-manage"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(REPO, "references", "manifest.json")

BASIC = "Basic"
NET_INSTANCE_TYPE = "cen_firewall"

# Timeouts come from the official guide, not from test timings. The guide budgets
# about 5 minutes to create and 5 to 30 minutes to open or close depending on route
# entry count. A lightly routed test CEN finished the same work in 28 to 140 seconds,
# which would make a production run look like a timeout.
TIMEOUT_TASK = 900       # attach provisioning
TIMEOUT_SWITCH = 2100    # open or close diversion, guide allows 30 minutes
TIMEOUT_REMOVE = 2100    # removal, longest observed when it tears down the region
TIMEOUT_PRECHECK = 300   # observed 3 to 12 seconds, but bounded generously

# Dense early, sparse later. Transitions that finish quickly finish inside the first
# couple of minutes, so that window is worth polling tightly; past it the guide's own
# budget is measured in minutes and a fixed 10 second interval would issue over 200
# list calls for a single operation - enough to invite the throttling that then shows
# up as the read failures this loop has to survive.
POLL_INTERVAL = 10
POLL_INTERVAL_LATE = 30
POLL_BACKOFF_AFTER = 120

# Sustained unreadability is different from an intermittent read failure. Over a
# 35 minute poll window a handful of throttled or transient transport failures are
# normal, so the counter that gives up is consecutive, not cumulative: a cumulative
# cap would abort a healthy long transition because of early jitter.
MAX_CONSECUTIVE_READ_FAILURES = 6

# Retrying a denial wastes the whole window and buries the real cause under a
# minute of noise, so these abort immediately instead of being retried.
PERMISSION_MARKERS = ("NoPermission", "ImplicitDeny", "Forbidden", "AccessDenied")

# FirewallSwitchStatus values. The three transient ones are absent from the CLI's
# documented filter enum yet occur constantly; polling that rejects them misreads a
# healthy transition.
STEADY = ("notconfigured", "closed", "opened")
TRANSIENT = ("opening", "closing", "deleting")

# Error codes whose messages contradict their cause. Matched on code, never on text.
MISLEADING = {
    "ErrorFirewallStatus": (
        "The VPC is already attached. The message says to retry later, but retrying "
        "never succeeds. Use switch, rename or remove instead."
    ),
    "ErrorVpcFirewallExist": (
        "The slot id does not exist. The message claims the firewall is already "
        "configured, which is the opposite of the truth. Verify the id with list."
    ),
}

SESSION_RE = re.compile(r"^[0-9a-f]{32}$")
REGION_RE = re.compile(r"^[a-z]{2}-[a-z]+-?[0-9a-z]*(-[0-9]+)?$")
CIDR_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")


# ---------------------------------------------------------------------------
# output helpers: data on stdout, everything else on stderr
# ---------------------------------------------------------------------------
def diag(msg):
    print(msg, file=sys.stderr, flush=True)


def progress(msg):
    diag("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def fail(message, **extra):
    """Report a terminal failure and exit non-zero."""
    payload = {"ok": False, "error": message}
    payload.update(extra)
    emit(payload)
    sys.exit(1)


def load_skill_version():
    """The UA version segment comes only from this skill's manifest.

    Guessing or reusing another skill's version would put a wrong value into every
    observability record for the session, so a problem here is a hard stop.
    """
    try:
        with open(MANIFEST, encoding="utf-8") as handle:
            version = json.load(handle).get("version")
    except OSError as exc:
        fail("cannot read %s: %s" % (MANIFEST, exc))
    except ValueError as exc:
        fail("%s is not valid JSON: %s" % (MANIFEST, exc))
    if not isinstance(version, str) or not version.strip():
        fail("%s has no usable top-level string 'version'" % MANIFEST)
    return version.strip()


def resolve_session_id(raw):
    if not raw:
        fail(
            "SKILL_SESSION_ID is not set. Generate a 32-character lowercase hex id "
            "once per session and pass it to every command, so all calls share one "
            "trace.",
            hint="python3 -c \"import uuid;print(uuid.uuid4().hex)\"",
        )
    value = raw.strip().lower()
    if not SESSION_RE.match(value):
        fail(
            "SKILL_SESSION_ID must be exactly 32 lowercase hexadecimal characters.",
            received=raw,
        )
    return value


def api_now_utc8():
    """Response timestamps are UTC+8 with no zone marker; compare in that frame."""
    return datetime.utcnow() + timedelta(hours=8)


def parse_ts(text):
    if not text:
        return None
    try:
        return datetime.strptime(str(text).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CLI invocation
# ---------------------------------------------------------------------------
class Cli:
    """Thin wrapper that tags every cloud call with the session User-Agent."""

    def __init__(self, session_id, skill_version, dry_run=False):
        self.ua = "AlibabaCloud-Agent-Skills/%s/%s skill-version/%s" % (
            SKILL_NAME, session_id, skill_version)
        self.dry_run = dry_run
        self.calls = 0
        self.planned = []

    def run(self, product, args, mutating=False):
        """Run one command and return (ok, parsed_or_text).

        Reads always execute, even in a dry run, because every mutating path here is
        check-then-act: without the current state the plan cannot be validated. Only
        mutating calls are short-circuited.

        Transport-level faults are retried once, because a `bad file descriptor`
        dial failure was observed on this plugin while other products and a direct
        request to the same endpoint all succeeded.
        """
        cmd = ["aliyun", product] + list(args)
        if product != "help":
            cmd += ["--user-agent", self.ua]
        if self.dry_run and mutating:
            self.planned.append(" ".join(cmd))
            diag("DRY-RUN (not sent) " + " ".join(cmd))
            return True, {"_dry_run": True, "command": cmd}

        # Counted only once the call is actually going out, so the two summary lines
        # at exit cannot contradict each other on a dry run.
        self.calls += 1

        last_err = ""
        for attempt in (1, 2):
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            except subprocess.TimeoutExpired:
                last_err = "local command timed out after 180s"
                continue
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            if proc.returncode == 0 and out:
                try:
                    return True, json.loads(out)
                except ValueError:
                    return True, {"_raw": out[:2000]}
            last_err = err or out
            if "bad file descriptor" not in last_err:
                break
            if attempt == 1:
                progress("transport error, retrying once: %s" % last_err[:120])
                time.sleep(2)
        return False, {"error": last_err[:2000]}

    def cloudfw(self, *args, **kw):
        return self.run("cloudfw", list(args), mutating=kw.get("mutating", False))

    def vpc(self, *args):
        return self.run("vpc", list(args))

    def ecs(self, *args):
        return self.run("ecs", list(args))


def extract_code(err_text):
    """Pull the API error code out of an SDKError blob.

    The blob contains both `StatusCode: 400` and `Code: ErrorPreCheckDoing`, so a
    naive search for `Code:` matches the status line first and yields `400`. The
    embedded JSON is tried first because it is unambiguous; the plain-text fallback
    excludes the `StatusCode:` line by lookbehind.
    """
    text = err_text or ""
    match = re.search(r'"Code"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1)
    match = re.search(r'(?<!Status)Code:\s*([^\s,]+)', text)
    return match.group(1) if match else ""


def report_api_error(action, result):
    """Turn an API failure into something actionable, correcting known bad text."""
    text = result.get("error", "") if isinstance(result, dict) else str(result)
    code = extract_code(text)
    payload = {"action": action, "code": code, "raw": text[:600]}
    if code in MISLEADING:
        payload["interpretation"] = MISLEADING[code]
    if code == "ErrorPreCheckDoing":
        payload["interpretation"] = (
            "The precheck is still running. This arrives as an HTTP 400 SDKError, "
            "not as a success response, so it is easy to mistake for a failure. "
            "Keep polling."
        )
    if is_permission_error(text):
        payload["interpretation"] = (
            "Permission denied. Read references/ram-policies.md for the required "
            "actions - note the prefix is yundun-cloudfirewall, not cloudfw - then "
            "use the ram-permission-diagnose skill and wait for the grant."
        )
    fail("API call failed: %s" % (action,), **payload)


def is_permission_error(text):
    """Prefer the error code, and fall back to the whole blob.

    Matching the blob catches denials whose code this catalogue has not seen, but on its
    own it is too eager: a message that merely contains the word Forbidden would abort a
    poll loop that should have retried, and inside a poll the cost of a false positive
    is giving up on a write that was still landing. So the code decides when there is
    one.
    """
    code = extract_code(text or "")
    if code:
        return any(marker in code for marker in PERMISSION_MARKERS)
    return any(marker in (text or "") for marker in PERMISSION_MARKERS)


def poll_interval(elapsed):
    """Interval to wait before the next poll, given seconds elapsed so far."""
    return POLL_INTERVAL if elapsed < POLL_BACKOFF_AFTER else POLL_INTERVAL_LATE


def unknown_outcome(slot_id, stage, reason):
    """Fields every `write accepted but terminal state unconfirmed` exit must carry.

    Without them the caller sees a non-zero exit and retries the write, and no
    mutating call in this product is idempotent: the retry returns ErrorFirewallStatus
    or -360142, whose text invites further retries that can never succeed. The most
    likely outcome at this point is that the original change succeeded.
    """
    return {
        "mutation_sent": True,
        "outcome": "unknown",
        "stage": stage,
        "slot_id": slot_id,
        "do_not_retry": (
            "The write was accepted and is still being applied server side. "
            "Repeating it returns an error, not a no-op."
        ),
        "recheck": (
            "SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py detail "
            "--slot-id %s" % slot_id
        ),
        "reason": reason,
    }


def incomplete_outcome(slot_id, stage, reason, investigate):
    """Fields for `the transition completed but verification came back negative`.

    Deliberately not `unknown`. An unknown result tells the caller to recheck, because
    the state may still settle; this one is a settled negative, and sending the caller
    to recheck would loop it through an answer that cannot change. What it needs is
    where to look, so this carries `investigate` in place of `recheck`.
    """
    return {
        "mutation_sent": True,
        "outcome": "confirmed_incomplete",
        "stage": stage,
        "slot_id": slot_id,
        "do_not_retry": ("The state transition itself completed, so repeating the "
                         "operation would either error or start a second unwanted "
                         "change."),
        "reason": reason,
        "investigate": investigate,
    }


def report_read_failure(action, err):
    """Hard-stop a read that failed outside a poll loop.

    Query contexts must not tolerate a failed read the way polling does: with no
    mutation in flight there is nothing to protect by continuing, and reporting an
    empty result from a failed read is the silent-failure case this skill exists to
    avoid.
    """
    if is_permission_error(err):
        report_api_error(action, {"error": err})
    fail("Could not read %s." % action,
         action=action, raw=(err or "")[:600],
         hint="No result is being reported from this read. Retry the command; if it "
              "keeps failing, treat the current state as unknown rather than empty.")


def require_consent(cli, args, operation, bullets, **ctx):
    """Refuse to proceed until the operator has been told what will happen.

    Every caller must reach this after the state read, never before. A gate that fires
    on invocations that turn out to be no-ops teaches the caller to pass --yes by
    reflex, which disarms it on the one run where it matters.

    A dry run is exempt because it sends nothing, and seeing the planned command is
    what the operator needs in order to decide.
    """
    if getattr(args, "yes", False) or cli.dry_run:
        return
    diag("")
    diag("Before %s, tell the user:" % operation)
    for line in bullets:
        diag("  - %s" % line)
    diag("Re-run with --yes once the user has agreed.")
    fail("%s requires explicit confirmation; pass --yes after informing the user"
         % operation, **ctx)


# ---------------------------------------------------------------------------
# regional write lock
# ---------------------------------------------------------------------------
# The firewall VPC is shared per CEN per region: the first attach in a region creates
# it and the last removal destroys it. Both decisions are made by reading a flag and
# then writing, and nothing server side serialises the pair, so two runs that read the
# flag in the same moment each conclude they are the first. This is not hypothetical -
# the eval harness runs cases concurrently.
#
# The lock closes that window for runs on one host. It cannot help across hosts and
# the cloud offers no lock to hold, so the guarantee is deliberately local and is
# documented as such rather than presented as a correctness property.
#
# Failing to take it is never fatal. A run that cannot write a lock directory proceeds
# and says so, because refusing to operate over a local filesystem quirk would be a
# worse failure than the race being guarded against.
LOCK_TTL = TIMEOUT_PRECHECK + TIMEOUT_TASK + TIMEOUT_SWITCH + 300
LOCK_DIRNAME = "alibabacloud-cfw-vpc-firewall-cen-basic"


def lock_directory():
    """First writable place to keep lock files, or None when there is none."""
    bases = [tempfile.gettempdir(),
             os.path.join(os.path.expanduser("~"), ".cache")]
    for base in bases:
        candidate = os.path.join(base, LOCK_DIRNAME)
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".writable-%d" % os.getpid())
            with open(probe, "w"):
                pass
            os.unlink(probe)
        except OSError:
            continue
        return candidate
    return None


def holder_is_alive(info):
    """Whether the process named in a lock file still exists.

    os.kill(pid, 0) raises PermissionError for a live process owned by another user,
    which is the one case where the answer is yes but the call did not succeed.
    """
    pid = info.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def lock_age(path):
    try:
        return int(time.time() - os.path.getmtime(path))
    except OSError:
        return None


def release_region_lock(path):
    if not path:
        return
    try:
        os.unlink(path)
    except OSError:
        pass


def refuse_locked_out(region, path, holder):
    """Report contention. Nothing was sent, so this is not an unknown outcome."""
    fail("Another run holds the write lock for region %s, so this command did not "
         "start. The regional firewall VPC is shared, and two runs that both read it "
         "as absent would each try to create it." % region,
         region=region, stage="lock", mutation_sent=False,
         lock_path=path, lock_holder=holder, lock_age_seconds=lock_age(path),
         hint="Wait for the other run to finish, then retry. If no other run is "
              "active the lock is stale: delete %s and retry." % path)


def acquire_region_lock(cli, region):
    """Take the regional write lock, unless this is a dry run.

    Released when the process exits, which includes the sys.exit inside fail(), so no
    caller has to wrap its body in try/finally. A SIGKILL leaves the file behind and
    the pid and age checks treat it as stale on the next run.

    Re-entrant for this pid. Without that, a caller whose earlier command failed and
    was caught - as tests do with SystemExit - would deadlock against a lock it owns.
    """
    if cli.dry_run or not region:
        return None
    directory = lock_directory()
    if directory is None:
        diag("WARNING: no writable lock directory, so this run holds no regional "
             "write lock. Do not run two mutating commands for one region at once.")
        return None
    path = os.path.join(directory, "region-%s.lock" % region)
    record = json.dumps({"pid": os.getpid(), "started": int(time.time()),
                         "region": region, "command": " ".join(sys.argv[1:])})
    for attempt in (1, 2):
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            holder, stale = {}, False
            try:
                with open(path, encoding="utf-8") as existing:
                    holder = json.load(existing)
            except (OSError, ValueError):
                stale = True              # unreadable or not JSON: abandoned
            else:
                if holder.get("pid") == os.getpid():
                    diag("regional write lock for %s already held by this process"
                         % region)
                    return path
                age = lock_age(path)
                stale = ((age is not None and age > LOCK_TTL)
                         or not holder_is_alive(holder))
            if stale and attempt == 1:
                diag("clearing a stale lock for region %s (holder pid %s)"
                     % (region, holder.get("pid")))
                try:
                    os.unlink(path)
                except OSError:
                    pass
                continue
            refuse_locked_out(region, path, holder)
        except OSError as exc:
            diag("WARNING: could not take the regional write lock (%s); continuing "
                 "without it." % exc)
            return None
        with os.fdopen(handle, "w", encoding="utf-8") as written:
            written.write(record)
        atexit.register(release_region_lock, path)
        diag("regional write lock taken for %s" % region)
        return path
    return None


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------
def need(value, label, hint=""):
    if value in (None, ""):
        fail("%s is required.%s" % (label, (" " + hint) if hint else ""))
    return value


def check_region(value):
    need(value, "--region")
    if not REGION_RE.match(value):
        fail(
            "--region must be a valid Alibaba Cloud region id.",
            received=value,
            expected_format="cn-shanghai, cn-hangzhou, ap-southeast-1",
        )
    return value


def check_id(value, label, prefix):
    need(value, label)
    if not value.startswith(prefix):
        fail(
            "%s must start with '%s'." % (label, prefix),
            received=value,
            hint="A CEN id looks like cen-xxxx, a slot id like vfw-xxxx, a VPC like "
                 "vpc-xxxx and a vSwitch like vsw-xxxx. Passing the wrong kind "
                 "produces a confusing error rather than a clear one.",
        )
    return value


def check_name(value):
    need(value, "--name")
    if len(value) > 128:
        fail("--name must be at most 128 characters.", received_length=len(value))
    return value


def check_cidr(value, label):
    need(value, label)
    if not CIDR_RE.match(value):
        fail("%s must be an IPv4 CIDR such as 10.0.0.0/24." % label, received=value)
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        fail("%s is not a valid CIDR: %s" % (label, exc), received=value)
    return str(network)


def check_firewall_cidrs(vpc_cidr, vsw_cidr):
    """Validate the firewall VPC and vSwitch CIDR pair before a rejected create call.

    Two constraints are enforced, because both hold in every observed case:

    * the allowed ranges are 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 and their
      subnets;
    * the vSwitch CIDR must be a subnet of the firewall VPC CIDR.

    The mask-length limits are deliberately NOT enforced. The API help asks for a
    mask of no more than 28 bits on the VPC and 29 on the vSwitch, which would mean
    a prefix length of at least 28 and 29. That reading contradicts the service's own
    defaults - the VPC default is 10.0.0.0/8 - and contradicts configurations that
    were accepted in practice, where a /24 VPC with a /26 vSwitch worked twice. The
    reverse reading is contradicted by the vSwitch default of /29. Since the
    documentation and the observed behaviour cannot both be right, the check that
    would reject a known-good configuration is left out and the service is allowed to
    answer.
    """
    vpc_net = ipaddress.ip_network(check_cidr(vpc_cidr, "--fw-vpc-cidr"), strict=False)
    vsw_net = ipaddress.ip_network(
        check_cidr(vsw_cidr, "--fw-vswitch-cidr"), strict=False)

    allowed = [ipaddress.ip_network(c) for c in
               ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if not any(_subnet_of(vpc_net, a) for a in allowed):
        fail(
            "--fw-vpc-cidr must be 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 or a "
            "subnet of one of them.",
            received=str(vpc_net),
        )
    if not _subnet_of(vsw_net, vpc_net):
        fail(
            "--fw-vswitch-cidr must be a subnet of --fw-vpc-cidr.",
            received_vswitch=str(vsw_net),
            received_vpc=str(vpc_net),
        )
    return str(vpc_net), str(vsw_net)


def _subnet_of(inner, outer):
    try:
        return inner.subnet_of(outer)
    except (TypeError, AttributeError):
        # Python 3.6 has no subnet_of; compare network and broadcast addresses.
        return (int(inner.network_address) >= int(outer.network_address)
                and int(inner.broadcast_address) <= int(outer.broadcast_address))


# ---------------------------------------------------------------------------
# reads
# ---------------------------------------------------------------------------
def fetch_slots(cli, cen_id=None, region=None, page_size=50, strict=True):
    """List slots, then assert the edition on every row.

    The assertion is the point: `--transit-router-type` is case sensitive and is
    silently dropped when the value is wrong, in which case the response contains
    slots this skill must never touch. It is kept in this one function precisely so
    there is no second, laxer implementation of it anywhere.

    Returns (rows, skipped, total_count, error). With strict=True a bad read calls
    fail() and never returns, which is right for a query: reporting an empty result
    from a read that did not happen is a silent wrong answer. Polling passes
    strict=False and inspects error itself, because there a bad read must not abort
    a change that is already in flight. rows is None, never [], when the read failed.
    """
    args = ["describe-vpc-firewall-cen-list", "--transit-router-type", BASIC,
            "--page-size", str(page_size), "--lang", "zh"]
    if cen_id:
        args += ["--cen-id", cen_id]
    if region:
        args += ["--region-no", region]
    ok, resp = cli.cloudfw(*args)
    if not ok:
        if not strict:
            return None, None, None, resp.get("error", "") if isinstance(resp, dict) else str(resp)
        report_api_error("describe-vpc-firewall-cen-list", resp)
    if "TotalCount" not in resp:
        if not strict:
            return None, None, None, "response has no TotalCount key: %s" % (
                json.dumps(resp)[:300],)
        fail(
            "Unexpected response shape from describe-vpc-firewall-cen-list.",
            received=resp,
            hint="A missing TotalCount usually means a flag was rejected rather than "
                 "that nothing was found. Do not report an empty result from this.",
        )
    rows = resp.get("VpcFirewalls") or []
    basic, skipped = [], []
    for row in rows:
        local = row.get("LocalVpc") or {}
        if local.get("TransitRouterType") == BASIC:
            basic.append(row)
        else:
            skipped.append({
                "VpcFirewallId": row.get("VpcFirewallId"),
                "TransitRouterType": local.get("TransitRouterType"),
            })
    if skipped:
        progress("dropped %d non-Basic row(s) that the edition filter let through"
                 % len(skipped))
    return basic, skipped, resp.get("TotalCount"), None


def find_slot(cli, cen_id=None, region=None, slot_id=None, vpc_id=None):
    """Resolve exactly one slot, by id or by VPC."""
    rows, skipped, total, _ = fetch_slots(cli, cen_id, region)
    matches = []
    for row in rows:
        local = row.get("LocalVpc") or {}
        if slot_id and row.get("VpcFirewallId") == slot_id:
            matches.append(row)
        elif vpc_id and local.get("NetworkInstanceId") == vpc_id:
            matches.append(row)
    if not matches:
        fail(
            "No Basic-edition slot matched.",
            slot_id=slot_id, vpc_id=vpc_id, cen_id=cen_id, region=region,
            total_returned=total, non_basic_dropped=len(skipped),
            hint="A nonexistent CEN id also returns TotalCount 0, so confirm the CEN "
                 "id is valid before concluding the VPC is unprotected. A VPC that "
                 "joined the CEN recently may need the console's asset sync, which "
                 "has no CLI equivalent.",
        )
    if len(matches) > 1:
        fail(
            "Several Basic slots matched; narrow the request with --cen-id or "
            "--region.",
            matched=[m.get("VpcFirewallId") for m in matches],
        )
    return matches[0]


def slot_summary(row):
    local = row.get("LocalVpc") or {}
    return {
        "VpcFirewallId": row.get("VpcFirewallId"),
        "VpcFirewallName": row.get("VpcFirewallName"),
        "FirewallSwitchStatus": row.get("FirewallSwitchStatus"),
        "PrecheckStatus": row.get("PrecheckStatus"),
        "CenId": row.get("CenId"),
        "CenName": row.get("CenName"),
        "RegionNo": local.get("RegionNo"),
        "VpcId": local.get("NetworkInstanceId"),
        "VpcName": local.get("VpcName"),
        "TransitRouterType": local.get("TransitRouterType"),
        "TransitRouterId": local.get("TransitRouterId"),
        "SupportManualMode": local.get("SupportManualMode"),
        "DefendCidrList": local.get("DefendCidrList"),
        "IpsConfig": row.get("IpsConfig"),
        "AclConfig": row.get("AclConfig"),
    }


def fetch_detail(cli, slot_id):
    ok, resp = cli.cloudfw("describe-vpc-firewall-cen-detail",
                           "--vpc-firewall-id", slot_id, "--lang", "zh")
    if not ok:
        report_api_error("describe-vpc-firewall-cen-detail", resp)
    return resp


def detail_summary(detail):
    fw = detail.get("FirewallVpc") or {}
    local = detail.get("LocalVpc") or {}
    eni = (local.get("EniList") or [{}])[0]
    return {
        "VpcFirewallId": detail.get("VpcFirewallId"),
        "VpcFirewallName": detail.get("VpcFirewallName"),
        "FirewallSwitchStatus": detail.get("FirewallSwitchStatus"),
        "AllowConfiguration": fw.get("AllowConfiguration"),
        "FirewallVpc": {
            "VpcId": fw.get("VpcId"),
            "VpcCidr": fw.get("VpcCidr"),
            "VswitchId": fw.get("VswitchId"),
            "VswitchCidr": fw.get("VswitchCidr"),
            "ZoneId": fw.get("ZoneId"),
            "StandbyZoneId": fw.get("StandbyZoneId"),
            "VswitchZoneId": fw.get("VswitchZoneId"),
            "FirewallServiceMode": fw.get("FirewallServiceMode"),
        },
        "LocalVpc": {
            "VpcId": local.get("NetworkInstanceId"),
            "VpcName": local.get("NetworkInstanceName"),
            "RegionNo": local.get("RegionNo"),
            "TransitRouterType": local.get("TransitRouterType"),
            "RouteMode": local.get("RouteMode"),
            "SupportManualMode": local.get("SupportManualMode"),
            "DefendCidrList": local.get("DefendCidrList"),
            "AttachmentId": local.get("AttachmentId"),
        },
        "Eni": {
            "EniId": eni.get("EniId"),
            "EniPrivateIpAddress": eni.get("EniPrivateIpAddress"),
            "EniVSwitchId": eni.get("EniVSwitchId"),
            "EniZoneId": eni.get("EniZoneId"),
        },
    }


def current_status(cli, slot_id, cen_id=None, region=None):
    """Returns (read_ok, status).

    Three outcomes must stay distinguishable. `read_ok=False` means the read did not
    happen. `status=None` with `read_ok=True` means the read succeeded and the slot is
    absent, which during removal is the success signal. Collapsing the two reports an
    absent slot for a failed read, and an absent slot reads as "already removed".
    """
    rows, _, _, err = fetch_slots(cli, cen_id, region, strict=False)
    if err is not None:
        return False, err
    for row in rows:
        if row.get("VpcFirewallId") == slot_id:
            return True, row.get("FirewallSwitchStatus")
    return True, None


def wait_status(cli, slot_id, target, timeout, cen_id=None, region=None,
                absent_is_success=False):
    """Poll the list until the slot settles on `target`.

    The caller has already sent a mutating request, so no outcome of this function may
    be reported as a plain failure:

    - transient states are progress, not errors; rejecting them aborts a healthy
      transition
    - an intermittent read failure is retried, because the change is still in flight
      and a failed read says nothing about it
    - sustained unreadability, and the timeout, both return outcome="unknown" with the
      do-not-retry fields attached rather than reached=False alone

    `absent_is_success` is set by removal only. A slot normally stays listed and resets
    to notconfigured, but if it disappears from the list that is the same end state, and
    polling it to a timeout would report a successful removal as unconfirmed. It must
    not be set for a switch: there the slot is known to be listed, so absence means the
    filter or the id is wrong, and calling that success would hide it.
    """
    deadline = time.time() + timeout
    seen = []
    started = time.time()
    consecutive = 0
    read_failures = 0
    unreadable_since = None
    while time.time() < deadline:
        read_ok, status = current_status(cli, slot_id, cen_id, region)
        if not read_ok:
            read_failures += 1
            consecutive += 1
            if unreadable_since is None:
                unreadable_since = time.time()
            if is_permission_error(status):
                out = unknown_outcome(slot_id, "poll", "permission denied while polling")
                out.update({"reached": False, "path": seen, "read_failures": read_failures,
                            "seconds": round(time.time() - started)})
                out["error"] = status
                out["interpretation"] = (
                    "Polling stopped immediately: a denial will not clear on retry. "
                    "Grant the actions in references/ram-policies.md, then recheck. "
                    "Do not repeat the write."
                )
                return out
            if consecutive >= MAX_CONSECUTIVE_READ_FAILURES:
                # Report measured time, not the interval times the count. A single read
                # can block for the CLI's own timeout plus one transport retry, so
                # multiplying out the interval understates the outage by minutes and
                # sends whoever reads this looking for the wrong kind of fault.
                out = unknown_outcome(
                    slot_id, "poll",
                    "%d consecutive status reads failed over %ds of wall clock"
                    % (consecutive, round(time.time() - unreadable_since)))
                out.update({"reached": False, "path": seen, "read_failures": read_failures,
                            "last_error": status[:400],
                            "seconds": round(time.time() - started)})
                return out
            progress("status read failed %d time(s) in a row; the change is still "
                     "in flight, continuing: %s" % (consecutive, str(status)[:120]))
            time.sleep(poll_interval(time.time() - started))
            continue

        consecutive = 0
        unreadable_since = None
        if status is None:
            if absent_is_success:
                seen.append("absent")
                progress("slot %s is no longer listed, which is the removal end state"
                         % slot_id)
                return {
                    "reached": True,
                    "outcome": "confirmed",
                    "status": "absent",
                    "path": seen,
                    "read_failures": read_failures,
                    "seconds": round(time.time() - started),
                    "note": "The slot left the list rather than resetting to "
                            "notconfigured. Treat this as removed, and confirm with "
                            "the detail subcommand.",
                }
            progress("slot %s is not in the list yet" % slot_id)
        elif not seen or seen[-1] != status:
            seen.append(status)
            kind = "transient" if status in TRANSIENT else "steady"
            progress("status=%s (%s)" % (status, kind))
            if status == target:
                return {
                    "reached": True,
                    "outcome": "confirmed",
                    "status": status,
                    "path": seen,
                    "read_failures": read_failures,
                    "seconds": round(time.time() - started),
                }
        time.sleep(poll_interval(time.time() - started))

    out = unknown_outcome(slot_id, "poll", "timed out after %ds without reaching '%s'"
                          % (timeout, target))
    out.update({
        "reached": False,
        "status": seen[-1] if seen else None,
        "path": seen,
        "read_failures": read_failures,
        "seconds": round(time.time() - started),
        "timeout": timeout,
        "hint": "Timeouts here follow the official guide, which allows 5 to 30 "
                "minutes for a switch transition depending on route entry count. "
                "If the slot is still in a transient state, keep polling rather "
                "than treating this as a failure.",
    })
    return out


# ---------------------------------------------------------------------------
# precheck
# ---------------------------------------------------------------------------
def run_precheck(cli, cen_id, vpc_id, region, wait=True):
    """Issue the check, then wait for a verdict that is provably fresh.

    The stored verdict persists server-side, so reading it without re-issuing the
    create call can report a problem the user has already fixed. Freshness is
    established by comparing the returned timestamp against the moment of the call,
    in UTC+8 because the service omits a zone marker.
    """
    issued_at = api_now_utc8()
    common = ["--cen-id", cen_id, "--vpc-id", vpc_id,
              "--network-instance-type", NET_INSTANCE_TYPE,
              "--biz-region", region, "--lang", "zh"]

    ok, resp = cli.cloudfw("create-vpc-firewall-precheck", *common, mutating=True)
    if not ok:
        report_api_error("create-vpc-firewall-precheck", resp)
    if cli.dry_run:
        # The create call was suppressed, so no PrecheckId exists to poll for. Falling
        # through would spend the whole TIMEOUT_PRECHECK on real read calls that can
        # only ever report an unknown status, which is why every other mutating
        # subcommand returns at exactly this point instead.
        return {"ok": True, "dry_run": True, "cen_id": cen_id, "vpc_id": vpc_id,
                "region": region, "planned": resp.get("command")}
    precheck_id = resp.get("PrecheckId")
    progress("precheck issued, PrecheckId=%s" % precheck_id)

    if not wait:
        return {"ok": True, "PrecheckId": precheck_id, "waited": False}

    deadline = time.time() + TIMEOUT_PRECHECK
    polls = 0
    doing = 0
    started = time.time()
    while time.time() < deadline:
        polls += 1
        ok, det = cli.cloudfw("describe-vpc-firewall-precheck-detail", *common)
        if not ok:
            text = det.get("error", "") if isinstance(det, dict) else str(det)
            # "Still running" arrives as an HTTP 400 SDKError, so it reaches this
            # branch rather than the success path. Treating it as a failure aborts a
            # healthy precheck, which is the single easiest mistake to make here.
            if extract_code(text) == "ErrorPreCheckDoing":
                doing += 1
                progress("poll %d: still running (ErrorPreCheckDoing)" % polls)
                time.sleep(POLL_INTERVAL)
                continue
            report_api_error("describe-vpc-firewall-precheck-detail", det)

        detail = det.get("PrecheckDetail") or {}
        status = detail.get("PrecheckStatus")
        stamp = parse_ts(detail.get("PrecheckTimestamp"))
        progress("poll %d: status=%s ts=%s" % (polls, status,
                                               detail.get("PrecheckTimestamp")))
        if status in ("passed", "failed"):
            fresh = bool(stamp and stamp >= issued_at - timedelta(seconds=5))
            if not fresh:
                progress("WARNING: verdict predates this run, treating as stale")
                time.sleep(POLL_INTERVAL)
                continue
            return {
                "ok": status == "passed",
                "PrecheckId": precheck_id,
                "PrecheckStatus": status,
                "PrecheckTimestamp": detail.get("PrecheckTimestamp"),
                "is_fresh": fresh,
                "polls": polls,
                "doing_signals": doing,
                "seconds": round(time.time() - started),
                "groups": summarise_groups(detail),
                "failures": collect_failures(detail),
            }
        time.sleep(POLL_INTERVAL)

    return {
        "ok": False, "PrecheckId": precheck_id, "timed_out": True,
        "polls": polls, "seconds": round(time.time() - started),
        "timeout": TIMEOUT_PRECHECK,
    }


def summarise_groups(detail):
    out = []
    for group in detail.get("PrecheckEntityGroups") or []:
        out.append({
            "Name": group.get("Name"),
            "Status": group.get("PrecheckEntityGroupStatus"),
            "FailedCount": group.get("FailedCount"),
            "Entities": [
                {"Name": e.get("Name"), "Status": e.get("Status")}
                for e in group.get("PrecheckEntities") or []
            ],
        })
    return out


def collect_failures(detail):
    """Extract every failing entity, not just the first group.

    Only the top-level PrecheckStatus is an aggregate; the offending group is the
    only one that flips while the others still report passed, so all of them have to
    be walked.
    """
    failures = []
    for group in detail.get("PrecheckEntityGroups") or []:
        for entity in group.get("PrecheckEntities") or []:
            if entity.get("Status") == "passed":
                continue
            failures.append({
                "Group": group.get("Name"),
                "Name": entity.get("Name"),
                "Status": entity.get("Status"),
                "Suggestion": entity.get("Suggestion"),
                "Info": entity.get("Info"),
            })
    return failures


def resolve_route_tables(cli, region, vpc_id):
    """Name the resources a precheck failure only describes generically.

    A failing entity carries no identifier, so "a custom route table is bound to a
    vSwitch" is not actionable until the actual tables are looked up. This is a
    best-effort aid: a failure to read them must not mask the verdict itself.
    """
    ok, resp = cli.vpc("describe-route-table-list", "--biz-region-id", region,
                       "--vpc-id", vpc_id)
    if not ok:
        return {"available": False, "reason": resp.get("error", "")[:200]}
    if "TotalCount" not in resp:
        return {
            "available": False,
            "reason": "response has no TotalCount; the region flag may be wrong. "
                      "vpc and ecs use --biz-region-id, not --region-id.",
        }
    custom = []
    for table in (resp.get("RouterTableList") or {}).get("RouterTableListType") or []:
        if table.get("RouteTableType") == "Custom":
            custom.append({
                "RouteTableId": table.get("RouteTableId"),
                "RouteTableName": table.get("RouteTableName"),
                "Status": table.get("Status"),
                "BoundVSwitchIds": (table.get("VSwitchIds") or {}).get("VSwitchId"),
            })
    return {"available": True, "custom_route_tables": custom}


# ---------------------------------------------------------------------------
# attach
# ---------------------------------------------------------------------------
def cmd_attach(cli, args):
    cen_id = check_id(args.cen_id, "--cen-id", "cen-")
    vpc_id = check_id(args.vpc_id, "--vpc-id", "vpc-")
    region = check_region(args.region)
    name = check_name(args.name)
    vswitch_id = check_id(args.vswitch_id, "--vswitch-id", "vsw-")

    # Held from before the first read until exit. The AllowConfiguration flag that
    # decides whether this attach creates the regional firewall VPC is read below, and
    # a second run reading it in the same moment would reach the same conclusion.
    acquire_region_lock(cli, region)

    # Locate the slot first. Attaching with a bad CEN or VPC produces a confusing
    # error, and the slot already exists for any VPC attached to the CEN.
    slot = find_slot(cli, cen_id=cen_id, region=region, vpc_id=vpc_id)
    slot_id = slot.get("VpcFirewallId")
    status = slot.get("FirewallSwitchStatus")

    # check-then-act: no mutating call in this product is idempotent and none
    # accepts a client token, so a repeat call errors rather than no-ops.
    if status != "notconfigured":
        fail(
            "Slot %s is already in state '%s'; attach only applies to a "
            "notconfigured slot." % (slot_id, status),
            slot_id=slot_id, status=status,
            hint="Use switch to change diversion, rename to change the name, or "
                 "remove followed by attach to change the configuration. The "
                 "firewall VPC CIDR, vSwitch CIDRs, zones and business vSwitch "
                 "cannot be edited after creation.",
        )

    detail = fetch_detail(cli, slot_id)
    fw = detail.get("FirewallVpc") or {}
    allow = fw.get("AllowConfiguration")
    first_in_region = allow == 1

    # Gated on the switch, not on attach itself. `close` is the default and leaves the
    # firewall dormant with no traffic impact, so it needs no consent; `open` produces
    # exactly the diversion start that the switch subcommand gates, and leaving it
    # ungated here would be a bypass of that gate.
    if args.firewall_switch == "open":
        require_consent(cli, args, "attaching %s with diversion opening immediately"
                        % vpc_id, [
            "established long-lived connections flap for sub-second intervals;",
            "    short connections are unaffected",
            "SLB and RDS sessions can drop, so a low-traffic window is advised",
            "opening cannot be paused or rolled back once accepted",
            "attaching alone already takes minutes, and the official guide allows",
            "    5 to 30 more minutes for the diversion on top of that",
            "the safer path is attach with --firewall-switch close, verify, then",
            "    use the switch subcommand to open in a chosen window",
        ], slot_id=slot_id, vpc_id=vpc_id, region=region)

    cmd_args = ["create-vpc-firewall-cen-configure",
                "--cen-id", cen_id,
                "--network-instance-id", vpc_id,
                "--vpc-region", region,
                "--vpc-firewall-name", name,
                "--firewall-switch", args.firewall_switch,
                "--vswitch-id", vswitch_id,
                "--lang", "zh"]

    regional = []
    if first_in_region:
        regional_supplied = any([args.fw_vpc_cidr, args.fw_vswitch_cidr,
                                 args.fw_zone, args.fw_standby_zone])
        if regional_supplied:
            # The set is all-or-nothing. Accepting a partial one and sending only part
            # of it would silently discard a zone or CIDR the operator did supply.
            need(args.fw_vpc_cidr, "--fw-vpc-cidr",
                 "The regional parameters are all-or-nothing on a first access.")
            need(args.fw_vswitch_cidr, "--fw-vswitch-cidr",
                 "The regional parameters are all-or-nothing on a first access.")
            vpc_cidr, vsw_cidr = check_firewall_cidrs(args.fw_vpc_cidr,
                                                      args.fw_vswitch_cidr)
            if args.fw_zone or args.fw_standby_zone:
                need(args.fw_zone, "--fw-zone",
                     "Both zones are required together, and they must be a legal "
                     "pair from the zones subcommand.")
                need(args.fw_standby_zone, "--fw-standby-zone",
                     "Both zones are required together.")
                regional += ["--firewall-vpc-zone-id", args.fw_zone,
                             "--firewall-vpc-standby-zone-id", args.fw_standby_zone,
                             "--firewall-vswitch-zone-id", args.fw_zone]
            regional += ["--firewall-vpc-cidr-block", vpc_cidr,
                         "--firewall-vswitch-cidr-block", vsw_cidr]
        else:
            progress("first access in this region: no regional parameters supplied, "
                     "so the service will allocate the firewall VPC")
    else:
        regional_supplied = any([args.fw_vpc_cidr, args.fw_vswitch_cidr,
                                 args.fw_zone, args.fw_standby_zone])
        if regional_supplied:
            progress("AllowConfiguration=%s: the regional firewall VPC already "
                     "exists, so the regional parameters are ignored and are not "
                     "being sent" % allow)

    cmd_args += regional

    # Snapshot the stored task before mutating, so the poll can ignore it. Both
    # async results persist server-side and a naive poll reports the previous run's
    # finished status as instant success.
    prior_task_id = None
    if not cli.dry_run:
        ok, task = cli.cloudfw("describe-firewall-task", "--child-instance-id", vpc_id,
                               "--lang", "zh")
        if ok:
            prior_task_id = task.get("TaskId")
            progress("stored task before attach: %s (%s)"
                     % (prior_task_id, task.get("TaskStatus")))

    started = api_now_utc8()
    ok, resp = cli.cloudfw(*cmd_args, mutating=True)
    if not ok:
        report_api_error("create-vpc-firewall-cen-configure", resp)
    if cli.dry_run:
        emit({"ok": True, "dry_run": True, "slot_id": slot_id,
              "first_in_region": first_in_region,
              "AllowConfiguration": allow, "planned": resp.get("command")})
        return

    returned = resp.get("VpcFirewallId")
    progress("attach accepted, returned slot id %s" % returned)
    if returned and returned != slot_id:
        progress("WARNING: the returned slot id differs from the discovered one")

    task_result = wait_task(cli, vpc_id, prior_task_id, started)
    if not task_result.get("finished"):
        payload = {"ok": False, "stage": "task", "slot_id": slot_id,
                   "returned_slot_id": returned,
                   "first_in_region": first_in_region, "task": task_result}
        # The attach was accepted; only the polling did not confirm it. Reporting this
        # as a plain failure invites a repeat, which returns ErrorFirewallStatus.
        payload.update(unknown_outcome(slot_id, "task",
                                       "provisioning task not confirmed as finished"))
        payload["interpretation"] = (
            "The attach was accepted and provisioning is still running. This is not a "
            "confirmed failure. Recheck with the detail subcommand; do not re-issue "
            "the attach."
        )
        emit(payload)
        sys.exit(1)

    target = "opened" if args.firewall_switch == "open" else "closed"
    switch_result = wait_status(cli, slot_id, target,
                                TIMEOUT_SWITCH if target == "opened" else TIMEOUT_TASK,
                                cen_id, region)
    final = fetch_detail(cli, slot_id)
    summary = detail_summary(final)
    reached = bool(switch_result.get("reached"))
    eni_present = bool(summary["Eni"]["EniId"])
    ok_all = reached and eni_present
    if summary["Eni"]["EniVSwitchId"] and vswitch_id:
        summary["Eni"]["matches_requested_vswitch"] = (
            summary["Eni"]["EniVSwitchId"] == vswitch_id)
    payload = {
        "ok": bool(ok_all),
        "stage": "attached",
        "slot_id": slot_id,
        "returned_slot_id": returned,
        "first_in_region": first_in_region,
        "AllowConfiguration_before": allow,
        "task": task_result,
        "switch": switch_result,
        "detail": summary,
    }
    if not reached:
        # The task finished, so the attach itself is done; what is unconfirmed is the
        # diversion state. Re-attaching is the wrong response to that.
        payload.update({k: v for k, v in switch_result.items()
                        if k in ("mutation_sent", "outcome", "do_not_retry", "recheck")})
        payload["mutation_sent"] = True
        payload.setdefault("outcome", "unknown")
        payload["interpretation"] = (
            "Provisioning finished but the diversion state was not confirmed. The "
            "attach is not something to repeat: use the switch subcommand after "
            "rechecking."
        )
    elif not eni_present:
        # A different failure entirely: the slot did reach its target state, so there
        # is nothing left in flight and rechecking cannot change the answer. Reporting
        # this as unknown would send the caller round that loop.
        payload.update(incomplete_outcome(
            slot_id, "attached",
            "the slot reached '%s' but no diversion ENI exists in the business "
            "vSwitch, so traffic is not being inspected" % target,
            "Read the task steps in this payload, then list the network interfaces in "
            "the business VPC as shown in references/verification-method.md section "
            "2.3. Do not repeat the attach."))
        payload["interpretation"] = (
            "The diversion state is confirmed but the attach is incomplete. This is a "
            "definite negative, not an unconfirmed result: investigate the ENI rather "
            "than rechecking or retrying."
        )
    emit(payload)
    if not ok_all:
        sys.exit(1)


def wait_task(cli, vpc_id, prior_task_id, started):
    """Poll the provisioning task, ignoring the previously stored result."""
    deadline = time.time() + TIMEOUT_TASK
    polls = 0
    stale = 0
    t0 = time.time()
    seen_steps = None
    while time.time() < deadline:
        polls += 1
        ok, task = cli.cloudfw("describe-firewall-task", "--child-instance-id", vpc_id,
                               "--lang", "zh")
        if not ok:
            progress("task poll %d failed: %s"
                     % (polls, str(task.get("error", ""))[:120]))
            time.sleep(poll_interval(time.time() - t0))
            continue
        task_id = task.get("TaskId")
        status = task.get("TaskStatus")
        stamp = parse_ts(task.get("TaskStartTimestamp"))
        is_stale = (prior_task_id is not None and task_id == prior_task_id) or \
                   (stamp is not None and stamp < started - timedelta(seconds=5))
        if is_stale:
            stale += 1
            progress("task poll %d: stored task %s (%s) predates this call, ignoring"
                     % (polls, task_id, status))
            time.sleep(poll_interval(time.time() - t0))
            continue

        steps = {s.get("StepName"): s.get("StepStatus")
                 for s in task.get("TaskSteps") or []}
        if steps != seen_steps:
            seen_steps = steps
            progress("task %s %s %s" % (task_id, status, json.dumps(
                steps, ensure_ascii=False)))
        if status == "finished":
            return {"finished": True, "TaskId": task_id, "polls": polls,
                    "stale_reads_ignored": stale,
                    "seconds": round(time.time() - t0), "steps": steps}
        if status in ("failed", "error"):
            return {"finished": False, "TaskId": task_id, "TaskStatus": status,
                    "polls": polls, "stale_reads_ignored": stale,
                    "seconds": round(time.time() - t0), "steps": steps,
                    "raw": task}
        time.sleep(poll_interval(time.time() - t0))
    return {"finished": False, "timed_out": True, "polls": polls,
            "stale_reads_ignored": stale, "seconds": round(time.time() - t0),
            "timeout": TIMEOUT_TASK,
            "hint": "The attach was accepted. A timeout here means provisioning is "
                    "unconfirmed, not that it failed. The official guide allows "
                    "around 5 minutes for creation. Recheck with the detail "
                    "subcommand rather than re-issuing the attach."}


# ---------------------------------------------------------------------------
# switch
# ---------------------------------------------------------------------------
def cmd_switch(cli, args):
    slot_id = check_id(args.slot_id, "--slot-id", "vfw-")
    want = args.switch
    target = "opened" if want == "open" else "closed"
    already = "opened" if want == "close" else "closed"

    read_ok, status = current_status(cli, slot_id, args.cen_id, args.region)
    if not read_ok:
        report_read_failure("describe-vpc-firewall-cen-list", status)
    if status is None:
        fail("Slot %s was not found among the Basic-edition slots." % slot_id,
             slot_id=slot_id,
             hint="Confirm the id with the list subcommand. A nonexistent slot id "
                  "produces ErrorVpcFirewallExist, whose message wrongly claims the "
                  "firewall is already configured.")
    if status == target:
        # No consent is asked for here on purpose: this invocation changes nothing, and
        # demanding --yes for a no-op is how the flag stops meaning anything.
        emit({"ok": True, "skipped": True, "slot_id": slot_id, "status": status,
              "reason": "already in the requested state; no call was made because "
                        "repeating it returns an error rather than a no-op"})
        return
    if status not in STEADY:
        fail("Slot %s is in transient state '%s'; wait for it to settle before "
             "switching." % (slot_id, status), slot_id=slot_id, status=status)
    if status == "notconfigured":
        fail("Slot %s is notconfigured, so there is nothing to switch. Attach the "
             "VPC first." % slot_id, slot_id=slot_id, status=status)

    # Past every guard that could still turn this into a no-op, so the gate now fires
    # only on a run that really will send the write.
    require_consent(cli, args, "switching diversion to '%s'" % want, [
        "established long-lived connections flap for sub-second intervals;",
        "    short connections are unaffected",
        "SLB and RDS sessions can drop, so a low-traffic window is advised",
        "the operation cannot be paused or rolled back; on failure the",
        "    service rolls back by itself",
        "the official guide allows 5 to 30 minutes depending on route",
        "    entry count",
    ], slot_id=slot_id, requested=want, from_status=status)

    if status != already:
        progress("slot is '%s', requesting '%s'" % (status, want))

    ok, resp = cli.cloudfw("modify-vpc-firewall-cen-switch-status",
                           "--vpc-firewall-id", slot_id,
                           "--firewall-switch", want, "--lang", "zh", mutating=True)
    if not ok:
        report_api_error("modify-vpc-firewall-cen-switch-status", resp)
    if cli.dry_run:
        emit({"ok": True, "dry_run": True, "slot_id": slot_id,
              "from_status": status, "requested": want,
              "planned": resp.get("command")})
        return

    progress("switch request accepted, polling for '%s'" % target)
    result = wait_status(cli, slot_id, target, TIMEOUT_SWITCH, args.cen_id, args.region)
    payload = {"ok": bool(result.get("reached")), "stage": "switch",
               "slot_id": slot_id, "from_status": status, "requested": want,
               "target": target, "result": result}
    if not result.get("reached"):
        # The write is in flight. Surfacing this as a bare failure invites the caller
        # to repeat it, which is the one thing that must not happen here.
        payload.update({k: v for k, v in result.items()
                        if k in ("mutation_sent", "outcome", "do_not_retry", "recheck")})
        payload["interpretation"] = (
            "Diversion was requested and is still being applied. This is not a "
            "confirmed failure. Recheck the slot; do not re-issue the switch."
        )
    emit(payload)
    if not result.get("reached"):
        sys.exit(1)


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------
def cmd_rename(cli, args):
    slot_id = check_id(args.slot_id, "--slot-id", "vfw-")
    name = check_name(args.name)

    read_ok, status = current_status(cli, slot_id, args.cen_id, args.region)
    if not read_ok:
        report_read_failure("describe-vpc-firewall-cen-list", status)
    if status is None:
        fail("Slot %s was not found among the Basic-edition slots." % slot_id,
             slot_id=slot_id)
    if status == "notconfigured":
        fail("Slot %s is notconfigured, so it cannot be renamed; the service "
             "returns ErrorFirewallStatusCannotModify." % slot_id,
             slot_id=slot_id, status=status)

    ok, resp = cli.cloudfw("modify-vpc-firewall-cen-configure",
                           "--vpc-firewall-id", slot_id,
                           "--vpc-firewall-name", name, "--lang", "zh", mutating=True)
    if not ok:
        report_api_error("modify-vpc-firewall-cen-configure", resp)
    if cli.dry_run:
        emit({"ok": True, "dry_run": True, "slot_id": slot_id, "name": name,
              "planned": resp.get("command")})
        return

    detail = detail_summary(fetch_detail(cli, slot_id))
    applied = detail.get("VpcFirewallName") == name
    emit({"ok": applied, "stage": "rename", "slot_id": slot_id,
          "requested_name": name, "current_name": detail.get("VpcFirewallName"),
          "note": "Rename is the only editable field. The firewall VPC CIDR, "
                  "vSwitch CIDRs, zones and business vSwitch cannot be changed "
                  "after creation."})
    if not applied:
        sys.exit(1)


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------
def cmd_remove(cli, args):
    slot_id = check_id(args.slot_id, "--slot-id", "vfw-")

    rows, _, _, _ = fetch_slots(cli, args.cen_id, args.region)
    target_row = None
    for row in rows:
        if row.get("VpcFirewallId") == slot_id:
            target_row = row
            break
    if target_row is None:
        fail("Slot %s was not found among the Basic-edition slots." % slot_id,
             slot_id=slot_id)

    status = target_row.get("FirewallSwitchStatus")
    if status == "notconfigured":
        # Already in the end state, so no consent is asked for and no call is made.
        emit({"ok": True, "skipped": True, "slot_id": slot_id, "status": status,
              "reason": "already removed; repeating the call returns -360134"})
        return
    if status in TRANSIENT:
        fail("Slot %s is in transient state '%s'; wait for it to settle."
             % (slot_id, status), slot_id=slot_id, status=status)

    # Protective pre-check. Removing the last access in a region also destroys the
    # shared firewall VPC, which is a wider blast radius than one VPC.
    local = target_row.get("LocalVpc") or {}
    region = local.get("RegionNo")
    cen_id = target_row.get("CenId")

    # The region has to be read before the lock can be keyed on it, so the list above is
    # only used for that. Everything the removal decision rests on is read again below,
    # under the lock: serialising the writes is not enough on its own, because a sibling
    # removed between that read and this lock would leave this run believing it is not
    # the last in the region and skipping the teardown warning entirely.
    acquire_region_lock(cli, region)

    rows, _, _, _ = fetch_slots(cli, args.cen_id, args.region)
    target_row = next((r for r in rows if r.get("VpcFirewallId") == slot_id), None)
    if target_row is None:
        # Gone from the list while this run was waiting. That is a removal end state, so
        # it is reported the same way as finding it already reset.
        emit({"ok": True, "skipped": True, "slot_id": slot_id, "status": "absent",
              "reason": "the slot left the list while this run waited for the regional "
                        "write lock, which is a removal end state"})
        return
    status = target_row.get("FirewallSwitchStatus")
    if status == "notconfigured":
        emit({"ok": True, "skipped": True, "slot_id": slot_id, "status": status,
              "reason": "another run removed it while this one waited for the regional "
                        "write lock"})
        return
    if status in TRANSIENT:
        fail("Slot %s moved to transient state '%s' while this run waited for the "
             "regional write lock; wait for it to settle." % (slot_id, status),
             slot_id=slot_id, status=status)

    siblings = [r for r in rows
                if r.get("VpcFirewallId") != slot_id
                and (r.get("LocalVpc") or {}).get("RegionNo") == region
                and r.get("FirewallSwitchStatus") != "notconfigured"]
    last_in_region = not siblings

    if status == "opened":
        diag("NOTE: slot is 'opened'. Closing diversion before removal is the path "
             "that has been verified; removing straight from 'opened' has not been.")
        if not args.force_open:
            fail("Slot %s is opened. Close diversion first, or pass "
                 "--force-open to remove directly (unverified path)." % slot_id,
                 slot_id=slot_id, status=status)

    # Unconditional: removal destroys a working configuration, and putting it back
    # means a fresh attach plus an open, which flaps connections again. last_in_region
    # widens the warning rather than being the thing that triggers it.
    bullets = [
        "the diversion ENI in the business vSwitch is deleted and traffic stops",
        "    being inspected for this VPC",
        "the configuration is destroyed, not disabled: the firewall VPC CIDR,",
        "    vSwitch CIDRs, zone pair and business vSwitch all have to be supplied",
        "    again on the next attach",
        "this slot currently protects traffic in state '%s'" % status,
    ]
    if last_in_region:
        bullets += [
            "THIS IS THE LAST configured slot in %s for %s" % (region, cen_id),
            "removing it also destroys the shared regional firewall VPC",
            "    (Cloud_Firewall_VPC), its vSwitch and its security group, so the",
            "    next attachment in this region has to recreate all of them",
        ]
    require_consent(cli, args, "removing VPC access for slot %s" % slot_id, bullets,
                    slot_id=slot_id, region=region, cen_id=cen_id,
                    from_status=status, last_in_region=last_in_region)

    ok, resp = cli.cloudfw("delete-vpc-firewall-cen-configure",
                           "--vpc-firewall-id-list", slot_id, "--lang", "zh",
                           mutating=True)
    if not ok:
        report_api_error("delete-vpc-firewall-cen-configure", resp)
    if cli.dry_run:
        emit({"ok": True, "dry_run": True, "slot_id": slot_id,
              "from_status": status, "last_in_region": last_in_region,
              "planned": resp.get("command")})
        return

    progress("removal accepted, polling for 'notconfigured'")
    result = wait_status(cli, slot_id, "notconfigured", TIMEOUT_REMOVE,
                         cen_id, region, absent_is_success=True)
    payload = {"ok": False, "stage": "remove",
               "slot_id": slot_id, "from_status": status,
               "last_in_region": last_in_region, "result": result}
    if result.get("reached"):
        if result.get("status") == "absent":
            # Nothing is left to read. Asking for detail on an id that is no longer
            # listed answers 400 ErrorVpcFirewallExist, whose message claims the
            # firewall already exists, and that hard error would report a successful
            # removal as a failure. Absence is the stronger reset evidence anyway.
            payload["reset_confirmed"] = {"slot_absent": True}
            payload["note"] = (
                "The slot left the list rather than resetting to notconfigured. Both "
                "are removal end states; this one leaves nothing to read back."
            )
            reset_ok = True
        else:
            detail = detail_summary(fetch_detail(cli, slot_id))
            payload["detail"] = detail
            # A slot owns its name and diversion ENI, but FirewallVpc is shared by
            # every configured slot in the same CEN/region.  Requiring the shared VPC
            # to disappear after a non-last removal turns a confirmed teardown into a
            # false failure: the VPC must remain while siblings still use it.
            # AllowConfiguration is likewise a value, not a claim: it returns to 1
            # only when the region was released.
            checks = {
                "status_notconfigured": detail.get("FirewallSwitchStatus") == "notconfigured",
                "eni_cleared": not detail["Eni"]["EniId"],
                "name_cleared": not detail.get("VpcFirewallName"),
            }
            firewall_vpc_cleared = not detail["FirewallVpc"]["VpcId"]
            if last_in_region:
                checks["firewall_vpc_cleared"] = firewall_vpc_cleared
            # detail_summary flattens AllowConfiguration to the top level even though
            # the raw API nests it under FirewallVpc, so reading it from the nested dict
            # here raises KeyError on every successful removal.
            payload["reset_confirmed"] = dict(checks, allow_configuration=detail.get("AllowConfiguration"))
            if not last_in_region:
                payload["reset_confirmed"]["firewall_vpc_retained"] = not firewall_vpc_cleared
            reset_ok = all(checks.values())
            payload["note"] = (
                "The slot id still appears in the list. Removal resets a slot, it does "
                "not delete it, so TotalCount is unchanged. DefendCidrList also still "
                "holds values because it reflects the business VPC's own routing."
            )
        # Reaching notconfigured is necessary but not sufficient. A slot can report the
        # reset state while still holding an ENI, and calling that success would tell
        # the caller traffic had stopped being diverted when it had not.
        payload["ok"] = reset_ok
        if last_in_region:
            payload["regional_teardown"] = verify_regional_teardown(cli, region, cen_id)
        if not reset_ok:
            failed = [k for k, v in checks.items() if v is False]
            payload.update(incomplete_outcome(
                slot_id, "remove",
                "the slot reported the reset state but these checks did not pass: %s"
                % ", ".join(failed),
                "Re-read the slot with the detail subcommand and list the network "
                "interfaces in the business VPC. Do not repeat the delete: it answers "
                "-360134 once the slot is already notconfigured."))
            payload["interpretation"] = (
                "Removal completed as a state transition but the teardown is not "
                "fully confirmed. Traffic may still reach a residual ENI, so treat "
                "this as unfinished rather than as done."
            )
    else:
        payload.update({k: v for k, v in result.items()
                        if k in ("mutation_sent", "outcome", "do_not_retry", "recheck")})
        payload["interpretation"] = (
            "Removal was accepted and is still being applied. This is not a confirmed "
            "failure, and repeating the delete returns -360134. Recheck the slot."
        )
    emit(payload)
    if not payload["ok"]:
        sys.exit(1)


def verify_regional_teardown(cli, region, cen_id):
    """Confirm the shared regional resources are gone, by their fixed names.

    Matching on Cloud_Firewall_VPC is more reliable than matching on a CIDR,
    because the name is assigned by the service rather than chosen by the operator.
    """
    out = {"region": region, "cen_id": cen_id}
    ok, resp = cli.vpc("describe-vpcs", "--biz-region-id", region, "--page-size", "50")
    if not ok:
        out["vpc_check"] = "unavailable: %s" % str(resp.get("error", ""))[:160]
        return out
    if "TotalCount" not in resp:
        out["vpc_check"] = ("unavailable: response has no TotalCount, so the region "
                            "flag was probably wrong (vpc and ecs use --biz-region-id)")
        return out
    names = [v.get("VpcName") for v in (resp.get("Vpcs") or {}).get("Vpc") or []]
    out["firewall_vpc_still_present"] = "Cloud_Firewall_VPC" in names
    out["vpc_count_in_region"] = resp.get("TotalCount")
    return out


# ---------------------------------------------------------------------------
# zones
# ---------------------------------------------------------------------------
def zone_pairs(raw):
    """Flatten ZoneList entries into [primary, standby] id pairs.

    Each entry is a two-element list of objects carrying LocalName and ZoneId, and
    each pair is a legal primary and standby combination. The order of the pairs
    differs between calls, so never select one by position.
    """
    pairs = []
    for entry in raw or []:
        ids = [z.get("ZoneId") for z in entry if isinstance(z, dict)]
        if len(ids) == 2:
            pairs.append({"primary": ids[0], "standby": ids[1]})
    return pairs


def cmd_zones(cli, args):
    region = check_region(args.region)
    payload = {"region": region}

    ok, resp = cli.cloudfw("describe-vpc-firewall-zone", "--region-no", region,
                           "--lang", "zh")
    if ok:
        payload["firewall_zone_pairs"] = zone_pairs(resp.get("ZoneList"))
        payload["pair_note"] = (
            "Each entry is a legal primary and standby pairing. Do not compose a "
            "pair from two independent choices, and do not rely on the order: it "
            "differs between calls. Leaving both zones unset selects dual-active "
            "mode; naming both selects active-standby mode, which lowers latency."
        )
    else:
        payload["firewall_zone_pairs_error"] = str(resp.get("error", ""))[:200]

    if args.cen_id:
        ok, resp = cli.cloudfw("describe-vpc-firewall-zone", "--region-no", region,
                               "--cen-id", check_id(args.cen_id, "--cen-id", "cen-"),
                               "--lang", "zh")
        if ok:
            payload["firewall_zone_pairs_cen_scoped"] = zone_pairs(
                resp.get("ZoneList"))

    ok, resp = cli.cloudfw("describe-vpc-zone", "--region-no", region,
                           "--environment", "VPC", "--lang", "zh")
    if ok:
        payload["business_vpc_zones"] = [z.get("ZoneId")
                                         for z in resp.get("ZoneList") or []]
        payload["business_zone_note"] = (
            "For choosing the business vSwitch that will host the diversion ENI. "
            "The guide recommends the same zone as the firewall vSwitch primary "
            "zone, to reduce latency."
        )
    else:
        payload["business_vpc_zones_error"] = str(resp.get("error", ""))[:200]

    emit(payload)


# ---------------------------------------------------------------------------
# simple reads
# ---------------------------------------------------------------------------
def cmd_list(cli, args):
    cen_id = check_id(args.cen_id, "--cen-id", "cen-") if args.cen_id else None
    region = check_region(args.region) if args.region else None
    rows, skipped, total, _ = fetch_slots(cli, cen_id, region)
    summaries = [slot_summary(r) for r in rows]
    if args.status:
        summaries = [s for s in summaries if s["FirewallSwitchStatus"] == args.status]
    emit({
        "ok": True,
        "cen_id": cen_id,
        "region": region,
        "basic_slot_count": len(summaries),
        "total_returned_by_api": total,
        "non_basic_dropped": skipped,
        "slots": summaries,
        "note": "A slot is the stable identity of a (CEN, attached VPC) pair. An "
                "unprotected VPC appears as notconfigured, and removal resets a "
                "slot rather than deleting it, so the count does not change.",
    })


def cmd_detail(cli, args):
    slot_id = check_id(args.slot_id, "--slot-id", "vfw-") if args.slot_id else None
    vpc_id = check_id(args.vpc_id, "--vpc-id", "vpc-") if args.vpc_id else None
    if not slot_id and not vpc_id:
        fail("pass --slot-id or --vpc-id")

    if slot_id:
        # Confirm the slot is Basic before trusting the detail response, because the
        # detail call itself applies no edition filter.
        rows, _, _, _ = fetch_slots(cli, args.cen_id, args.region)
        if not any(r.get("VpcFirewallId") == slot_id for r in rows):
            fail("Slot %s is not among the Basic-edition slots." % slot_id,
                 slot_id=slot_id,
                 hint="It may belong to another edition, or the id may not exist.")
    else:
        slot = find_slot(cli, cen_id=args.cen_id, region=args.region, vpc_id=vpc_id)
        slot_id = slot.get("VpcFirewallId")

    detail = fetch_detail(cli, slot_id)
    summary = detail_summary(detail)
    summary["ok"] = True
    summary["interpretation"] = {
        "first_in_region": summary["AllowConfiguration"] == 1,
        "regional_firewall_vpc_exists": bool(summary["FirewallVpc"]["VpcId"]),
        "diversion_eni_exists": bool(summary["Eni"]["EniId"]),
        "manual_route_mode_supported": summary["LocalVpc"]["SupportManualMode"] == 1,
    }
    emit(summary)


def cmd_precheck(cli, args):
    cen_id = check_id(args.cen_id, "--cen-id", "cen-")
    vpc_id = check_id(args.vpc_id, "--vpc-id", "vpc-")
    region = check_region(args.region)
    result = run_precheck(cli, cen_id, vpc_id, region, wait=not args.no_wait)
    if result.get("PrecheckStatus") == "failed":
        result["offending_resources"] = resolve_route_tables(cli, region, vpc_id)
        result["note"] = (
            "A failing entity names no resource, so the Suggestion text alone is "
            "not actionable. offending_resources resolves the custom route table "
            "case locally. Whether a failed verdict blocks attachment is "
            "unconfirmed; treat it as blocking and ask the user before proceeding."
        )
    emit(result)
    if not result.get("ok"):
        sys.exit(1)


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cfw_cen_basic.py",
        description="Manage Cloud Firewall VPC border firewalls on CEN Basic "
                    "Edition. Data on stdout, diagnostics on stderr.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Set SKILL_SESSION_ID to a 32-character lowercase hex id, generated "
               "once per session and reused for every command.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the write calls instead of sending them; reads "
                             "still execute so the plan reflects real state")
    sub = parser.add_subparsers(dest="command", required=True)

    def common_identity(p):
        p.add_argument("--cen-id", help="CEN instance id, cen-xxxx")
        p.add_argument("--region", help="region id, for example cn-shanghai")

    p = sub.add_parser("list", help="list Basic-edition slots")
    common_identity(p)
    p.add_argument("--status", choices=STEADY + TRANSIENT,
                   help="keep only slots in this state")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("detail", help="read one slot in full")
    common_identity(p)
    p.add_argument("--slot-id", help="vfw-xxxx")
    p.add_argument("--vpc-id", help="vpc-xxxx, resolved to its slot")
    p.set_defaults(func=cmd_detail)

    p = sub.add_parser("precheck", help="run the pre-access check and wait")
    p.add_argument("--cen-id", required=True)
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--no-wait", action="store_true",
                   help="issue the check and return without polling")
    p.set_defaults(func=cmd_precheck)

    p = sub.add_parser("attach", help="configure VPC access")
    p.add_argument("--cen-id", required=True)
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--name", required=True, help="firewall name, at most 128 chars")
    p.add_argument("--vswitch-id", required=True,
                   help="business vSwitch that will host the diversion ENI")
    p.add_argument("--firewall-switch", choices=["open", "close"], default="close",
                   help="close attaches dormant, open also starts diversion")
    p.add_argument("--fw-vpc-cidr",
                   help="regional, first access only; 10.0.0.0/8, 172.16.0.0/12, "
                        "192.168.0.0/16 or a subnet of one")
    p.add_argument("--fw-vswitch-cidr",
                   help="regional, first access only; must be a subnet of --fw-vpc-cidr")
    p.add_argument("--fw-zone", help="regional, primary zone from a legal pair")
    p.add_argument("--fw-standby-zone", help="regional, standby zone from the same pair")
    p.add_argument("--yes", action="store_true",
                   help="required with --firewall-switch open: confirms the user has "
                        "been told about connection flapping")
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("switch", help="open or close diversion")
    common_identity(p)
    p.add_argument("--slot-id", required=True)
    p.add_argument("--switch", required=True, choices=["open", "close"])
    p.add_argument("--yes", action="store_true",
                   help="confirm the user has been told about connection flapping")
    p.set_defaults(func=cmd_switch)

    p = sub.add_parser("rename", help="rename a firewall, the only editable field")
    common_identity(p)
    p.add_argument("--slot-id", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("remove", help="remove VPC access")
    common_identity(p)
    p.add_argument("--slot-id", required=True)
    p.add_argument("--yes", action="store_true",
                   help="confirm the user has been told about the regional teardown")
    p.add_argument("--force-open", action="store_true",
                   help="remove straight from the opened state, which is unverified")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("zones", help="list legal firewall zone pairs and business zones")
    p.add_argument("--region", required=True)
    p.add_argument("--cen-id", help="also query the CEN-scoped pair list")
    p.set_defaults(func=cmd_zones)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    session_id = resolve_session_id(os.environ.get("SKILL_SESSION_ID"))
    skill_version = load_skill_version()
    cli = Cli(session_id, skill_version, dry_run=getattr(args, "dry_run", False))
    diag("session-id=%s skill-version=%s%s"
         % (session_id, skill_version, " (dry run)" if cli.dry_run else ""))

    args.func(cli, args)
    if cli.dry_run and cli.planned:
        diag("planned mutating calls that were NOT sent: %d" % len(cli.planned))
    diag("cloud API calls made: %d" % cli.calls)


if __name__ == "__main__":
    main()
