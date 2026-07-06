#!/usr/bin/env python3
"""
Lightweight regex-based RunScript sandbox pre-checker.
Catches common agent coding mistakes before remote validation.
Zero dependencies — pure stdlib regex only.

Usage:
    python3 check_sandbox.py <script.py> [...]
    python3 check_sandbox.py --dir <dir>
"""
from __future__ import annotations

import re
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# ── Rules ────────────────────────────────────────────────────────────

IMPORT_WHITELIST = {
    "asyncio", "collections", "csv", "dataclasses", "datetime", "decimal",
    "enum", "fractions", "functools", "itertools", "json", "math", "re",
    "statistics", "string", "time", "typing", "uuid",
}

FORBIDDEN_FUNCS = [
    "eval", "exec", "compile", "__import__",
    "getattr", "setattr", "hasattr", "delattr",
    "globals", "locals", "vars",
]

# product.action → blocked (case-insensitive match)
BLOCKED_APIS = {
    "ram.listaccesskeys", "sts.assumerole",
    "kms.getsecretvalue", "ecs.describeuserdata",
}

CLI_META_PRODUCTS = {"configure", "plugin", "ossutil", "autocompletion"}

# ── API Metadata (public endpoint, no auth) ──
API_META_URL = "https://api.aliyun.com/meta/v1/products/{product}/versions/{version}/apis/{action}/api.json"
_API_DEF_CACHE = {}  # in-memory cache: "Product.Version.Action" → api def dict

SDK_PATTERNS = [
    (r'\bAcsClient\s*\(', "AcsClient"),
    (r'\bfrom\s+alibabacloud_\w+\.client\s+import', "alibabacloud SDK Client"),
    (r'\bClient\s*\([^)]*access_key', "SDK Client with credentials"),
]

Q = ("\"", "'")


def _str_val(pattern_body: str) -> str:
    """Build a regex that captures a string value in quotes."""
    return rf'["\']({pattern_body}?)["\']'


def check(source: str) -> list[dict]:
    """Return list of {rule_id, line, message, fix} violations."""
    violations = []
    lines = source.splitlines()
    has_result = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # ── SEC-4001: forbidden import ──
        m = re.match(r'^(?:import|from)\s+([\w.]+)', stripped)
        if m:
            mod = m.group(1).split(".")[0]
            if mod not in IMPORT_WHITELIST:
                violations.append({
                    "rule_id": "SEC-4001", "line": i,
                    "message": f"Forbidden import: {mod}",
                    "fix": f"Remove 'import {mod}'. Allowed: {', '.join(sorted(IMPORT_WHITELIST))}. "
                           f"call_cli is pre-injected — do not import it.",
                })

        # ── OBF-3018: print() ──
        if re.search(r'\bprint\s*\(', stripped):
            violations.append({
                "rule_id": "OBF-3018", "line": i,
                "message": "print() disallowed",
                "fix": "Remove print(); assign data to 'result' instead (dict or list).",
            })

        # ── SEC-4002: eval / exec / reflection ──
        for fn in FORBIDDEN_FUNCS:
            if re.search(rf'\b{fn}\s*\(', stripped):
                violations.append({
                    "rule_id": "SEC-4002", "line": i,
                    "message": f"Forbidden call: {fn}()",
                    "fix": f"Remove {fn}(). Sandbox blocks all reflection and dynamic code execution.",
                })

        # ── SEC-4002: input() ──
        if re.search(r'\binput\s*\(', stripped):
            violations.append({
                "rule_id": "SEC-4002", "line": i,
                "message": "input() disallowed",
                "fix": "Remove input(). The RunScript runtime handles user confirmation (HITL) automatically.",
            })

        # ── SEC-4005: SDK client instantiation ──
        for pattern, label in SDK_PATTERNS:
            if re.search(pattern, stripped):
                violations.append({
                    "rule_id": "SEC-4005", "line": i,
                    "message": f"SDK client detected: {label}",
                    "fix": "Remove SDK client code. Use call_cli(product, version, action, params) instead.",
                })

        # ── SEC-4006: open() for write ──
        m_open = re.search(r'\bopen\s*\(\s*["\']([^"\']+)["\']', stripped)
        if m_open:
            path = m_open.group(1)
            if not path.startswith("/tmp"):
                violations.append({
                    "rule_id": "SEC-4006", "line": i,
                    "message": f"open() outside /tmp: '{path}'",
                    "fix": "Only /tmp paths are writable. Use result variable to return data.",
                })

        # ── SLP-3001: time.sleep > 30 ──
        m_sleep = re.search(r'time\.sleep\s*\(\s*(\d+)', stripped)
        if m_sleep and int(m_sleep.group(1)) > 30:
            violations.append({
                "rule_id": "SLP-3001", "line": i,
                "message": f"time.sleep({m_sleep.group(1)}) > 30s",
                "fix": "Split into a loop: for _ in range(N): time.sleep(30)",
            })

        # ── result assignment ──
        if re.match(r'^\s*result\s*=', line):
            has_result = True

    # ── call_cli deep checks (whole-source) ──
    _check_call_cli(source, lines, violations)

    # ── API parameter validation (optional, graceful degradation) ──
    _check_api_params(source, violations)

    if not has_result:
        violations.append({
            "rule_id": "OUT-3001", "line": 0,
            "message": "No 'result = ...' assignment found",
            "fix": "Add 'result = <dict or list>' at the end of the script to return data.",
        })

    return violations


