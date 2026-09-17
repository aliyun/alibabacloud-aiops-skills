#!/usr/bin/env python3
"""
_report.py -- Report rendering for OSS access-log trace diagnosis
=================================================================
SECURITY: READ-ONLY. Pure rendering over an already-collected payload; no cloud
call and no credential handling happens here.

Internal module (prefixed with `_`). Do NOT run directly except for
`--self-test`.

Two audiences are served from one payload:
  * generate_text_report  -- the human-readable report, including the STATUS and
    NEXT_ACTION contract lines, the matched policy statement quoted verbatim,
    the per-condition hit table, the generated console statements, the official
    documentation verification block, the mandatory Information Sources
    (auto-fill declarations), and the verified / could-NOT-be-verified split;
  * build_summary_fields  -- the machine-consumable summary / key_findings /
    suggestions triple consumed by a later stage.

Self-test:
  python3 _report.py --self-test
"""

from __future__ import annotations

import json

import trace_request

def generate_text_report(payload: dict) -> str:
    """Render the human-readable report."""
    lines: list[str] = []
    row = payload.get("traced_row") or {}
    knowledge = payload.get("knowledge") or {}
    facts = payload.get("facts") or {}

    lines.append("=" * 74)
    lines.append("OSS access-log trace diagnosis")
    lines.append("=" * 74)
    lines.append(f"  STATUS          : {payload.get('status', '-')}")
    lines.append(f"  Bucket          : {payload['bucket']}")
    lines.append(f"  Region          : {payload['region']} "
                 f"(source: {payload.get('region_source', '-')})")
    lines.append(f"  Endpoint        : {payload.get('endpoint') or '-'}")
    lines.append(f"  UID             : {payload.get('uid') or '-'} "
                 f"({payload.get('uid_source', '-')})")
    lines.append(f"  Log project     : {payload.get('log_project') or '-'}")
    lines.append(f"  Log probe       : {payload.get('probe_status', '-')}")
    lines.append(f"  Log readable    : {payload.get('log_usable')}")
    lines.append(f"  Log channel     : "
                 f"{'available' if payload.get('channel_available') else 'UNAVAILABLE'}")
    lines.append(f"  Window          : last "
                 f"{payload['window']['seconds'] // 3600}h")
    lines.append(f"  Session id      : {payload.get('session_id', '-')}")
    lines.append(f"  NEXT_ACTION     : {payload.get('next_action', '-')}")
    lines.append("-" * 74)

    if row:
        lines.append("Traced request")
        lines.append("-" * 74)
        for line in trace_request.render_request_row(row):
            lines.append(line)
        lines.append("-" * 74)
    else:
        lines.append("Traced request : no logged row was available")
        lines.append("-" * 74)

    lines.append("Error identification")
    lines.append(f"  EC              : {knowledge.get('ec', '-')}")
    lines.append(f"  Error code      : {knowledge.get('error_code', '-')}")
    lines.append(f"  HTTP status     : {knowledge.get('http_status', '-')}")
    lines.append(f"  Meaning         : {knowledge.get('meaning') or '-'}")
    lines.append(f"  Resolved by     : {knowledge.get('matched_by', '-')}")
    if knowledge.get("doc"):
        lines.append(f"  Public doc      : {knowledge['doc']}")
    lines.append(f"  Verdict class   : {payload.get('verdict_class', '-')} "
                 f"- {payload.get('verdict_label', '')}")
    if payload.get("verdict_downgraded"):
        lines.append(f"  Verdict note    : {payload['verdict_downgraded']}")
    lines.append("-" * 74)

    lines.append("Conclusion")
    lines.append(f"  {payload.get('conclusion') or '-'}")
    lines.append("")
    lines.append("Root cause")
    for text in str(payload.get("root_cause") or "-").splitlines() or ["-"]:
        lines.append(f"  {text}")
    lines.append("")
    lines.append("Recommendations")
    for index, item in enumerate(payload.get("recommendations") or [], 1):
        lines.append(f"  {index}. {item}")
    lines.append("-" * 74)

    lines.append("Configuration evidence")
    # Anti-fabrication (KB 04 L4): when a read failed, render an explicit
    # UNAVAILABLE placeholder so a verbatim relay can never turn an unread
    # item into a concrete value. Never let a failed read silently default to
    # '-' / False / 0, which a weak model would report as a verified fact.
    _unavail = "UNAVAILABLE (not verified -- the read failed; do NOT state a value)"
    _acl = facts.get('bucket_acl')
    _acl_render = _acl if (_acl and facts.get('acl_source') != 'unavailable') else _unavail
    lines.append(f"  Bucket ACL           : {_acl_render}")
    _bpa_render = (facts.get('block_public_access')
                   if facts.get('block_public_access_available') else _unavail)
    lines.append(f"  Block public access  : {_bpa_render}")
    if facts.get('policy_available', True):
        lines.append(f"  Policy statements    : "
                     f"{facts.get('policy_statement_count', 0)} "
                     f"(Deny: {facts.get('policy_deny_count', 0)})")
    else:
        lines.append(f"  Policy statements    : {_unavail}")
    lines.append(f"  Anonymous read       : {facts.get('anonymous_read_possible')}")
    lines.append(f"  Anonymous list       : {facts.get('anonymous_list_possible')}")
    lines.append(f"  Created              : {facts.get('creation_date') or '-'}")
    lines.append(f"  Versioning           : {facts.get('versioning') or '-'}")

    condition_analysis = (payload.get("evidence") or {}).get("condition_analysis")
    if condition_analysis:
        lines.append("")
        lines.append("Policy condition hit analysis")
        for block in condition_analysis:
            lines.append(f"  statement #{block['statement_index']}:")
            for condition in block["conditions"]:
                state = {True: "MET", False: "not met",
                         None: "not evaluable"}.get(condition["matched"], "-")
                lines.append(
                    f"    {condition['operator']:<16} "
                    f"{condition['condition_key']:<24} "
                    f"expected={condition['expected']} "
                    f"actual='{condition['actual']}' -> {state}")
                if condition.get("note"):
                    lines.append(f"      note: {condition['note']}")

    matched = (payload.get("evidence") or {}).get("matched_statements")
    if matched:
        lines.append("")
        lines.append("Matched policy statement(s), verbatim")
        for index, statement in enumerate(matched, 1):
            rendered = json.dumps(statement, ensure_ascii=False, indent=2)
            lines.append(f"  [{index}] " + rendered.replace("\n", "\n      "))

    grammar = (payload.get("evidence") or {}).get("policy_grammar_warnings")
    if grammar:
        lines.append("")
        lines.append("Policy grammar problems found")
        for item in grammar:
            lines.append(f"  ! {item}")

    relation = payload.get("account_relation") or {}
    if relation:
        lines.append("")
        lines.append("Caller account relation")
        lines.append(f"  Cross-account   : {relation.get('cross_account')}")
        lines.append(f"  Basis           : {relation.get('basis', '-')}")
        if relation.get("role_name"):
            lines.append(f"  Assumed role    : {relation['role_name']}")
            lines.append(f"  Role owner UID  : {relation.get('role_owner_id', '-')}")

    referer = payload.get("referer") or {}
    if referer:
        lines.append("")
        lines.append("Hotlink protection")
        lines.append(f"  Allow empty referer : {referer.get('allow_empty_referer')}")
        lines.append(f"  Whitelist entries   : "
                     f"{referer.get('whitelist_count', 0)}")
        for item in (referer.get("whitelist") or [])[:20]:
            lines.append(f"    - {item}")
        if referer.get("blacklist_count"):
            lines.append(f"  Blacklist entries   : "
                         f"{referer.get('blacklist_count', 0)}")
            for item in (referer.get("blacklist") or [])[:20]:
                lines.append(f"    ! {item}")

    ram = payload.get("ram_evidence") or {}
    if ram.get("queried"):
        lines.append("")
        lines.append("RAM evidence")
        lines.append(f"  Policies scanned    : {len(ram.get('policies') or [])}")
        lines.append(f"  Explicit Deny found : {len(ram.get('deny_statements') or [])}")
        if ram.get("role"):
            lines.append(f"  Role trusts OSS svc : {ram.get('oss_service_trusted')}")

    if payload.get("post_policy"):
        lines.append("")
        lines.append("Decoded form-upload policy")
        for key, value in payload["post_policy"].items():
            lines.append(f"  {key:<28}: {value}")

    if payload.get("escalation_package"):
        lines.append("-" * 74)
        lines.append("Support ticket package (attach this to your ticket)")
        for key, value in payload["escalation_package"].items():
            if isinstance(value, list):
                lines.append(f"  {key}:")
                for item in value:
                    lines.append(f"    - {item}")
            else:
                lines.append(f"  {key}: {value}")

    batch_rows = payload.get("batch_delete_rows") or []
    if batch_rows:
        lines.append("")
        lines.append(f"Batch-delete topic rows ({len(batch_rows)})")
        lines.append("  A batch delete logs ONE request row in the access topic;")
        lines.append("  the removed keys below come from the batch-delete topic.")
        for item in batch_rows[:20]:
            lines.append(
                f"    {item.get('time', '-')}  {item.get('objectname', '-')}"
                f"  request_id={item.get('request_id', '-')}"
                f"  ua={item.get('user_agent', '-')}")

    generated = payload.get("generated_queries") or []
    if generated:
        lines.append("-" * 74)
        executed = bool(payload.get("log_usable"))
        heading = ("Console statements (also generated for reuse)" if executed
                   else "Console statements (generated, NOT executed here)")
        lines.append(heading)
        if not executed:
            lines.append("  NO log query was executed by this run. Run these in")
            lines.append(f"  the SLS console of region {payload.get('region')},")
            lines.append(f"  project {payload.get('log_project') or 'oss-log-<uid>-<region>'},")
            lines.append("  logstore oss-log-store, with the time picker set to")
            lines.append(f"  the incident window.")
        for item in generated:
            lines.append(f"  [{item['id']}] {item['title']}  "
                         f"(topic: {item['topic']})")
            lines.append(f"      {item['purpose']}")
            statement = item["statement"]
            while len(statement) > 92:
                cut = statement.rfind(" ", 0, 92)
                cut = cut if cut > 40 else 92
                lines.append(f"      {statement[:cut]}")
                statement = statement[cut:].lstrip()
            lines.append(f"      {statement}")

    doc_verification = payload.get("doc_verification") or {}
    if doc_verification:
        lines.append("-" * 74)
        lines.append("Official documentation verification")
        lines.append(f"  matched : {doc_verification.get('matched')}")
        lines.append(f"  source  : {doc_verification.get('source', '-')}")
        note = doc_verification.get("note")
        if note:
            lines.append(f"  note    : {note}")
            if str(note).startswith("DEGRADED"):
                lines.append("  Unable to verify against online official docs "
                             "(offline).")
        for doc in (doc_verification.get("docs") or [])[:3]:
            lines.append(f"  - {doc.get('title', '-')}")
            lines.append(f"    {doc.get('url', '-')}")
            excerpt = str(doc.get("excerpt") or "").replace("\n", " ")
            if excerpt:
                lines.append(f"    {excerpt[:240]}")
        if not doc_verification.get("docs"):
            lines.append("  No document was returned; cite none rather than "
                         "recalling a URL from memory.")

    autofill = payload.get("autofill_declarations") or []
    lines.append("-" * 74)
    lines.append("Information Sources (mandatory)")
    if autofill:
        for item in autofill:
            lines.append(f"  [auto-filled] {item}")
    else:
        lines.append("  No parameter was auto-filled; every input came from the "
                     "user.")

    lines.append("-" * 74)
    lines.append("What was verified")
    for item in payload.get("verified") or ["  (none)"]:
        lines.append(f"  + {item}")
    lines.append("What could NOT be verified")
    for item in payload.get("unverifiable") or ["  (none)"]:
        lines.append(f"  - {item}")
    lines.append("Graceful Degradation Log")
    for item in payload.get("degradation_log") or []:
        lines.append(f"  [WARN] {item}")
    if not payload.get("degradation_log"):
        lines.append("  none")
    lines.append("=" * 74)

    lines.append("")
    lines.append("Summary")
    lines.append("-------")
    lines.append(f"STATUS           : {payload.get('status', '-')}")
    lines.append(f"What was queried : the realtime access log of bucket "
                 f"{payload['bucket']} plus its authorization configuration.")
    lines.append(f"Key finding      : {payload.get('conclusion') or '-'}")
    lines.append(f"Verdict class    : {payload.get('verdict_class', '-')} "
                 f"({payload.get('verdict_label', '')}).")
    lines.append(f"NEXT_ACTION      : {payload.get('next_action', '-')}")
    lines.append("Note             : this skill is read-only and changed "
                 "nothing.")
    return "\n".join(lines)


