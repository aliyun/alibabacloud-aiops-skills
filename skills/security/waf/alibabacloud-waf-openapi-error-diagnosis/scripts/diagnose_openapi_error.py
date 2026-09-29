#!/usr/bin/env python3
"""
WAF OpenAPI Parameter Diagnosis Helper (read-only)

Fetches the AUTHORITATIVE parameter spec for a WAF OpenAPI action from the public
Alibaba Cloud OpenAPI metadata endpoint, prints it, and (optionally) diffs a set of
request parameters the customer actually sent against that spec, so the offending
parameter can be located precisely.

Works for BOTH WAF generations:
  - WAF 3.0 -> version 2021-10-01 (the only 3.0 version)
  - WAF 2.0 -> versions 2016-03-10 / 2016-07-18 / 2017-09-30 / 2018-01-17 /
               2019-09-10 / 2021-07-27 (2021-07-27 is 2.0, NOT 3.0 -- never guess
               the generation from the year). The public metadata only publishes
               specs for 2019-09-10; the other five 2.0 versions have no public docs.

--version is required for spec fetch and parameter diff. When omitted, the script only
probes documented versions and exits with a confirmation prompt; it never silently pins
a version or emits a version-specific spec.

The metadata endpoint is public and needs NO credentials, so the core spec lookup
and diff run without any AK/SK. This script never sends a real WAF API call.

Observability: the Agent injects SKILL_SESSION_ID and SKILL_VERSION as inline env
vars; this script builds its request User-Agent from them at runtime (version falls
back to references/manifest.json). Format:
    AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{skill-version}

Usage:
    # Discovery only: report candidate versions, then obtain user confirmation
    SKILL_SESSION_ID=<session-id> SKILL_VERSION=<skill-version> \
        python3 scripts/diagnose_openapi_error.py --action CreateDomain

    # Fetch the confirmed-version spec
    SKILL_SESSION_ID=<session-id> SKILL_VERSION=<skill-version> \
        python3 scripts/diagnose_openapi_error.py --version 2019-09-10 --action CreateDomain

    # Diff supplied API/SDK params; preserve redaction markers such as "***"
    SKILL_SESSION_ID=<session-id> SKILL_VERSION=<skill-version> \
        python3 scripts/diagnose_openapi_error.py --version 2021-10-01 \
        --action CreateDefenseRule --params '{"RegionId":"cn-beijing","TemplateId":"123"}'

Exit codes:
    0: no parameter problem found (params consistent with the official spec)
    1: at least one parameter problem located (unknown / missing / type / enum)
    2: spec fetch error, action/version not resolvable, or bad input (human intervention)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

PRODUCT = "waf-openapi"
META_URL = ("https://api.aliyun.com/meta/v1/products/{product}"
            "/versions/{version}/apis/{action}/api.json")
SKILL_NAME = "alibabacloud-waf-openapi-error-diagnosis"
# Session-id and skill-version are injected by the Agent at runtime (see the
# Observability section in SKILL.md). The version falls back to references/manifest.json.
SESSION_ID = os.environ.get("SKILL_SESSION_ID", "")
_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "references", "manifest.json")


def _manifest_version():
    try:
        with open(_MANIFEST, "r", encoding="utf-8") as f:
            v = json.load(f).get("version")
            return v if isinstance(v, str) and v else ""
    except (OSError, ValueError):
        return ""


SKILL_VERSION = os.environ.get("SKILL_VERSION", "") or _manifest_version()


def build_user_agent():
    """AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{skill-version}.

    Degrades gracefully when session-id / version are unavailable so the call still
    carries a meaningful attribution prefix.
    """
    ua = "AlibabaCloud-Agent-Skills/%s" % SKILL_NAME
    if SESSION_ID:
        ua += "/%s" % SESSION_ID
    if SKILL_VERSION:
        ua += " skill-version/%s" % SKILL_VERSION
    return ua

# WAF has TWO major generations. WAF 3.0 has a single version; WAF 2.0 spans SIX
# version strings. NEVER infer the generation from the year -- 2021-07-27 is WAF 2.0
# even though it looks close to WAF 3.0's 2021-10-01.
WAF3_VERSIONS = ("2021-10-01",)
WAF2_VERSIONS = ("2016-03-10", "2016-07-18", "2017-09-30",
                 "2018-01-17", "2019-09-10", "2021-07-27")
# The public api.aliyun.com metadata only publishes specs for these two versions;
# the other five WAF 2.0 versions return no data there (documented 2.0 = 2019-09-10).
DOCUMENTED_VERSIONS = ("2021-10-01", "2019-09-10")
ALL_KNOWN_VERSIONS = WAF3_VERSIONS + WAF2_VERSIONS


def major_of(version):
    """Map an API version string to its WAF generation ('3.0' / '2.0' / None)."""
    if version in WAF3_VERSIONS:
        return "3.0"
    if version in WAF2_VERSIONS:
        return "2.0"
    return None

# Loose JSON-schema type -> python type families
_TYPE_MAP = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def kebab_to_pascal(name):
    """describe-defense-rules -> DescribeDefenseRules (leave PascalCase untouched)."""
    if "-" in name:
        return "".join(p[:1].upper() + p[1:] for p in name.split("-") if p)
    return name[:1].upper() + name[1:]


def pascal_to_kebab(name):
    """DescribeDefenseRules -> describe-defense-rules."""
    if "-" in name:
        return name
    s = re.sub(r"(?<!^)(?=[A-Z])", "-", name)
    return s.lower()


def fetch_spec(version, action):
    url = META_URL.format(product=PRODUCT, version=version, action=action)
    req = urllib.request.Request(url, headers={"User-Agent": build_user_agent()})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return None, "HTTP %s from metadata endpoint" % resp.status
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, "HTTP %s %s (action may not exist in version %s)" % (
            e.code, e.reason, version)
    except urllib.error.URLError as e:
        return None, "network error: %s" % e.reason
    except json.JSONDecodeError as e:
        return None, "invalid metadata JSON: %s" % e


def spec_is_real(spec):
    """The metadata endpoint returns HTTP 200 with {"message":"api not found"} for an
    action absent from that version. A real spec carries parameters/methods/responses."""
    return (isinstance(spec, dict)
            and not (spec.get("message") and "parameters" not in spec)
            and any(k in spec for k in ("parameters", "methods", "responses", "summary")))


def resolve_version(action):
    """Probe the documented versions and find which one(s) contain the action.

    Returns (version, spec, matched, err):
      - exactly one match  -> (that version, its spec, [version], None)
      - multiple matches   -> (None, None, [versions...], ambiguity_error)  # do NOT guess
      - no match           -> (None, None, [], not_found_error)
    Implements version determination from the action name using fresh public data.
    Some actions (e.g. CreateDomain) exist in BOTH generations, so ambiguity is real
    and must be surfaced rather than silently resolved to the first hit.
    """
    matched = []
    for v in DOCUMENTED_VERSIONS:
        spec, err = fetch_spec(v, action)
        if err is None and spec_is_real(spec):
            matched.append((v, spec))
    if len(matched) == 1:
        return matched[0][0], matched[0][1], [matched[0][0]], None
    if len(matched) > 1:
        vers = [m[0] for m in matched]
        return None, None, vers, (
            "action '%s' exists in MULTIPLE documented versions %s -- cannot infer the "
            "WAF generation from the name alone. Pass --version explicitly (WAF 3.0="
            "2021-10-01, WAF 2.0=2019-09-10); never guess it from the year."
            % (action, vers))
    return None, None, [], (
        "action '%s' not found in the documented public versions %s"
        % (action, list(DOCUMENTED_VERSIONS)))



def flatten_params(raw_params):
    """Normalize the metadata `parameters[]` into a flat spec list.

    Handles both flat query params and body/schema-wrapped params.
    """
    specs = []
    for p in raw_params or []:
        name = p.get("name")
        if not name:
            continue
        schema = p.get("schema") or {}
        specs.append({
            "name": name,
            "in": p.get("in", "query"),
            "type": schema.get("type", "string"),
            "required": bool(schema.get("required", False)),
            "enum": schema.get("enum") or schema.get("enumValueTitles") or None,
            "example": schema.get("example"),
            "default": schema.get("default"),
            "description": (schema.get("description") or "").strip(),
        })
    return specs


def cli_flags(version, action):
    """Collect valid `--flags` from the aliyun CLI plugin help (CLI channel only)."""
    kebab = pascal_to_kebab(action)
    cmd = ["aliyun", PRODUCT, kebab, "--help"]
    if version != "2021-10-01":
        cmd = ["aliyun", PRODUCT, kebab, "--api-version", version, "--help"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return None, "cannot run aliyun --help: %s" % e
    out = proc.stdout + proc.stderr
    if "not a valid" in out or "is not available" in out:
        return None, out.strip().splitlines()[0] if out.strip() else "unknown action"
    flags = set(re.findall(r"^\s+(--[a-z0-9-]+)", out, flags=re.MULTILINE))
    return flags, None


def type_ok(expected, value):
    py = _TYPE_MAP.get(expected)
    if py is None:
        return True
    if expected in ("integer", "number") and isinstance(value, bool):
        return False
    # API transports are string-based; a numeric/boolean sent as string is acceptable
    if isinstance(value, str):
        return True
    return isinstance(value, py)


_REDACTED_MARKERS = {"***", "*****", "******", "<redacted>", "[redacted]", "redacted"}


def is_redacted_value(value):
    """Return True for an explicit redaction marker; never request or reconstruct it."""
    return isinstance(value, str) and value.strip().lower() in _REDACTED_MARKERS


def redacted_param_names(params):
    """Return top-level parameter names whose values were explicitly redacted."""
    return sorted(key for key, value in params.items() if is_redacted_value(value))


def diff_params(specs, params):
    """Compare customer params against the spec. Returns a list of findings."""
    findings = []
    by_name = {s["name"]: s for s in specs}

    # 1) missing required
    for s in specs:
        if s["required"] and s["name"] not in params:
            findings.append({
                "kind": "missing_required", "param": s["name"],
                "detail": "required parameter is absent (type=%s, example=%s)"
                          % (s["type"], s["example"])})

    # 2) unknown / misspelled params
    for key in params:
        if key not in by_name:
            close = [n for n in by_name if n.lower() == key.lower()]
            hint = (" -> did you mean '%s' (wrong case/style)?" % close[0]
                    if close else "")
            findings.append({
                "kind": "unknown_param", "param": key,
                "detail": "not a documented parameter of this action%s" % hint})

    # 3) type + enum on the params that do exist
    for key, val in params.items():
        s = by_name.get(key)
        if not s or is_redacted_value(val):
            continue
        if not type_ok(s["type"], val):
            findings.append({
                "kind": "type_mismatch", "param": key,
                "detail": "expected type %s, got %s"
                          % (s["type"], type(val).__name__)})
        if s["enum"] and val not in s["enum"]:
            findings.append({
                "kind": "enum_violation", "param": key,
                "detail": "value %r not in allowed set %s"
                          % (val, s["enum"])})
    return findings


def main():
    ap = argparse.ArgumentParser(
        description="Read-only WAF OpenAPI parameter diagnosis helper")
    ap.add_argument("--action", required=True,
                    help="API action (PascalCase or kebab-case), e.g. DescribeDefenseRules")
    ap.add_argument("--version",
                    help="Confirmed API version. WAF 3.0 = 2021-10-01; WAF 2.0 = one of "
                         "2016-03-10/2016-07-18/2017-09-30/2018-01-17/2019-09-10/"
                         "2021-07-27. If omitted, discovery reports candidates and exits.")
    ap.add_argument("--channel", choices=("api", "cli"), default="api",
                    help="api = SDK/raw PascalCase params; cli = also validate CLI flags")
    ap.add_argument("--params", help="JSON object of the params the customer sent "
                                     "(or @path/to/file.json)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    action = kebab_to_pascal(args.action)

    # --- Determine candidate versions, but require explicit user confirmation ---
    version = args.version
    if version is None:
        candidate, _spec, matched, rerr = resolve_version(action)
        if matched and len(matched) > 1:
            print("[NEEDS_CONFIRMATION] %s" % rerr, file=sys.stderr)
            print("        Choices: WAF 2.0 (2019-09-10) or WAF 3.0 "
                  "(2021-10-01). Ask the customer to choose, then WAIT.", file=sys.stderr)
        elif candidate:
            print("[NEEDS_CONFIRMATION] action '%s' is documented in version %s "
                  "(WAF %s), but the customer did not provide an API version."
                  % (action, candidate, major_of(candidate)), file=sys.stderr)
            print("        Ask the customer to confirm the API version, then WAIT and "
                  "rerun with --version explicitly.", file=sys.stderr)
        else:
            print("[ERROR] cannot discover a documented version for action '%s': %s"
                  % (action, rerr), file=sys.stderr)
            print("        Ask the customer for the API version; do not guess.",
                  file=sys.stderr)
        sys.exit(2)
    else:
        known = major_of(version)
        if known is None:
            print("[ERROR] --version %r is not a known WAF version. Known: WAF 3.0 %s; "
                  "WAF 2.0 %s." % (version, list(WAF3_VERSIONS), list(WAF2_VERSIONS)),
                  file=sys.stderr)
            sys.exit(2)
        if version not in DOCUMENTED_VERSIONS:
            print("[ERROR] WAF %s version %s has NO public API docs on api.aliyun.com "
                  "(only 2019-09-10 is published for WAF 2.0)." % (known, version),
                  file=sys.stderr)
            print("        The parameter spec cannot be fetched for this version. Retry "
                  "with --version 2019-09-10 (the documented WAF 2.0 version), or check "
                  "the OpenAPI portal. Do NOT read this as 'the action does not exist'.",
                  file=sys.stderr)
            sys.exit(2)
        spec, err = fetch_spec(version, action)

    if err or spec is None:
        print("[ERROR] cannot fetch spec for %s/%s: %s"
              % (PRODUCT, version, action), file=sys.stderr)
        if err:
            print("        %s" % err, file=sys.stderr)
        sys.exit(2)

    # A wrong-version action returns HTTP 200 with {"message":"api not found"} --
    # surface it as the wrong-version root cause (never as "action has no params").
    if not spec_is_real(spec):
        msg = spec.get("message") if isinstance(spec, dict) else None
        other = "2019-09-10" if version == "2021-10-01" else "2021-10-01"
        print("[ERROR] action '%s' not found in version %s%s."
              % (action, version, " (metadata says: %s)" % msg if msg else ""),
              file=sys.stderr)
        print("        Either (a) it belongs to the other WAF generation -- confirm ONCE "
              "with --version %s; or (b) the action name is wrong / it is a non-public "
              "(internal) action with NO public API docs. If the other version also "
              "returns 'api not found', conclude case (b): report 'no public spec', fall "
              "back to the manual diff dimensions, and do NOT invent a spec." % other,
              file=sys.stderr)
        sys.exit(2)

    params = None
    if args.params:
        raw = args.params
        if raw.startswith("@"):
            try:
                with open(raw[1:], "r", encoding="utf-8") as f:
                    raw = f.read()
            except OSError as e:
                print("[ERROR] cannot read params file: %s" % e, file=sys.stderr)
                sys.exit(2)
        try:
            params = json.loads(raw)
        except ValueError as e:
            print("[ERROR] --params is not valid JSON: %s" % e, file=sys.stderr)
            sys.exit(2)
        if not isinstance(params, dict):
            print("[ERROR] --params must be a JSON object", file=sys.stderr)
            sys.exit(2)

    specs = flatten_params(spec.get("parameters"))
    if not specs:
        print("[WARN] action %s has no documented request parameters" % action,
              file=sys.stderr)

    findings = diff_params(specs, params) if params is not None else []
    redacted_params = redacted_param_names(params) if params is not None else []

    cli_flag_info = None
    if args.channel == "cli":
        flags, cerr = cli_flags(version, action)
        cli_flag_info = {"error": cerr} if cerr else {"valid_flags": sorted(flags)}

    report = {
        "product": PRODUCT,
        "version": version,
        "version_explicitly_confirmed": True,
        "waf_generation": major_of(version),
        "action": action,
        "cli_action": pascal_to_kebab(action),
        "summary": spec.get("summary") or spec.get("description") or "",
        "methods": spec.get("methods"),
        "parameter_spec": specs,
        "cli": cli_flag_info,
        "findings": findings,
        "redacted_params": redacted_params,
        "redaction_non_blocking": bool(redacted_params),
        "problem_found": bool(findings),
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(1 if findings else 0)

    print("\n" + "=" * 68)
    print("  WAF OpenAPI Parameter Spec: %s (%s / WAF %s, version confirmed)"
          % (action, version, report["waf_generation"]))
    print("=" * 68)
    if report["summary"]:
        print("  %s" % report["summary"])
    if args.channel == "cli":
        print("  CLI action: aliyun %s %s%s"
              % (PRODUCT, report["cli_action"],
                 "" if version == "2021-10-01"
                 else " --api-version " + version))
    print("-" * 68)
    print("  %-32s %-8s %-6s %s" % ("PARAM", "TYPE", "REQ", "ENUM / EXAMPLE"))
    for s in specs:
        enum_ex = ""
        if s["enum"]:
            enum_ex = "enum=%s" % (s["enum"][:6])
        elif s["example"] is not None:
            enum_ex = "e.g. %s" % (str(s["example"])[:32])
        print("  %-32s %-8s %-6s %s"
              % (s["name"], s["type"], "yes" if s["required"] else "no", enum_ex))
    if cli_flag_info and cli_flag_info.get("valid_flags"):
        print("-" * 68)
        print("  Valid CLI flags: %s" % ", ".join(cli_flag_info["valid_flags"]))
    elif cli_flag_info and cli_flag_info.get("error"):
        print("-" * 68)
        print("  [CLI help unavailable] %s" % cli_flag_info["error"])

    if params is not None:
        print("-" * 68)
        if redacted_params:
            print("  REDACTION (NON-BLOCKING): %s" % ", ".join(redacted_params))
            print("  Diff continued; only the redacted values' content/format could not "
                  "be fully validated.")
        if findings:
            print("  LOCATED %d PARAMETER PROBLEM(S):" % len(findings))
            for f in findings:
                print("   - [%s] %s: %s" % (f["kind"], f["param"], f["detail"]))
        else:
            print("  No parameter problem found against the official spec.")
    print("=" * 68 + "\n")
    if not findings and params is not None:
        print("Note: params match the documented spec. If the call still fails, the "
              "error is likely NOT parameter-class (auth / permission / throttling / "
              "server-side) or a value is semantically wrong (e.g. an InstanceId that "
              "does not exist). Check the error Code and RequestId.", file=sys.stderr)

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