def _check_call_cli(source: str, lines: list[str], violations: list[dict]):
    """Parse call_cli() invocations and check product/action/params."""
    # Match call_cli(...) including multiline — find each invocation
    for m in re.finditer(r'call_cli\s*\(', source):
        start = m.start()
        line_no = source[:start].count('\n') + 1

        # Extract the full arg string (balanced parens, up to 500 chars)
        arg_str = _extract_balanced_parens(source, m.end() - 1)
        if not arg_str:
            continue

        # Extract product
        pm = re.search(r'product\s*=\s*["\']([^"\']+)["\']', arg_str)
        product = pm.group(1) if pm else ""

        # Extract action
        am = re.search(r'action\s*=\s*["\']([^"\']+)["\']', arg_str)
        action = am.group(1) if am else ""

        # ── CLI-META: forbidden product ──
        if product.lower() in CLI_META_PRODUCTS:
            violations.append({
                "rule_id": "CLI-META", "line": line_no,
                "message": f"Forbidden CLI meta product: '{product}'",
                "fix": f"'{product}' is a CLI meta command, not a cloud API. Use a real product name.",
            })

        # ── BLK-5001: blocked API ──
        api_key = f"{product}.{action}".lower()
        if api_key in BLOCKED_APIS:
            violations.append({
                "rule_id": "BLK-5001", "line": line_no,
                "message": f"Blocked API: {product}.{action}",
                "fix": f"{product}.{action} returns credentials/secrets and is blocked. Remove this call.",
            })


def _extract_balanced_parens(source: str, open_pos: int) -> str:
    """Extract content inside balanced () starting at open_pos. Max 2000 chars."""
    depth = 0
    end = min(open_pos + 2000, len(source))
    for i in range(open_pos, end):
        if source[i] == '(':
            depth += 1
        elif source[i] == ')':
            depth -= 1
            if depth == 0:
                return source[open_pos + 1:i]
    return source[open_pos + 1:end]


# ── API Parameter Validation (optional, public endpoint) ─────────────

def _fetch_api_def(product: str, version: str, action: str) -> dict | None:
    """Fetch API definition from public metadata endpoint. Memory cached only — no disk residue."""
    cache_key = f"{product}.{version}.{action}"

    # Memory cache (process-scoped, disappears on exit)
    if cache_key in _API_DEF_CACHE:
        return _API_DEF_CACHE[cache_key]

    # HTTP fetch (timeout=10s, no auth, no disk writes)
    url = API_META_URL.format(product=product, version=version, action=action)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "check-sandbox/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                _API_DEF_CACHE[cache_key] = data
                return data
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        pass
    return None


def _extract_api_params(api_def: dict) -> list[dict]:
    """Extract normalized parameter info from API definition JSON.

    Returns list of: {name, type, required, description, example}
    """
    result = []
    seen = set()
    for p in api_def.get("parameters", []):
        name = p.get("name", "")
        if not name or name in seen:
            continue
        seen.add(name)

        schema = p.get("schema", {})
        ptype = p.get("type") or schema.get("type", "string")
        required = p.get("required", False) or schema.get("required", False) or schema.get("docRequired", False)
        description = schema.get("description", "") or p.get("description", "")
        example = schema.get("example", "") or p.get("example", "")

        result.append({
            "name": name,
            "type": ptype.lower(),
            "required": required,
            "description": description[:100],
            "example": example,
        })
    return result


