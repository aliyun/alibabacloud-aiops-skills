#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified entry for compliance-and-filing-docs: dispatch --axis <name> to that axis's original
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

import _guardrails as g

AXES = {
 "idc-address-query": "axes/idc_address_query/idc_address_query.py",
 "compliance-cert-guide": "axes/compliance_cert_guide/compliance_inventory.py"
}

# Axes that can deliver a command into the customer's instance, and the flags that
# activate that delivery. Evidence-derived: only axes whose entry script really
# dispatches through Cloud Assistant are listed; every other axis has no guest channel.
GUEST_ACTIVATION = {}
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description='compliance-and-filing-docs axis dispatcher')
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
