#!/usr/bin/env bash
# Offline analysis of nginx Ingress annotation compatibility — no cluster access, no credentials.
#
# Usage:
#   analyze-ingress-offline.sh <file.yaml|dir> [...]
#   analyze-ingress-offline.sh <file.yaml|dir> --json-only
#   analyze-ingress-offline.sh --help
#
# Output:
#   stderr: per-Ingress classification report (🟢 converted / 🟡 behaviour change /
#           🔴 unsupported / 🚫 downgraded) plus path risks
#   stdout: JSON array with the same findings, structured for a machine to read
#
# Verdicts are decided by **value**, not by key alone, matching the ingress2albconfig source
# (the AddInfo / AddError / AddCritical trio in feature_*.go). See references/annotation-mapping.md.
#
# Dependencies (declared, and enforced at runtime below — see PYYAML_MIN):
#   python3 >= 3.8   required. Nothing else from the standard library is pinned.
#   PyYAML  >= 5.0   OPTIONAL. Used when importable AND at least this version; anything older
#                    is refused rather than trusted, because 5.0 is where safe_load became the
#                    documented default and multi-document handling settled. When PyYAML is
#                    absent or too old the script falls back to a built-in minimal parser that
#                    extracts only annotations and paths — enough for compatibility analysis,
#                    and it says which parser it used so a verdict is never silently weaker.
#   No network access, no cloud SDK, no kubectl: nothing here reaches outside the filesystem.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: analyze-ingress-offline.sh <file.yaml|dir> [...] [--json-only]

Analyze nginx Ingress YAML offline and classify every annotation for an ALB migration.

Arguments:
  <file.yaml|dir>  One or more YAML files, or directories to scan for *.yaml / *.yml
  --json-only      Print only the JSON to stdout (suppress the stderr report)
  -h, --help       Show this help

Output:
  stderr: per-Ingress report — 🟢 converted, 🟡 behaviour change, 🔴 unsupported,
          🚫 downgraded (still produced, but needs human confirmation)
  stdout: JSON array of the same findings

Notes:
  Does NOT require kubectl or cluster access.
  This is a single-Ingress view: cross-Ingress regex tainting, order and splitting are
  batch-level conclusions it does not produce. See references/generated-resources.md §5.
EOF
}

JSON_ONLY=0
TARGETS=()
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --json-only) JSON_ONLY=1 ;;
        -*) echo "Error: unknown option: $arg" >&2; echo "  Try --help." >&2; exit 2 ;;
        *) TARGETS+=("$arg") ;;
    esac
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
    echo "Error: no input specified." >&2
    echo "  Usage: $(basename "$0") <file.yaml|dir> [...] [--json-only]" >&2
    exit 2
fi

command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required." >&2; exit 1; }

# Collect the files to analyze.
FILES=()
for target in "${TARGETS[@]}"; do
    if [ -d "$target" ]; then
        while IFS= read -r f; do FILES+=("$f"); done \
            < <(find "$target" -type f \( -name '*.yaml' -o -name '*.yml' \) | sort)
    elif [ -f "$target" ]; then
        FILES+=("$target")
    else
        echo "Warning: skipping path that does not exist: $target" >&2
    fi
done

[ "${#FILES[@]}" -gt 0 ] || { echo "Error: no YAML file found." >&2; exit 1; }

JSON_ONLY="$JSON_ONLY" python3 - "${FILES[@]}" <<'PY'
import json
import os
import re
import sys

JSON_ONLY = os.environ.get("JSON_ONLY") == "1"


def report(*args):
    """Human-readable output goes to stderr, so stdout stays pure JSON."""
    if not JSON_ONLY:
        print(*args, file=sys.stderr)


P = "nginx.ingress.kubernetes.io/"

# The 20 annotations whose key can be converted: nginx short name -> alb short name.
# "The key converts" does not mean 🟢 — whether it is 🟢, 🟡 or 🔴 depends on the value,
# judged case by case below.
CONVERT = {
    "canary": "canary",
    "canary-by-header": "canary-by-header",
    "canary-by-header-value": "canary-by-header-value",
    "canary-by-cookie": "canary-by-cookie",
    "canary-weight": "canary-weight",
    "canary-weight-total": "canary-weight",   # folded into canary-weight, not its own annotation
    "enable-cors": "enable-cors",
    "cors-allow-origin": "cors-allow-origin",
    "cors-allow-methods": "cors-allow-methods",
    "cors-allow-headers": "cors-allow-headers",
    "cors-expose-headers": "cors-expose-headers",
    "cors-allow-credentials": "cors-allow-credentials",
    "cors-max-age": "cors-max-age",
    "backend-protocol": "backend-protocol",
    "load-balance": "backend-scheduler",
    "upstream-hash-by": "backend-scheduler-uch-value",
    "ssl-redirect": "ssl-redirect",
    "use-regex": "use-regex",
    "rewrite-target": "rewrite-target",
    # nginx's limit-rps and ALB's traffic-limit-ip-qps are the same thing (both "per client
    # IP per second") under different names. This was long reported as unsupported until a
    # reverse check found it.
    "limit-rps": "traffic-limit-ip-qps",
}