def _parse_params_dict(params_str: str) -> dict[str, tuple]:
    """Parse params={...} inner content into {key: (raw_value_str, inferred_type)}.

    Only extracts TOP-LEVEL keys (outside any parenthesized expression).
    Keys inside function calls like json.dumps({"Key": val}) are ignored.
    """
    # Find character spans inside function calls — these are NOT top-level
    skip_ranges = []
    for fm in re.finditer(r'\b\w+\s*\(', params_str):
        paren_start = params_str.index('(', fm.start())
        depth = 1
        i = paren_start + 1
        while i < len(params_str) and depth > 0:
            if params_str[i] == '(':
                depth += 1
            elif params_str[i] == ')':
                depth -= 1
            i += 1
        skip_ranges.append((paren_start, i))

    result = {}
    for m in re.finditer(
        r"""["'](\w+)["']\s*:\s*([^,}\n]+)""",
        params_str,
    ):
        # Skip keys that fall inside a function call (nested, not top-level)
        if any(lo <= m.start() < hi for lo, hi in skip_ranges):
            continue

        key = m.group(1)
        raw_val = m.group(2).strip()

        if re.match(r'^["\']', raw_val) or raw_val.startswith("f\"") or raw_val.startswith("f'"):
            vtype = "str_literal"
        elif re.match(r'^-?\d+(\.\d+)?$', raw_val):
            vtype = "number"
        elif raw_val in ("True", "False"):
            vtype = "bool"
        elif re.match(r'^[a-zA-Z_]\w*', raw_val):
            vtype = "variable"
        else:
            vtype = "other"

        result[key] = (raw_val, vtype)
    return result


def _fmt_param_info(p: dict) -> str:
    """Format one API param for display: 'Name (type, required/optional) - desc'."""
    parts = [p["name"], f"({p['type']}, {'required' if p['required'] else 'optional'})"]
    if p.get("description"):
        parts.append(f"- {p['description']}")
    return " ".join(parts)


