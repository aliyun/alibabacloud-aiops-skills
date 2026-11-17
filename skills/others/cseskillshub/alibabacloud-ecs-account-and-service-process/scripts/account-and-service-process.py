#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified entry for account-and-service-process: dispatch --axis <name> to that axis's original
entry script under scripts/axes/, passing through all remaining argv verbatim.
Per-axis behaviour/contract lives in references/axes/<name>.md (SKILL.md index).

Two guardrails run before the axis does (see _guardrails.py):

  * In-guest (Cloud Assistant `RunCommand`) reads are OFF by default. Without
    `--allow-guest-read` the axis's guest-activation flags are stripped and a
    `CONSENT-REQUIRED:` notice is printed; cloud-side reads still run, so a
    forgotten consent degrades the answer instead of blocking it.
  * A credential-class failure ends the run with `CREDENTIAL-FAIL-CLOSED:` and
    exit 3, listing the checks the customer can run. This script never reads
    `~/.aliyun/config.json` or the ALIBABACLOUD_* environment variables.
"""
import argparse
import json
import os
import subprocess
import sys

import _guardrails as g

AXES = {
 "swas-boundary-guide": "axes/swas_boundary_guide/swas_boundary_guide.py",
 "account-transfer-guide": "axes/account_transfer_guide/transfer_guide.py",
 "business-contact-routing": "axes/business_contact_routing/routing.py",
 "invalid-ticket-triage": "axes/invalid_ticket_triage/triage_invalid_ticket.py",
 "instance-tag-metadata-guide": "axes/instance_tag_metadata_guide/ecs_instance_tag_metadata_check.py"
}

# Axes that can deliver a command into the customer's instance, and the flags that
# activate that delivery. Evidence-derived: only axes whose entry script really
# dispatches through Cloud Assistant are listed; every other axis has no guest channel.
GUEST_ACTIVATION = {}
HERE = os.path.dirname(os.path.abspath(__file__))


# --- release-side versioned User-Agent (static rule UA-SKILL-VERSION) ---
import json as _json


def _skill_version_from_manifest():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "manifest.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return _json.load(fh)["version"]
    except Exception:
        return "0.0.0"


SKILL_UA = ("AlibabaCloud-Agent-Skills/alibabacloud-ecs-account-and-service-process/{session-id} "
            "skill-version/" + _skill_version_from_manifest())
# --- end versioned UA ---


REGION_FLAGS = ('--region-id', '--region', '--region_id', '--RegionId')


def region_from_argv(rest):
    """The region this run was pointed at, under any of its spellings."""
    argv = list(rest or [])
    for index, tok in enumerate(argv):
        if tok.split('=', 1)[0] not in REGION_FLAGS:
            continue
        if '=' in tok:
            return tok.split('=', 1)[1] or None
        nxt = argv[index + 1] if index + 1 < len(argv) else None
        return nxt if (nxt and not nxt.startswith('-')) else None
    return None


OFFER_PAGE_SIZE = 50
OFFER_MAX_PAGES = 4
SWEEP_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-qingdao",
    "cn-zhangjiakou", "cn-huhehaote", "cn-wulanchabu", "cn-heyuan",
    "cn-guangzhou", "cn-shenzhen", "cn-chengdu", "cn-nanjing",
    "cn-fuzhou", "cn-wuhan-lr", "cn-hongkong", "ap-northeast-1",
    "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
    "ap-southeast-3", "ap-southeast-5", "ap-southeast-6",
    "ap-southeast-7", "us-east-1", "us-west-1", "eu-central-1",
    "eu-west-1", "me-east-1", "me-central-1",
]
SWEEP_CALL_TIMEOUT = 15
SIGHTING_BUDGET_S = 120.0


def instance_candidates(region, env=None):
    """One bounded read-only DescribeInstances listing for the offer block.

    Returns (rows, state, denial_line, meta); a missing CLI, a timeout, a refusal or an
    unreadable body is reported as a list that could not be read, never as an
    account with nothing in it. `meta` says whether the listing stayed inside the
    first pages, so a big account is counted honestly instead of silently cut.
    """
    rows = []
    total_count = None
    partial = False
    page = 1
    while page <= OFFER_MAX_PAGES:
        cmd = ['aliyun', 'ecs', 'DescribeInstances', '--PageSize', str(OFFER_PAGE_SIZE),
               '--PageNumber', str(page), '--user-agent', SKILL_UA]
        if region:
            cmd += ['--RegionId', region]
        try:
            proc = subprocess.run(cmd, timeout=60, env=env,
                                  stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError):
            return rows, ('candidates' if rows else 'unavailable'), None, \
                   {"partial": bool(rows), "total": total_count}
        if proc.returncode != 0:
            denial = None
            low = (proc.stderr or b'').decode('utf-8', 'replace').lower()
            if 'nopermission' in low or 'implicitdeny' in low or 'forbidden.ram' in low:
                denial = ('The candidate list itself was refused (permission gap): grant '
                          'ecs:DescribeInstances to the identity in use using the statement '
                          'in references/ram-policies.md, then re-run.')
            return rows, ('candidates' if rows else 'unavailable'), denial, \
                   {"partial": False, "total": total_count}
        text = (proc.stdout or b'').decode('utf-8', 'replace')
        offsets = [index for index in (text.find('{'), text.find('[')) if index != -1]
        if not offsets:
            return rows, 'unavailable', None, {"partial": False, "total": None}
        try:
            body = json.JSONDecoder().raw_decode(text[min(offsets):])[0]
        except ValueError:
            return rows, 'unavailable', None, {"partial": False, "total": None}
        if isinstance(body, dict) and total_count is None:
            try:
                total_count = int(body.get('TotalCount') or 0) or None
            except (TypeError, ValueError):
                total_count = None
        instances = (body.get('Instances', {}).get('Instance', [])
                     if isinstance(body, dict) else [])
        found = 0
        for row in instances or []:
            if not isinstance(row, dict):
                continue
            ident = str(row.get('InstanceId') or '').strip()
            if not ident:
                continue
            rows.append('%s (%s, %s)' % (ident, row.get('InstanceName') or '-',
                                         row.get('Status') or '-'))
            found += 1
        if found < OFFER_PAGE_SIZE:
            break
        page += 1
        partial = page > OFFER_MAX_PAGES
    return rows, ('candidates' if rows else 'empty'), None, \
           {"partial": partial, "total": total_count}


def target_id_from_argv(rest):
    """The instance id this run was pointed at, under its common spellings."""
    argv = list(rest or [])
    for index, tok in enumerate(argv):
        head = tok.split('=', 1)[0]
        if head not in ('--instance-id', '--instance-ids'):
            continue
        if '=' in tok:
            val = tok.split('=', 1)[1]
        else:
            nxt = argv[index + 1] if index + 1 < len(argv) else ''
            val = nxt if (nxt and not nxt.startswith('-')) else ''
        val = (val or '').strip()
        if not val:
            continue
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list) and parsed:
                return str(parsed[0]).strip() or None
            if isinstance(parsed, str):
                return parsed.strip() or None
        except ValueError:
            pass
        cleaned = val.strip().strip('[]').strip()
        first = cleaned.split(',')[0].strip().strip('"').strip("'")
        return first or None
    return None


def instance_sightings(target_id, env=None, budget_s=SIGHTING_BUDGET_S):
    """Bounded existence check for one instance id over the built-in region list.

    Mirrors the core package's sweep discipline: a fixed list, per-region
    filtered reads, and an honest statement that regions outside the list were
    not covered. It answers only "where can this credential read that id"; it
    never moves the diagnosis target. Returns (found_region, scanned,
    regions_total, stop_reason); a stopped sweep says not-checked, never not-found.
    """
    import time
    deadline = time.time() + budget_s
    scanned = 0
    for region in SWEEP_REGIONS:
        if time.time() > deadline:
            return None, scanned, len(SWEEP_REGIONS), 'the sweep time budget ran out'
        probe = ['aliyun', 'ecs', 'DescribeInstances', '--RegionId', region,
                 '--InstanceIds', json.dumps([target_id]), '--PageSize', '10',
                 '--user-agent', SKILL_UA]
        try:
            proc = subprocess.run(probe, timeout=SWEEP_CALL_TIMEOUT, env=env,
                                  stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError):
            continue
        scanned += 1
        if proc.returncode != 0:
            low = (proc.stderr or b'').decode('utf-8', 'replace').lower()
            if ('nopermission' in low or 'implicitdeny' in low
                    or 'forbidden.ram' in low):
                return None, scanned, len(SWEEP_REGIONS), \
                    'the identity in use was refused mid-sweep'
            continue
        out = (proc.stdout or b'').decode('utf-8', 'replace')
        offs = [i for i in (out.find('{'), out.find('[')) if i != -1]
        if not offs:
            continue
        try:
            body = json.JSONDecoder().raw_decode(out[min(offs):])[0]
        except ValueError:
            continue
        for row in (body.get('Instances', {}).get('Instance', [])
                    if isinstance(body, dict) else []):
            if isinstance(row, dict) and str(row.get('InstanceId') or '') == target_id:
                return region, scanned, len(SWEEP_REGIONS), None
    return None, scanned, len(SWEEP_REGIONS), None

_AXIS_PROBE = r"""
import importlib.util
import json
import os
import sys