# 🔴 unsupported uses a **catch-all** verdict, matching the ingress2albconfig source: any
# nginx.ingress.kubernetes.io/* annotation not in CONVERT counts as unsupported. No hardcoded
# list is maintained, so a newly added upstream annotation is reported rather than missed.

# PyYAML is optional, but when present it must meet the declared floor: an older release is
# treated exactly like a missing one, so the fallback parser is used instead of a parser whose
# behaviour this script was never checked against.
PYYAML_MIN = (5, 0)
YAML_SKIP_REASON = ""
try:
    import yaml  # noqa

    def _pyyaml_version():
        raw = getattr(yaml, "__version__", "0")
        parts = []
        for chunk in raw.split(".")[:2]:
            digits = "".join(c for c in chunk if c.isdigit())
            parts.append(int(digits) if digits else 0)
        while len(parts) < 2:
            parts.append(0)
        return tuple(parts), raw

    _ver, _raw = _pyyaml_version()
    if _ver >= PYYAML_MIN:
        HAVE_YAML = True
    else:
        HAVE_YAML = False
        YAML_SKIP_REASON = "PyYAML %s is older than the required %d.%d" % (
            _raw, PYYAML_MIN[0], PYYAML_MIN[1])
except ImportError:
    HAVE_YAML = False
    YAML_SKIP_REASON = "PyYAML is not installed"


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_fallback(text):
    """Minimal parser for when PyYAML is absent: extract only what the analysis needs.

    Pulls out kind / metadata.name / metadata.namespace / annotations /
    spec.ingressClassName / rules[].http.paths[].{path,pathType}.
    """
    # tls=None means "could not be parsed" (the fallback parser does not reconstruct
    # spec.tls), which is kept distinct from "has no tls": the ssl-redirect judgement
    # needs it, and without it the judgement is skipped rather than guessed.
    out = {"kind": None, "name": None, "namespace": None,
           "annotations": {}, "class": None, "paths": [], "hosts": [], "tls": None}
    lines = text.splitlines()
    ann_indent = None       # indentation of the "annotations:" key
    cur_path = cur_type = None

    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()

        # Inside an annotation block, collect every more-deeply-indented "key: value".
        if ann_indent is not None:
            if indent > ann_indent and ":" in s and not s.startswith("- "):
                k, _, v = s.partition(":")
                out["annotations"][_unquote(k)] = _unquote(v)
                continue
            if indent <= ann_indent:
                ann_indent = None  # leave the annotation block and resume normal parsing

        if re.match(r"^annotations:\s*$", s):
            ann_indent = indent
            continue
        m = re.match(r"^kind:\s*(\S+)", s)
        if m and out["kind"] is None:
            out["kind"] = _unquote(m.group(1))
            continue
        m = re.match(r"^name:\s*(\S+)", s)
        if m and out["name"] is None and indent <= 4:
            out["name"] = _unquote(m.group(1))
            continue
        m = re.match(r"^namespace:\s*(\S+)", s)
        if m and out["namespace"] is None:
            out["namespace"] = _unquote(m.group(1))
            continue
        m = re.match(r"^ingressClassName:\s*(\S+)", s)
        if m:
            out["class"] = _unquote(m.group(1))
            continue
        m = re.match(r"^-?\s*host:\s*(\S+)", s)
        if m:
            out["hosts"].append(_unquote(m.group(1)))
            continue

        # path and pathType appear as a pair inside the same list item.
        m = re.match(r"^-?\s*path:\s*(\S+)", s)
        if m:
            if cur_path is not None:
                out["paths"].append((cur_path, cur_type))
            cur_path, cur_type = _unquote(m.group(1)), None
            continue
        m = re.match(r"^pathType:\s*(\S+)", s)
        if m:
            cur_type = _unquote(m.group(1))
            continue

    if cur_path is not None:
        out["paths"].append((cur_path, cur_type))
    return out