def build_summary_fields(payload: dict) -> dict:
    """Attach the dual-audience summary fields consumed by a later stage."""
    payload["summary"] = (
        f"Diagnosed bucket {payload['bucket']} in {payload['region']}. "
        f"{payload.get('conclusion') or 'No conclusion could be drawn.'} "
        f"Verdict class {payload.get('verdict_class', '-')}: "
        f"{payload.get('verdict_label', '')}."
    )
    payload["key_findings"] = [
        f"EC {payload['knowledge'].get('ec', '-')} / "
        f"error code {payload['knowledge'].get('error_code', '-')} / "
        f"status {payload['knowledge'].get('http_status', '-')}",
        f"Verdict class {payload.get('verdict_class', '-')}",
        (f"Bucket ACL {payload['facts'].get('bucket_acl')}"
         if (payload['facts'].get('bucket_acl')
             and payload['facts'].get('acl_source') != 'unavailable')
         else "Bucket ACL UNAVAILABLE (not verified)"),
        (f"Policy statements {payload['facts'].get('policy_statement_count', 0)}, "
         f"Deny {payload['facts'].get('policy_deny_count', 0)}"
         if payload['facts'].get('policy_available', True)
         else "Policy statements UNAVAILABLE (not verified)"),
        (f"Block public access {payload['facts'].get('block_public_access')}"
         if payload['facts'].get('block_public_access_available')
         else "Block public access UNAVAILABLE (not verified)"),
        f"Log probe {payload.get('probe_status', '-')}",
    ]
    payload["suggestions"] = list(payload.get("recommendations") or [])
    return payload