axis_dir, package = sys.argv[1], sys.argv[2]
sys.path.insert(0, axis_dir)
spec = importlib.util.spec_from_file_location("selftest_cli", os.path.join(axis_dir, "_cli.py"))
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
problems = []
session = "0123456789abcdef0123456789abcdef"
builder = (getattr(cli, "build_user_agent", None) or getattr(cli, "user_agent", None)
           or getattr(cli, "user_agent_for", None))
ua = ""
try:
    if builder is not None:
        try:
            ua = builder(session)
        except TypeError:
            ua = builder()
except Exception as exc:
    problems.append("ua-error:%r" % exc)
manifest_path = os.path.normpath(os.path.join(axis_dir, "..", "..", "..", "references", "manifest.json"))
version = None
try:
    with open(manifest_path, encoding="utf-8") as fh:
        version = json.load(fh)["version"]
except Exception:
    problems.append("manifest-unreadable")
if package not in ua or not version or ("skill-version/" + version) not in ua:
    problems.append("ua-shape:%s" % ua)
notice = 'Notice: plugin auto-installed\n{"RequestId": "x", "Ok": true}'
decoder = getattr(cli, "_json_body", None)
try:
    if decoder is not None:
        payload = decoder(notice)
    elif hasattr(cli, "_parse_body"):
        payload = cli._parse_body(notice, "probe", "ProbeAction")
    elif hasattr(cli, "parse_payload"):
        payload = cli.parse_payload(notice, "probe", "ProbeAction")
    else:
        payload = None
        problems.append("no-tolerant-decoder")
    if payload is not None and not payload.get("Ok"):
        problems.append("json-notice-wrong")