def normalize(doc):
    """Reshape a PyYAML result into the same structure parse_fallback returns."""
    md = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    paths = []
    hosts = []
    for rule in (spec.get("rules") or []):
        rule = rule or {}
        hosts.append(rule.get("host") or "")
        http = (rule.get("http") or {})
        for p in (http.get("paths") or []):
            paths.append((p.get("path", ""), p.get("pathType")))
    # The hosts list of each tls entry; an empty list = covers every host (matching
    # UnMatchTLS in the source).
    tls = [list((t or {}).get("hosts") or []) for t in (spec.get("tls") or [])]
    return {
        "kind": doc.get("kind"),
        "name": md.get("name"),
        "namespace": md.get("namespace"),
        "annotations": {str(k): str(v) for k, v in (md.get("annotations") or {}).items()},
        "class": spec.get("ingressClassName"),
        "paths": paths,
        "hosts": hosts,
        "tls": tls,
    }


def load(path):
    """Return the candidate Ingress records found in this file."""
    try:
        text = open(path).read()
    except OSError as e:
        report(f"⚠️  cannot read {path}: {e}")
        return []
    recs = []
    if HAVE_YAML:
        try:
            for d in yaml.safe_load_all(text):
                if isinstance(d, dict):
                    recs.append(normalize(d))
            return recs
        except Exception as e:
            report(f"⚠️  PyYAML failed on {path}, falling back to the minimal parser: {e}")
    # Minimal parser: split multi-document YAML on ---
    for chunk in re.split(r"(?m)^---\s*$", text):
        if chunk.strip():
            recs.append(parse_fallback(chunk))
    return recs


# ---- Constants and helpers for the value-level judgements ----

# ALB and nginx both read these annotations with Go's strconv.ParseBool, which accepts only
# the 12 spellings below. "on"/"yes" are not among them — neither side can parse those.
BOOL_OK = {"1", "t", "T", "TRUE", "true", "True",
           "0", "f", "F", "FALSE", "false", "False"}

# The 4 annotations whose value must be a boolean. A non-boolean means the annotation is
# stripped and reported 🚫; the rest of the Ingress is still produced.
BOOL_ANNOTATIONS = ("canary", "enable-cors", "cors-allow-credentials", "ssl-redirect")

# The tool's 🔴 scope is **not limited to the nginx prefix**: anything no feature consumed is
# reported, with only the two families below exempt.
ALB_PREFIX = "alb.ingress.kubernetes.io/"
TOOLING_PREFIXES = ("kubectl.kubernetes.io/", "app.kubernetes.io/", "helm.sh/",
                    "meta.helm.sh/", "argocd.argoproj.io/", "fluxcd.io/",
                    "kustomize.toolkit.fluxcd.io/")

# Reported and "removed from the output" are the same set: the prefixes below are both
# reported and left out of the output. Anything else (an in-house annotation, say) is
# reported 🟢 carried over and copied verbatim.
DROPPED_PREFIXES = ("nginx.ingress.kubernetes.io/", "nginx.org/", "nginx.com/",
                    "ingress.kubernetes.io/", "cert-manager.io/",
                    "external-dns.alpha.kubernetes.io/")

# A few 🔴 items have a migration recipe with a "wrong but still publishable" trap, or a
# conclusion that contradicts intuition. These notes only warn and point at the document —
# they deliberately **do not restate the recipe**, which is maintained in exactly one place
# (migration-patterns.md) so two sources of truth cannot drift apart.
TRAP_NOTES = {
    "custom-http-errors":
        "🚨 The ALB recipe needs all three parts and must include rule-direction.<svc>: Response — "
        "without the direction every request to that path is replaced by the error page, and the "
        "webhook does not catch it. See migration-patterns.md Level 1",
    "custom-headers":
        "🚨 Two preconditions: the value is a ConfigMap reference (expand it header by header); and "
        "it acts on **response** headers, so ALB needs an explicit rule-direction.<svc>: Response or "
        "it does nothing. See migration-patterns.md Level 1",
    "default-backend":
        "⚠️ This is the fallback for 'the rule's Service has no active endpoints', **not** "
        "spec.defaultBackend; ALB has no equivalent switch. See annotation-mapping.md §4.6",
    "proxy-next-upstream":
        "⚠️ Do not just drop it: ALB has no retry configuration at all. With a value of off, a "
        "non-idempotent endpoint may be submitted twice. See annotation-mapping.md §4.7",
    "proxy-next-upstream-tries": "⚠️ Same as proxy-next-upstream: see annotation-mapping.md §4.7",
    "proxy-next-upstream-timeout": "⚠️ Same as proxy-next-upstream: see annotation-mapping.md §4.7",
    "ssl-passthrough":
        "⚠️ ALB listener protocols are only HTTP/HTTPS/QUIC, so this **cannot** become TCP/SSL on "
        "ALB — move it to CLB/NLB, where it no longer goes through the three resources. "
        "See annotation-mapping.md §4.12",
    "mirror-target":
        "⚠️ The mirror target can only be a server group (TargetType has the single value "
        "ForwardGroupMirror), not an arbitrary URL",
    "mirror-request-body": "⚠️ ALB's mirror configuration has no such field; it cannot be expressed",
    "mirror-host":
        "⚠️ An ALB mirrored request carries the original Host and it cannot be rewritten; a mirror "
        "backend that splits environments by Host will silently take the wrong branch",
}

