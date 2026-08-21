#!/usr/bin/env python3
"""normalize_diff.py — normalized diff of two config/index objects.

Produces a stable, semantics-preserving diff between a "before" snapshot (from
`aliyun sls get-logtail-pipeline-config` / `get-index`) and an "after" target,
so the user approves exactly what changes. Normalizes object-key order but
preserves every array order: processor order and SourceKeys/DestKeys positions
are semantic and must never be sorted away.

Protocol: stdout = single JSON object {tool,status,changed,added,removed,modified};
          stderr = diagnostics; exit 0 no change, 3 has changes, 2 usage error.
(exit 3 lets a caller distinguish "identical" from "differs" without parsing.)

Usage:
  python3 scripts/normalize_diff.py --before old.json --after new.json [--kind config|index]
"""
import argparse
import json
import os
import sys


def die(msg, code=2):
    sys.stderr.write("[normalize_diff] %s\n" % msg)
    sys.exit(code)


def load(path):
    if not os.path.isfile(path):
        die("file not found: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as e:
            die("%s is not valid JSON: %s" % (path, e))


def unwrap(doc, kind):
    """Accept raw object or render/get output wrappers."""
    if not isinstance(doc, dict):
        return doc

    wrappers = [
        key
        for key in ("config", "index", "body")
        if key in doc and isinstance(doc[key], (dict, list))
    ]
    if kind == "auto":
        if len(wrappers) > 1:
            die(
                "ambiguous wrapper contains %s; pass --kind config or --kind index"
                % ", ".join(wrappers)
            )
        return doc[wrappers[0]] if wrappers else doc

    if kind in wrappers:
        return doc[kind]
    if "body" in wrappers and not any(
        key in wrappers for key in ("config", "index")
    ):
        return doc["body"]
    opposite = "index" if kind == "config" else "config"
    if opposite in wrappers:
        die("requested --kind %s but input contains only %s" % (kind, opposite))
    return doc


def normalize(obj):
    """Recursively sort dict keys while preserving semantic list order."""
    if isinstance(obj, dict):
        return {k: normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [normalize(x) for x in obj]
    return obj


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        if not obj:
            out[prefix] = {"__normalized_container__": "object"}
        for k, v in obj.items():
            out.update(flatten(v, "%s.%s" % (prefix, k) if prefix else str(k)))
    elif isinstance(obj, list):
        if not obj:
            out[prefix] = {"__normalized_container__": "array"}
        for i, v in enumerate(obj):
            out.update(flatten(v, "%s[%d]" % (prefix, i)))
    else:
        out[prefix] = obj
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--before", required=True, help="snapshot JSON (get-* output)")
    ap.add_argument("--after", required=True, help="target JSON")
    ap.add_argument("--kind", choices=["config", "index", "auto"], default="auto")
    args = ap.parse_args()

    before = normalize(unwrap(load(args.before), args.kind))
    after = normalize(unwrap(load(args.after), args.kind))

    fb, fa = flatten(before), flatten(after)
    keys = set(fb) | set(fa)
    added, removed, modified = {}, {}, {}
    for k in sorted(keys):
        if k not in fb:
            added[k] = fa[k]
        elif k not in fa:
            removed[k] = fb[k]
        elif fb[k] != fa[k]:
            modified[k] = {"before": fb[k], "after": fa[k]}

    changed = bool(added or removed or modified)
    out = {
        "tool": "normalize_diff",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        "kind": args.kind,
        "status": "changed" if changed else "identical",
        "changed": changed,
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": {"added": len(added), "removed": len(removed), "modified": len(modified)},
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 3 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