except Exception as exc:
    problems.append("json-notice-error:%r" % exc)
retry = getattr(cli, "_region_flag_retry", None)
if retry is None:
    problems.append("no-region-retry")
else:
    cmd = ["aliyun", "ecs", "DescribeDisks", "--RegionId", "cn-hangzhou"]
    out = retry(cmd, "ERROR: missing required parameter(s): --biz-region-id", "cn-hangzhou")
    if out is None or out[-2:] != ["--biz-region-id", "cn-hangzhou"]:
        problems.append("region-retry-wrong")
if not hasattr(cli, "_with_auto_plugin"):
    problems.append("no-auto-plugin")
print(json.dumps({"problems": problems}))
"""

def selftest():
    """Offline gate checks: dispatcher survival, consent, credential fail-closed,
    answer scrubs, and per-axis transport (UA / JSON notice / region retry / plugin).
    No cloud call is made and no credential file is read."""
    import json
    import subprocess
    failures = []
    total = 0

    def check(name, ok, detail=""):
        nonlocal total
        total += 1
        suffix = (" - " + detail) if not ok and detail else ""
        print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, suffix), flush=True)
        if not ok:
            failures.append(name)

    package = os.path.basename(os.path.dirname(HERE))
    for axis, rel in sorted(AXES.items()):
        entry = os.path.join(HERE, rel)
        check("entry-exists " + axis, os.path.isfile(entry), entry)
        try:
            proc = subprocess.run([sys.executable, entry, "--help"],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=60)
            check("help-rc0 " + axis, proc.returncode == 0, "rc=%s" % proc.returncode)
        except (OSError, subprocess.SubprocessError) as exc:
            check("help-rc0 " + axis, False, repr(exc))
        axis_dir = os.path.dirname(entry)
        try:
            proc = subprocess.run([sys.executable, "-c", _AXIS_PROBE, axis_dir, package],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=60)
            out = proc.stdout.decode("utf-8", "replace").strip()
            report = json.loads(out.splitlines()[-1])
            problems = report.get("problems") or []
            check("transport " + axis, proc.returncode == 0 and not problems,
                  ";".join(problems) or proc.stderr.decode("utf-8", "replace")[-200:])
        except (OSError, subprocess.SubprocessError, ValueError, IndexError) as exc:
            check("transport " + axis, False, repr(exc))

    activation = next((flags for flags in GUEST_ACTIVATION.values() if flags), ("--confirm",))
    flag = activation[0]
    gated, dropped = g.gate_guest_flags([flag, "target-value", "--keep", "x"], activation, False)
    check("consent-strip", flag not in gated and dropped == [flag] and "--keep" in gated)
    granted_gate, granted_dropped = g.gate_guest_flags([flag, "target-value"], activation, True)
    check("consent-granted-keeps", flag in granted_gate and not granted_dropped)
    rest, granted = g.parse_consent([g.CONSENT_FLAG, "--other"], granted=False, environ={})
    check("consent-flag-parse", granted and rest == ["--other"])
    check("consent-notice", g.consent_notice("probe-axis", [flag]).startswith("CONSENT-REQUIRED:"))
    check("credential-rc3", g.EXIT_CREDENTIAL_UNAVAILABLE == 3)
    check("credential-detect", g.credential_error_line(
        ["ERROR: InvalidAccessKeyId.NotFound: Specified access key is not found."]) is not None)
    check("credential-prose-detect", g.credential_error_line(["unable to locate credentials"]) is not None)
    check("credential-nopermission-not-fatal", g.credential_error_line(
        ["NoPermission: You are not authorized to do this action."]) is None)
    check("probe-refused", bool(g.credential_probe_tokens(["cat ~/.aliyun/config.json"])))
    view = g.customer_view(["== INTERNAL ==", "  RequestId: ABC-123", "  Code: Throttling",
                            "Disk d-abc is healthy."])
    check("scrub-sdk-body", "Disk d-abc is healthy." in view and "RequestId" not in view
          and "Throttling" not in view and "INTERNAL" not in view)
    check("scrub-sdk-tail", g.customer_line("read failed: request execution failed: SDKError:") == "read failed:")
    check("scrub-request-id", g.customer_line("query failed request id: ABCDEF12-34567890") == "query failed")
    check("scrub-verdict-words", g.customer_line("status INSUFFICIENT-EVIDENCE / UNCONFIRMED")
          == "status not enough evidence yet / not confirmed")
    check("scrub-uid", g.sanitize_identifiers("account 1234567890123456") == "account ****3456")
    check("fail-closed-text", g.credential_fail_closed("hit", axis="probe-axis", exit_code=1
          ).startswith("CREDENTIAL-FAIL-CLOSED:"))
    check("offer-target-not-found", g.target_not_found_line(
        ["No instance matched i-abc in cn-hangzhou, so no conclusion was drawn."]) is not None)
    check("offer-no-false-positive", g.target_not_found_line(["Disk d-abc is healthy."]) is None)
    check("offer-missing-arg", g.missing_instance_arg(
        ["error: the following arguments are required: --instance-id"]))
    check("offer-missing-arg-region-only", not g.missing_instance_arg(
        ["error: the following arguments are required: --region-id"]))
    offer_block = "\n".join(g.instance_offer_block(["i-abc (web, Running)"], region="cn-hangzhou",
                                                   state="candidates", total=1, had_target_id=True))
    check("offer-block-candidates", "i-abc" in offer_block and "Reply with the one" in offer_block)
    offer_empty = "\n".join(g.instance_offer_block([], region="cn-hangzhou", state="empty"))
    check("offer-block-empty", "not your account" in offer_empty)
    offer_unavail = "\n".join(g.instance_offer_block([], region="cn-hangzhou", state="unavailable"))
    check("offer-block-unavailable", "console" in offer_unavail)
    check("offer-region-parse", region_from_argv(
        ["--region-id", "cn-hangzhou", "--instance-id", "i-abc"]) == "cn-hangzhou")
    ua_ok = isinstance(globals().get("SKILL_UA"), str) and \
        "AlibabaCloud-Agent-Skills/alibabacloud-ecs-" in globals().get("SKILL_UA", "")
    check("ua-defined-before-run", ua_ok)
    sight = g.region_sightings_block("i-x", found_region="cn-shanghai",
                                     scanned=3, total_regions=29)
    check("sighting-found", "--region-id cn-shanghai" in " ".join(sight)
          and "does not switch" in " ".join(sight))
    stopped = g.region_sightings_block("i-x", scanned=12, total_regions=29,
                                       stop_reason="the sweep time budget ran out")
    check("sighting-partial", "12 of 29" in " ".join(stopped)
          and "not checked" in " ".join(stopped))
    miss = g.region_sightings_block("i-x", scanned=29, total_regions=29)
    check("sighting-none", "29 regions on the built-in sweep list" in " ".join(miss))
    wired = all(name in globals() for name in
                 ("OFFER_PAGE_SIZE", "OFFER_MAX_PAGES", "SWEEP_REGIONS",
                  "SWEEP_CALL_TIMEOUT", "SIGHTING_BUDGET_S",
                  "instance_candidates", "target_id_from_argv",
                  "instance_sightings")) and len(SWEEP_REGIONS) == 29
    check("sightings-wired", wired)
    native = g.target_not_found_line(
        ["instance i-notthere123456 was not returned in cn-hangzhou; "
         "check the region and the credential's resource scope"])
    prose = g.target_not_found_line(
        ["Instance not visible in the console list or in a resource group"])
    check("offer-detection-wording", bool(native) and prose is None)
    if failures:
        print("SELFTEST FAIL %d/%d checks failed: %s" % (len(failures), total, ", ".join(failures)), flush=True)
        return 1
    print("SELFTEST PASS %d checks" % total, flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description='account-and-service-process axis dispatcher')
    ap.add_argument('--axis', choices=sorted(AXES))
    ap.add_argument('--selftest', action='store_true',
                    help='offline gate checks (no cloud call, no credential read)')
    ap.add_argument(g.CONSENT_FLAG, action='store_true', dest='allow_guest_read',
                    help='the customer explicitly confirmed the in-guest read-only '
                         'command this call would deliver')
    argv = sys.argv[1:]
    if '--' in argv:
        i = argv.index('--')
        front, back = argv[:i], argv[i + 1:]
    else:
        front, back = argv, []
    a, unknown = ap.parse_known_args(front)
    if a.selftest:
        return selftest()
    if not a.axis:
        ap.error('--axis is required (or run --selftest)')
    rest = list(unknown) + back
    rest, granted = g.parse_consent(rest, granted=a.allow_guest_read)
    rest, dropped = g.gate_guest_flags(rest, GUEST_ACTIVATION.get(a.axis, ()), granted)
    if dropped:
        print(g.consent_notice(a.axis, dropped), flush=True)
    entry = os.path.join(HERE, AXES[a.axis])
    if not os.path.isfile(entry):
        print('entry not found: ' + entry, file=sys.stderr)
        return 2
    # Argument-list invocation (shell=True is forbidden); the axis enforces its own
    # read-only/confirmation contract behind this gate.
    rc, lines = g.run_stream([sys.executable, entry] + rest, timeout_s=600,
                             env=g.consent_env(granted), echo=sys.stderr)
    hit = g.credential_error_line(lines)
    body = list(lines)
    if hit:
        body.extend([''] + g.credential_fail_closed(
            hit, axis=a.axis, exit_code=rc).splitlines())
    offer_state = None
    offer_region = region_from_argv(rest)
    if hit:
        offer_state = 'not evaluated (this run failed on credentials)'
    elif offer_region and g.missing_instance_arg(lines):
        rows, state, denial, meta = instance_candidates(
            offer_region, env=g.consent_env(granted))
        if denial:
            body.extend(['', denial])
        body.extend([''] + g.instance_offer_block(
            rows, region=offer_region, state=state,
            total=(meta or {}).get('total') or len(rows), had_target_id=False))
        if (meta or {}).get('partial'):
            body.append("The listing above covered the first %d instances of %s "
                        "reported for this region; the rest are counted, not shown."
                        % (len(rows), (meta or {}).get('total') or 'more'))
        offer_state = state
    elif g.target_not_found_line(lines, target_id_from_argv(rest)):
        had_id = any(tok.split('=', 1)[0] in ('--instance-id', '--instance-ids')
                     for tok in rest)
        rows, state, denial, meta = instance_candidates(
            offer_region, env=g.consent_env(granted))
        if denial:
            body.extend(['', denial])
        if had_id:
            named = target_id_from_argv(rest) or ''
            found_region, scanned, total_regions, stop = instance_sightings(
                named, env=g.consent_env(granted))
            body.extend([''] + g.region_sightings_block(
                named, found_region=found_region, scanned=scanned,
                total_regions=total_regions, stop_reason=stop))
            print('REGION-SIGHTING: %s' % (found_region or
                  (stop or 'none in %d regions checked' % scanned)),
                  file=sys.stderr, flush=True)
        body.extend([''] + g.instance_offer_block(
            rows, region=offer_region, state=state,
            total=(meta or {}).get('total') or len(rows), had_target_id=had_id))
        if (meta or {}).get('partial'):
            body.append("The listing above covered the first %d instances of %s "
                        "reported for this region; the rest are counted, not shown."
                        % (len(rows), (meta or {}).get('total') or 'more'))
        offer_state = state
    if offer_state:
        print('INSTANCE-OFFER: %s' % offer_state, file=sys.stderr, flush=True)
    sys.stdout.write(g.customer_view(body))
    sys.stdout.flush()
    if hit:
        return g.EXIT_CREDENTIAL_UNAVAILABLE
    return rc


if __name__ == '__main__':
    sys.exit(main())