ALB_QPS_MIN, ALB_QPS_MAX = 1, 100000
ALB_CORS_MAX_AGE_MIN, ALB_CORS_MAX_AGE_MAX = -1, 172800

VERDICT_NAME = {"🟢": "converted", "🟡": "behaviorChange",
                "🔴": "notSupported", "🚫": "downgraded"}


def bool_value(v):
    """Return (canonical, is_bool); canonical is 'true' or 'false'."""
    s = v.strip().strip("\"'")
    if s not in BOOL_OK:
        return None, False
    return ("true" if s.lower() in ("1", "t", "true") else "false"), True


def host_matches(tls_host, rule_host):
    """Matches hostMatches in the source: exact (case-insensitive) or *.suffix over one label."""
    if not rule_host:
        return False
    if tls_host.lower() == rule_host.lower():
        return True
    if not tls_host.startswith("*."):
        return False
    label, dot, rest = rule_host.partition(".")
    return bool(dot) and bool(label) and rest.lower() == tls_host[2:].lower()


def tls_coverage(rec):
    """Return (rules covered by a certificate, rules not covered); None when tls is unknown."""
    if rec["tls"] is None:
        return None
    covered = plain = 0
    for h in rec["hosts"]:
        hit = False
        for entry in rec["tls"]:
            if not entry:          # a tls entry with no hosts covers everything
                hit = True
                break
            if any(host_matches(th, h) for th in entry):
                hit = True
                break
        if hit:
            covered += 1
        else:
            plain += 1
    return covered, plain


if not HAVE_YAML:
    report("ℹ️  %s, using the built-in minimal parser (annotations and paths only). "
           "For complex YAML, pip install 'pyyaml>=%d.%d' for full parsing.\n"
           % (YAML_SKIP_REASON or "PyYAML is unavailable", PYYAML_MIN[0], PYYAML_MIN[1]))

total = {"ingress": 0, "green": 0, "yellow": 0, "red": 0, "downgraded": 0}
risky_paths = []
downgraded_ingresses = []
results = []


def add(rec, mark, key, value, target, note):
    """Record one finding for both the human report and the JSON."""
    rec["findings"].append({
        "key": key,
        "value": value,
        "verdict": VERDICT_NAME[mark],
        "target": target or None,
        "note": note.strip() or None,
    })