# ---------------------------------------------------------------------------
# Inline boundary assertions
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Report rendering must survive an evidence-free payload."""
    skeleton = {"bucket": "b1", "region": "cn-hangzhou", "uid": "",
                "uid_source": "-", "log_project": "", "window": {"seconds": 0},
                "probe_status": "skipped", "traced_row": {}, "knowledge": {},
                "verdict_class": "B", "verdict_label": "", "conclusion": "",
                "root_cause": "", "recommendations": [], "evidence": {},
                "facts": {}, "account_relation": {}, "conditional_evidence": {},
                "ram_evidence": {}, "post_policy": {}, "escalation_package": {},
                "verified": [], "unverifiable": [], "degradation_log": []}
    text = generate_text_report(skeleton)
    # normal: the contract sections are always present
    assert "Conclusion" in text and "Graceful Degradation Log" in text, text[:200]
    assert "STATUS" in text and "NEXT_ACTION" in text
    assert "Information Sources (mandatory)" in text
    # boundary: a populated payload renders the extra sections too
    filled = dict(skeleton)
    filled["generated_queries"] = [{"id": "T3", "title": "t", "purpose": "p",
                                    "statement": "x" * 200,
                                    "topic": "oss_access_log"}]
    filled["doc_verification"] = {"matched": False, "docs": [],
                                  "source": "llms-index",
                                  "note": "DEGRADED: offline"}
    filled["autofill_declarations"] = ["UID auto-derived: 1"]
    filled["referer"] = {"allow_empty_referer": True, "whitelist_count": 1,
                         "whitelist": ["a"], "blacklist_count": 0, "blacklist": []}
    filled["batch_delete_rows"] = [{"time": "t", "objectname": "o",
                                    "request_id": "r", "user_agent": "u"}]
    text2 = generate_text_report(filled)
    assert "Console statements" in text2 and "T3" in text2
    assert "Unable to verify against online official docs" in text2
    assert "[auto-filled] UID auto-derived: 1" in text2
    assert "Batch-delete topic rows" in text2
    # invalid: missing optional keys must not raise
    assert generate_text_report({"bucket": "b", "region": "r",
                                 "window": {"seconds": 0}})
    assert build_summary_fields(dict(skeleton))["summary"]
    assert build_summary_fields(dict(skeleton))["key_findings"]
    print("report self-test passed")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
        sys.exit(0)
    print("internal module; run with --self-test", file=sys.stderr)
    sys.exit(2)