def _check_api_params(source: str, violations: list[dict]):
    """Validate call_cli params against OpenAPI definitions from public metadata endpoint.

    Fetches https://api.aliyun.com/meta/v1/... (no auth, no disk writes) for each
    unique product/version/action, then checks:
      - API-PARAM-UNKNOWN:  param name not in API definition
      - API-PARAM-REQUIRED: required param missing
      - API-PARAM-TYPE:     param value type mismatches definition

    Graceful degradation: silently skips if API definition cannot be fetched.
    """
    for m in re.finditer(r'call_cli\s*\(', source):
        start = m.start()
        line_no = source[:start].count('\n') + 1

        arg_str = _extract_balanced_parens(source, m.end() - 1)
        if not arg_str:
            continue

        pm = re.search(r'product\s*=\s*["\']([^"\']+)["\']', arg_str)
        product = pm.group(1) if pm else ""
        vm = re.search(r'version\s*=\s*["\']([^"\']+)["\']', arg_str)
        version = vm.group(1) if vm else ""
        am = re.search(r'action\s*=\s*["\']([^"\']+)["\']', arg_str)
        action = am.group(1) if am else ""

        if not all([product, version, action]):
            continue

        api_tag = f"{product}.{action}"

        # Extract params dict content
        params_m = re.search(r'params\s*=\s*\{([^}]+)\}', arg_str, re.DOTALL)
        if not params_m:
            # Check if params is a variable reference (e.g. params=p) — cannot validate
            if re.search(r'params\s*=\s*[a-zA-Z_]\w*', arg_str):
                continue
            # params={} or truly absent — check for required params
            try:
                api_def = _fetch_api_def(product, version, action)
                if api_def:
                    for ap in _extract_api_params(api_def):
                        if ap["required"]:
                            eg = f" Example: {ap['example']}" if ap.get("example") else ""
                            violations.append({
                                "rule_id": "API-PARAM-REQUIRED", "line": line_no,
                                "message": f"{api_tag}: required param '{ap['name']}' ({ap['type']}) not provided. {ap['description']}",
                                "fix": f"Add '{ap['name']}' to params.{eg}",
                            })
            except Exception:
                pass
            continue

        call_params = _parse_params_dict(params_m.group(1))

        # Fetch API definition (memory-cached, no disk I/O)
        try:
            api_def = _fetch_api_def(product, version, action)
        except Exception:
            continue
        if not api_def:
            continue

        api_params = _extract_api_params(api_def)
        if not api_params:
            continue

        api_param_map = {p["name"]: p for p in api_params}

        # --- API-PARAM-UNKNOWN: param name not in definition ---
        for pname in call_params:
            if pname not in api_param_map:
                valid_list = "\n".join(
                    f"  - {_fmt_param_info(p)}" for p in sorted(api_params, key=lambda x: x["name"])
                )
                violations.append({
                    "rule_id": "API-PARAM-UNKNOWN", "line": line_no,
                    "message": (
                        f"{api_tag}: param '{pname}' does not exist in the OpenAPI definition.\n"
                        f"Valid params for {api_tag}:\n{valid_list}"
                    ),
                    "fix": f"Remove '{pname}' from params or replace with a valid param name above.",
                })

        # --- API-PARAM-REQUIRED: required param missing ---
        for ap in api_params:
            if ap["required"] and ap["name"] not in call_params:
                eg = f" Example: {ap['example']}" if ap.get("example") else ""
                violations.append({
                    "rule_id": "API-PARAM-REQUIRED", "line": line_no,
                    "message": (
                        f"{api_tag}: required param '{ap['name']}' ({ap['type']}) missing. "
                        f"{ap['description']}"
                    ),
                    "fix": f"Add '{ap['name']}' to params.{eg}",
                })

        # --- API-PARAM-TYPE: type mismatch for literal values ---
        for pname, (raw_val, vtype) in call_params.items():
            if pname not in api_param_map or vtype == "variable":
                continue

            ap = api_param_map[pname]
            expected = ap["type"]
            eg_hint = f" Example from API: {ap['example']}" if ap.get("example") else ""
            type_hint = f"API expects {expected}."

            if expected in ("integer", "long", "int", "int32", "int64"):
                if vtype == "str_literal":
                    inner = raw_val.strip("'\"")
                    if not re.match(r'^-?\d+$', inner):
                        violations.append({
                            "rule_id": "API-PARAM-TYPE", "line": line_no,
                            "message": f"{api_tag}: '{pname}' expects integer, got non-numeric string {raw_val[:50]}. {type_hint}",
                            "fix": f"Remove quotes — pass an integer literal for '{pname}'.{eg_hint}",
                        })
                elif vtype == "bool":
                    violations.append({
                        "rule_id": "API-PARAM-TYPE", "line": line_no,
                        "message": f"{api_tag}: '{pname}' expects integer, got boolean {raw_val}. {type_hint}",
                        "fix": f"Pass an integer for '{pname}'.{eg_hint}",
                    })

            elif expected in ("float", "double", "number", "decimal"):
                if vtype == "str_literal":
                    inner = raw_val.strip("'\"")
                    if not re.match(r'^-?\d+(\.\d+)?$', inner):
                        violations.append({
                            "rule_id": "API-PARAM-TYPE", "line": line_no,
                            "message": f"{api_tag}: '{pname}' expects number, got non-numeric string {raw_val[:50]}. {type_hint}",
                            "fix": f"Remove quotes — pass a numeric literal for '{pname}'.{eg_hint}",
                        })
                elif vtype == "bool":
                    violations.append({
                        "rule_id": "API-PARAM-TYPE", "line": line_no,
                        "message": f"{api_tag}: '{pname}' expects number, got boolean {raw_val}. {type_hint}",
                        "fix": f"Pass a number for '{pname}'.{eg_hint}",
                    })

            elif expected == "boolean":
                if vtype == "str_literal":
                    inner = raw_val.strip("'\"").lower()
                    if inner not in ("true", "false"):
                        violations.append({
                            "rule_id": "API-PARAM-TYPE", "line": line_no,
                            "message": f"{api_tag}: '{pname}' expects boolean, got {raw_val[:50]}. {type_hint}",
                            "fix": f"Pass True or False (Python bool) for '{pname}'.{eg_hint}",
                        })
                elif vtype == "number":
                    violations.append({
                        "rule_id": "API-PARAM-TYPE", "line": line_no,
                        "message": f"{api_tag}: '{pname}' expects boolean, got number {raw_val}. {type_hint}",
                        "fix": f"Pass True or False for '{pname}', not a number.{eg_hint}",
                    })

            elif expected == "array":
                if vtype == "str_literal":
                    violations.append({
                        "rule_id": "API-PARAM-TYPE", "line": line_no,
                        "message": f"{api_tag}: '{pname}' expects array, got string {raw_val[:50]}. {type_hint}",
                        "fix": f"Pass a Python list for '{pname}', e.g. ['value1', 'value2'].{eg_hint}",
                    })

            # string type: most params accept string, skip


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: check_sandbox.py <script.py> [...] | --dir <dir>")
        sys.exit(1)

    files = []
    if sys.argv[1] == "--dir":
        files = sorted(Path(sys.argv[2]).glob("*.py"))
    else:
        files = [Path(f) for f in sys.argv[1:]]

    passed = failed = 0
    for f in files:
        vs = check(f.read_text())
        if not vs:
            print(f"  PASS  {f.name}")
            passed += 1
        else:
            print(f"  FAIL  {f.name} ({len(vs)})")
            for v in vs:
                ln = f"L{v['line']}" if v["line"] else "   "
                print(f"        {ln}  [{v['rule_id']}] {v['message']}")
                print(f"              → {v['fix']}")
            failed += 1

    total = passed + failed
    print(f"\n  {passed}/{total} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