for path in sys.argv[1:]:
    for r in load(path):
        anns = r["annotations"]
        is_ing = r["kind"] == "Ingress" or any(k.startswith(P) for k in anns)
        if not is_ing:
            continue
        total["ingress"] += 1
        ns = r["namespace"] or "default"
        name = r["name"] or "<unnamed>"
        cls = r["class"] or anns.get("kubernetes.io/ingress.class") or "-"
        rec = {"file": path, "namespace": ns, "name": name, "class": cls,
               "findings": [], "pathNotes": []}
        results.append(rec)
        report(f"\n=== {ns}/{name}  (class={cls})  [{path}] ===")

        cov = tls_coverage(r)

        # Does this Ingress itself put its hosts into regex mode? Same criteria as the source
        # (regexAnnotations + taintedHostsByClass): use-regex counts only when its value is
        # **true**; or rewrite-target is present with a value different from the path it sits
        # on (when the value equals the path, nginx considers nothing rewritten).
        # ⚠️ Still a single-Ingress view — other Ingresses on the same host taint it too, and
        # that is a batch-level judgement.
        regex_declared = bool_value(anns.get(P + "use-regex", ""))[0] == "true"
        _rw = anns.get(P + "rewrite-target")
        _rwv = _rw.strip().strip("\"'") if _rw else ""
        regex_by_rw = bool(_rw) and any(_rwv != pp for pp, _ in r["paths"])
        regex_mode = regex_declared or regex_by_rw

        # Can upstream-hash-by become uch? That decides whether load-balance is overridden (🟡).
        uch_ok = False
        if (P + "upstream-hash-by") in anns:
            uch_ok = bool(re.match(r"^\$?arg_([A-Za-z0-9_-]+)$",
                                   anns[P + "upstream-hash-by"].strip().strip("\"'")))

        if not anns:
            report("  (no annotations)")
        for k in sorted(anns):
            v = anns[k]
            if k == "kubernetes.io/ingress.class":
                total["green"] += 1
                note = "dropped; the class name is carried by spec.ingressClassName"
                add(rec, "🟢", k, v, "spec.ingressClassName", note)
                report(f"  🟢 {k} = {v}\n      -> {note}")
                continue
            if not k.startswith(P):
                # Only what gets removed is reported 🔴; what is copied verbatim is reported 🟢
                # (source: notSupportFeature).
                if k.startswith(ALB_PREFIX) or k.startswith(TOOLING_PREFIXES):
                    continue
                if k.startswith(DROPPED_PREFIXES):
                    total["red"] += 1
                    note = ("not copied to the output (it configures a different ingress "
                            "controller, or would fight the source Ingress over one resource); "
                            "resolve it with the migration-patterns.md decision tree")
                    add(rec, "🔴", k, v, None, note)
                    report(f"  🔴 {k} = {v}\n      -> {note}")
                else:
                    total["green"] += 1
                    note = ("copied to the output verbatim (the tool did not translate it into "
                            "ALB behaviour, but did not remove it either); confirm case by case "
                            "whether keeping it is harmless")
                    add(rec, "🟢", k, v, k, note)
                    report(f"  🟢 {k} = {v}\n      -> {note}")
                continue

            short = k[len(P):]

            # A non-boolean value for a boolean annotation: the annotation is stripped and the
            # rest of the Ingress is still produced (a 🚫 downgrade, not a whole-source failure).
            if short in BOOL_ANNOTATIONS and not bool_value(v)[1]:
                total["downgraded"] += 1
                downgraded_ingresses.append(f"{ns}/{name}")
                note = ("the value is not a boolean (only true/false/1/0/t/f and their case "
                        "variants are accepted), so this annotation is stripped and the rest of "
                        "the Ingress is still produced. Write true/false and re-run. "
                        "See the downgrade table in SKILL.md Step 2")
                add(rec, "🚫", k, v, None, note)
                report(f"  🚫 {k} = {v}\n      -> {note}")
                continue

            if short in CONVERT:
                # Value-level judgement: some annotations convert by key but a particular value
                # has no ALB counterpart (🔴) or converts with different semantics (🟡). Never
                # blanket-label them 🟢, which would suggest the feature migrated untouched.
                # Each case corresponds to a branch in feature_*.go.
                mark, extra, ok = "🟢", "", True
                if short == "rewrite-target":
                    extra = ("  ($N -> ${N}; it also puts the host into regex mode and adds "
                             "use-regex=true. A value holding an nginx variable or a ? cannot be "
                             "expressed by ALB -> 🔴)")
                elif short == "use-regex":
                    if bool_value(v)[0] == "true":
                        mark = "🟡"
                        extra = ("  the output is matched by regex: ALB's regex is "
                                 "**case-sensitive** and nginx's ~* is not (measured: nginx "
                                 "serves /images/x from a /Images rule, ALB returns 503)")
                    else:
                        extra = ("  (value is false: ALB matches literally with no annotation, "
                                 "so the target is empty)")
                elif short == "limit-rps":
                    lv = v.strip().strip("\"'")
                    try:
                        rps = int(lv)
                    except ValueError:
                        rps = None
                    if rps is None or not (ALB_QPS_MIN <= rps <= ALB_QPS_MAX):
                        mark, ok = "🔴", False
                        extra = (f"  the value {lv} is outside ALB's {ALB_QPS_MIN}-{ALB_QPS_MAX}, "
                                 "so the annotation is dropped (no rate limiting)")
                    else:
                        mark = "🟡"   # a legal value **always** reports 🟡: that path in the source only has AddError
                        extra = ("  the same number lets very different traffic through: nginx "
                                 "counts per replica and allows a 5x burst by default, ALB counts "
                                 "once with no burst (measured at 5: nginx allowed 37, ALB 2); and "
                                 "this tool emits one rule per path, each counting independently. "
                                 "Must be measured")
                elif short == "cors-max-age":
                    cv = v.strip().strip("\"'")
                    try:
                        age = int(cv)
                    except ValueError:
                        age = None
                    if age is None or age < ALB_CORS_MAX_AGE_MIN:
                        mark, ok = "🔴", False
                        extra = (f"  the value {cv} is not an integer or is below "
                                 f"{ALB_CORS_MAX_AGE_MIN}, so the annotation is dropped")
                    elif age > ALB_CORS_MAX_AGE_MAX:
                        mark = "🟡"
                        extra = (f"  the value {cv} exceeds ALB's maximum and is clamped to "
                                 f"{ALB_CORS_MAX_AGE_MAX} (shorter preflight cache). nginx's "
                                 "default of 1728000 is exactly 10x the maximum")
                elif short == "ssl-redirect":
                    # It applies when "this Ingress has a tls block", regardless of which hosts
                    # the certificate covers (cluster-measured plus upstream docs, see
                    # annotation-mapping.md §6.2); the tool implements it this way.
                    if bool_value(v)[0] != "true":
                        extra = "  (value is false: neither side redirects, a faithful conversion)"
                    elif r["tls"] is None:
                        extra = ("  ⚠️ spec.tls could not be parsed (no PyYAML), so this cannot be "
                                 "judged — verify by hand per annotation-mapping.md §6.2")
                    elif not r["tls"]:
                        extra = ("  (this Ingress has no spec.tls block: nginx does not redirect and "
                                 "neither will the output, so the target is empty — copying it "
                                 "across would 308 to an HTTPS endpoint that does not exist)")
                    else:
                        extra = ("  (has a spec.tls block -> every host redirects, regardless of "
                                 "certificate coverage)")
                elif short == "canary":
                    extra = "  (the order is computed from the path length, see generated-resources.md §5b)"
                elif short in ("canary-weight", "canary-weight-total"):
                    tot = anns.get(P + "canary-weight-total", "").strip().strip("\"'")
                    has_weight = (P + "canary-weight") in anns
                    if not has_weight:
                        # A total on its own has no numerator to fold into, so the tool does not
                        # consume it and the catch-all reports 🔴.
                        mark, ok = "🔴", False
                        extra = "  there is no canary-weight to fold into; on its own it means nothing"
                    elif tot:
                        try:
                            t = int(tot)
                        except ValueError:
                            t = 0
                        if t <= 0:
                            mark, ok = "🔴", False
                            extra = (f"  canary-weight-total={tot} is not a positive integer, so the "
                                     "weight cannot be scaled and the annotation is dropped")
                        else:
                            w = anns.get(P + "canary-weight", "0").strip().strip("\"'")
                            try:
                                wi = int(w)
                            except ValueError:
                                wi = -1
                            if wi < 0:
                                mark, ok = "🔴", False
                                extra = (f"  canary-weight={w} is not a non-negative integer, so the "
                                         "annotation is dropped")
                            else:
                                pct = min(wi, t) * 100 // t
                                if min(wi, t) * 100 % t:
                                    mark = "🟡"
                                extra = (f"  {w}/{tot} scales to {pct} percent for ALB (ALB reads "
                                         "canary-weight with no denominator, so copying it verbatim "
                                         "multiplies the canary traffic)")
                elif short == "load-balance":
                    lv = v.strip().strip("\"'")
                    m2 = {"round_robin": "wrr", "least_conn": "wlc", "ip_hash": "sch"}
                    if lv in m2 and uch_ok:
                        mark = "🟡"
                        extra = (f"  the value {lv} -> {m2[lv]}, but a convertible upstream-hash-by "
                                 "is present too: ALB has a single backend-scheduler field, so the "
                                 "consistent hash (uch) **overrides** it and this algorithm never "
                                 "takes effect")
                    elif lv in m2:
                        extra = f"  (the value {lv} -> {m2[lv]})"
                    else:
                        mark, ok = "🔴", False
                        extra = (f"  the value {lv} has no ALB scheduling counterpart (only "
                                 "wrr/wlc/sch/uch), so it needs a human choice; ewma is in this class")
                elif short == "upstream-hash-by":
                    hv = v.strip().strip("\"'")
                    m3 = re.match(r"^\$?arg_([A-Za-z0-9_-]+)$", hv)
                    if m3:
                        extra = (f"  (hashes the query-string parameter {m3.group(1)}; "
                                 "backend-scheduler: uch must be set as well)")
                    else:
                        mark, ok = "🔴", False
                        extra = ("  ALB's consistent hash only supports a query-string parameter "
                                 f"(uch-value is the parameter name), so {hv} cannot be expressed "
                                 "and needs manual work")
                elif short == "backend-protocol":
                    u = v.strip().strip("\"'").upper()
                    grpc_no_tls = u in ("GRPC", "GRPCS") and r["tls"] == []
                    if grpc_no_tls:
                        mark, ok = "🚫", False
                        extra = ("  🚨 grpc but this Ingress has no spec.tls: the output always "
                                 "declares HTTP:80, and the controller requires ssl-redirect=true "
                                 "for grpc on an HTTP listener, or the whole AlbConfig model build "
                                 "fails and every Ingress on that ALB stops getting rules. So "
                                 "backend-protocol is stripped and a plain HTTP Ingress is emitted; "
                                 "add spec.tls, then put backend-protocol back")
                    elif u in ("HTTP", "HTTPS", "GRPC"):
                        extra = f"  (the value {u} -> {u.lower()}; ALB is case-sensitive, so it must be lower-cased)"
                        if u == "GRPC":
                            extra += ("; spec.tls is present, so the tool forces ssl-redirect=true "
                                      "and reports it as a behaviour change")
                    elif u == "GRPCS":
                        mark = "🟡"
                        extra = ("  GRPCS -> grpc: ALB has no grpcs, so after the downgrade ALB no "
                                 "longer speaks TLS to the backend — confirm the backend semantics; "
                                 "the tool also forces ssl-redirect=true")
                    else:
                        mark, ok = "🔴", False
                        extra = f"  the value {u} has no ALB counterpart (AUTO_HTTP/FCGI and the like); needs manual work"

                if mark == "🚫":
                    total["downgraded"] += 1
                    downgraded_ingresses.append(f"{ns}/{name}")
                    tgt = f"      -> annotation stripped, the rest is still produced{extra}"
                    add(rec, mark, k, v, None, extra)
                elif ok:
                    total["yellow" if mark == "🟡" else "green"] += 1
                    tgt = f"      -> alb.ingress.kubernetes.io/{CONVERT[short]}{extra}"
                    add(rec, mark, k, v, ALB_PREFIX + CONVERT[short], extra)
                else:
                    total["red"] += 1
                    tgt = f"      -> this value is not supported and needs manual work{extra}"
                    add(rec, mark, k, v, None, extra)
                report(f"  {mark} {k} = {v}\n{tgt}")

                # One annotation can carry two verdicts: when the regex came from
                # rewrite-target, besides its own 🟢 it also gets a 🟡 for switching the host
                # into regex matching.
                if short == "rewrite-target" and regex_by_rw and not regex_declared:
                    total["yellow"] += 1
                    note = ("it puts the host into regex mode, and ALB's regex is case-sensitive "
                            "while nginx's ~* is not")
                    add(rec, "🟡", k, v, ALB_PREFIX + "use-regex", note)
                    report(f"  🟡 {k} = {v}\n      -> {ALB_PREFIX}use-regex  {note}")
            else:
                # Catch-all: not in CONVERT = unsupported (nginx-prefixed ones are never copied).
                total["red"] += 1
                note = ("unsupported, and not copied to the output; resolve it with the "
                        "four-level decision tree in migration-patterns.md")
                add(rec, "🔴", k, v, None, note)
                report(f"  🔴 {k} = {v}\n      -> {note}")
                if short in TRAP_NOTES:
                    rec["findings"][-1]["trap"] = TRAP_NOTES[short]
                    report(f"      {TRAP_NOTES[short]}")

        # 🟡 A canary disagreeing with its main about TLS/redirect: listen-ports is derived per
        # Ingress from that Ingress's own spec.tls, whereas nginx merges the canary into the
        # main's location. So a canary with no tls block only lands on the 80 listener — there
        # is no rule for it on the 443 the main actually serves, and the split stops working.
        is_canary = bool_value(anns.get(P + "canary", ""))[0] == "true"
        if is_canary and not r["tls"]:
            total["yellow"] += 1
            note = ("no 443 rule will exist for this canary, so the traffic split stops working "
                    "over HTTPS; and when the main had ssl-redirect forced on for grpc, the "
                    "canary's lower order matches first without redirecting. Fix: give the canary "
                    "the same spec.tls as its main before migrating")
            add(rec, "🟡", P + "canary", "true", None,
                "this canary has no spec.tls while its main may have one, so the output only "
                "declares HTTP:80. " + note)
            report("  🟡 this canary has no spec.tls, and if its main has one the output only "
                   f"declares HTTP:80\n      -> {note}")

        # 🟡 Behaviour change: canary-weight combined with canary-by-header/cookie
        if (P + "canary-weight") in anns and (
            (P + "canary-by-header") in anns or (P + "canary-by-cookie") in anns
        ):
            total["yellow"] += 1
            note = ("ALB's semantics differ, so the canary method must be confirmed by a human "
                    "(weight or header/cookie — pick one)")
            add(rec, "🟡", P + "canary-weight", anns[P + "canary-weight"], None,
                "used together with canary-by-header/-by-cookie. " + note)
            report(f"  🟡 canary-weight together with canary-by-header/-by-cookie -> {note}")

        # Path risks. Note this script only judges at the annotation level and **does not
        # predict the final path** — how a path is written depends on whether its host is in
        # regex mode (any Ingress on that host carrying use-regex/rewrite-target taints it),
        # which is a batch-level judgement needing every document in view. See
        # references/generated-resources.md §5.
        host_regex = regex_mode
        for pp, pt in r["paths"]:
            meta = any(c in pp for c in "()[]{}|^$\\")
            wild = any(c in pp for c in "*?")
            if pt is None:
                # The source has no pathType -> the tool guesses ImplementationSpecific and
                # flags it, rather than refusing to produce anything.
                total["downgraded"] += 1
                downgraded_ingresses.append(f"{ns}/{name}")
                note = ("this path has **no pathType**; the output guesses "
                        "ImplementationSpecific, which is closest to what nginx does with an "
                        "unset type. Prefix and Exact would each give a different hit set, so "
                        "confirm it")
                rec["pathNotes"].append({"path": pp, "pathType": None,
                                         "verdict": "downgraded", "note": note})
                report(f"  🚫 path={pp} -> {note}")
                continue
            if host_regex:
                if pt != "Prefix":
                    note = ("this host is in regex mode, so the pathType becomes Prefix and the "
                            "path is kept as written")
                    rec["pathNotes"].append({"path": pp, "pathType": pt,
                                             "verdict": "info", "note": note})
                    report(f"  📐 path={pp} ({pt}) -> {note}")
            elif meta or wild:
                # Outside regex mode ALB rejects these characters, so the tool adds use-regex
                # and puts the path on Prefix rather than emitting an illegal literal.
                risky_paths.append(f"{ns}/{name}: {pp} ({pt})")
                total["downgraded"] += 1
                downgraded_ingresses.append(f"{ns}/{name}")
                note = ("holds characters ALB will not accept as a literal while this Ingress "
                        "declares no use-regex/rewrite-target. The output adds "
                        "use-regex: \"true\" and puts the path on Prefix — never emit it as a "
                        "literal, because ALB rejects it and that error stops rule updates for "
                        "the entire load balancer. Verify the regex, and note ALB's regex is "
                        "case-sensitive")
                rec["pathNotes"].append({"path": pp, "pathType": pt,
                                         "verdict": "downgraded", "note": note})
                report(f"  🚫 path={pp} ({pt}) -> {note}")
            elif pt == "ImplementationSpecific":
                if pp == "":
                    note = ("the output is path: / with pathType: Prefix (**not** an appended *)")
                    rec["pathNotes"].append({"path": pp, "pathType": pt,
                                             "verdict": "info", "note": note})
                    report(f"  📐 path=(empty) ({pt}) -> {note}")
                else:
                    note = f"a * is appended to express prefix matching: {pp}*"
                    rec["pathNotes"].append({"path": pp, "pathType": pt,
                                             "verdict": "info", "note": note})
                    report(f"  📐 path={pp} ({pt}) -> {note}")

