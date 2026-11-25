#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified entry for server-migration-on-cloud: dispatch --axis <name> to that axis's original
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
import os
import sys
import subprocess

import _guardrails as g

AXES = {"site-migration-guide": "axes/site_migration_guide/site_migration.py",
 "onmigration-assessment": "axes/onmigration_assessment/assess_migration.py",
 "forced-migration-guide": "axes/forced_migration_guide/forced_migration_guide.py",
 "instance-clone-guide": "axes/instance_clone_guide/clone_guidance.py",
 "instance-relocation-guide": "axes/instance_relocation_guide/relocation_preflight.py"
}

# Axes that can deliver a command into the customer's instance, and the flags that
# activate that delivery. Evidence-derived: only axes whose entry script really
# dispatches through Cloud Assistant are listed; every other axis has no guest channel.
GUEST_ACTIVATION = {}
HERE = os.path.dirname(os.path.abspath(__file__))




def _selftest():
    """Dispatcher-level end-to-end survival guard (F1): every registered axis must
    exist and answer --help; the consent gate must strip ungranted guest flags."""
    checks = []

    def check(name, ok, detail=''):
        checks.append(ok)
        print('[%s] %s%s' % ('PASS' if ok else 'FAIL', name, (' ' + detail) if detail else ''))

    check('axes-registered', bool(AXES))
    for axis, rel in sorted(AXES.items()):
        entry = os.path.join(HERE, rel)
        check('entry-exists:' + axis, os.path.isfile(entry))
        try:
            rc = subprocess.run([sys.executable, entry, '--help'], capture_output=True,
                                timeout=60).returncode
            check('axis-help:' + axis, rc == 0, 'rc=%d' % rc)
        except Exception as exc:
            check('axis-help:' + axis, False, repr(exc))
    check('guest-keys-subset', set(GUEST_ACTIVATION) <= set(AXES))
    flags = ('--confirm',)
    stripped, dropped = g.gate_guest_flags(list(flags), flags, False)
    check('consent-strips-ungranted', not stripped and bool(dropped))
    kept, dropped2 = g.gate_guest_flags(list(flags), flags, True)
    check('consent-keeps-granted', kept == list(flags) and not dropped2)
    check("auth-denial-code", g.policy_denial_code(
        ["ERROR: NoPermission: User not authorized to operate on the specified resource."]) == "NoPermission")
    check("auth-denial-json", g.policy_denial_code(
        ['{"Code": "NoPermission", "Message": "refused"}']) == "NoPermission")
    check("auth-denial-action", g.extract_denied_action(
        ["NoPermission: ecs:DescribeDisks"]) == "ecs:DescribeDisks")
    check("auth-denial-not-credential", g.credential_error_line(
        ["NoPermission: You are not authorized."]) is None)
    check("auth-prose-not-denial", g.policy_denial_code(
        ["When the code is NoPermission, the missing permission must be granted."]) is None)
    check("auth-gap-short", "Add only that one action." in "\n".join(
        g.authorization_gap_short("NoPermission", action="ecs:DescribeDisks")))
    check("auth-gap-block-axis", "ecs:DescribeDisks" in g.authorization_gap_block(
        "NoPermission", action="ecs:DescribeDisks", axis="probe-axis", exit_code=1))
    check("auth-denial-raw-line", g.is_policy_denial(
        "ERROR: NoPermission: refused acs:ram::1234567890123456:role/x"))
    check("auth2-identity-field", g.identity_type_of(
        ["  IdentityType    : RAMUser"]) == "RAMUser")
    check("auth2-identity-unproven", g.identity_type_of(["account ****3456"]) is None)
    check("auth2-grant-role", "intersection" in "\n".join(
        g.authorization_gap_short("NoPermission", action="ecs:DescribeDisks",
                                  identity_type="AssumedRoleUser")))
    check("auth3-expired-refresh", "Refresh them first" in g.credential_fail_closed(
        "ERROR: SecurityTokenExpired: expired", axis="probe-axis", exit_code=3))
    check("auth3-ak-config", "configuration" in g.credential_fail_closed(
        "ERROR: InvalidAccessKeyId.NotFound: x", axis="probe-axis", exit_code=3))
    n_ok = sum(1 for c in checks if c)
    print('SELFTEST %s %d checks' % ('PASS' if n_ok == len(checks) else 'FAIL', len(checks)))
    return 0 if n_ok == len(checks) else 1


def main():
    if '--selftest' in sys.argv[1:]:
        return _selftest()
    ap = argparse.ArgumentParser(description='server-migration-on-cloud axis dispatcher')
    ap.add_argument('--axis', required=True, choices=sorted(AXES))
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
    denial_code = None if hit else g.policy_denial_code(lines)
    identity_type = g.identity_type_of(lines)
    if denial_code:
        # AUTH-1: a policy refusal is NOT fail-closed - the identity
        # authenticated and the rest of the answer stands. The customer is
        # owed the single-action grant path; the raw denial line (resource
        # ARN with the account id) stays out of the customer block, and the
        # long form goes to the run log on stderr.
        # The raw refusal lines carry the resource ARN (account id); they stay
        # in the run log (run_stream already echoed them to stderr) and out of
        # the customer block, which gets the actionable gap form instead.
        body = [ln for ln in body if not g.is_policy_denial(ln)]
        body.extend([''] + g.authorization_gap_short(
            denial_code, action=g.extract_denied_action(lines),
            identity_type=identity_type))
        for line in g.authorization_gap_block(
                denial_code, action=g.extract_denied_action(lines),
                axis=a.axis, exit_code=rc,
                identity_type=identity_type).splitlines():
            print(line, file=sys.stderr, flush=True)
    sys.stdout.write(g.customer_view(body))
    sys.stdout.flush()
    if hit:
        return g.EXIT_CREDENTIAL_UNAVAILABLE
    return rc


if __name__ == '__main__':
    sys.exit(main())


# --- release-side versioned User-Agent (static rule UA-SKILL-VERSION) ---
import json as _json


def _skill_version_from_manifest():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "manifest.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return _json.load(fh)["version"]
    except Exception:
        return "0.0.0"


SKILL_UA = "AlibabaCloud-Agent-Skills skill-version/" + _skill_version_from_manifest()
# --- end versioned UA ---