report("\n" + "=" * 60)
report(f"Ingresses: {total['ingress']}  🟢 converted: {total['green']}  "
       f"🟡 behaviour change: {total['yellow']}  🔴 unsupported: {total['red']}  "
       f"🚫 downgraded: {len(set(downgraded_ingresses))}")
if downgraded_ingresses:
    report("\n🚫 The following Ingresses were downgraded. All three resources are still "
           "produced — check each repair before applying:")
    for x in sorted(set(downgraded_ingresses)):
        report("   -", x)
if total["yellow"]:
    report("\n🟡 Behaviour changes present: converted successfully but the semantics may differ. "
           "Confirm each per the notes above; rate limiting and regex case-sensitivity must be "
           "measured.")
if risky_paths:
    report("\n🚫 The following paths were rewritten as regexes (ALB rejects these characters as "
           "literals, and the host had no regex annotation):")
    for x in risky_paths:
        report("   -", x)
if total["red"]:
    report("\n👉 Unsupported annotations present: resolve each with the "
           "references/migration-patterns.md decision tree before migrating.")
    report("   ⚠️ **🔴 does not mean unmigratable**: a good share of 🔴 items have an ALB-side "
           "route (a native annotation, or instance- and listener-side configuration), and some "
           "are safe to drop.\n"
           "   This script only judges 'the tool did not convert it automatically', not 'whether "
           "it can be reworked' — reading this output alone **systematically understates** how "
           "migratable the input is. Walk the four-level tree for each item.")

json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write("\n")
PY
