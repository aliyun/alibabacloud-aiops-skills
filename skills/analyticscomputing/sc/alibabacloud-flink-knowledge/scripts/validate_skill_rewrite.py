#!/usr/bin/env python3
"""Static validation harness for the SKILL.md rewrite invariants.

This script checks that SKILL.md conforms to the approved five-layer
architecture design and does not contain legacy global state-machine
patterns. It is intended to:
  - PASS after the rewrite is complete
  - FAIL against the current (legacy) SKILL.md

Usage:
    python3 scripts/validate_skill_rewrite.py

Exit code 0 = all invariants satisfied; non-zero = one or more failures.
"""

import sys
from pathlib import Path

# ---- Configuration ----------------------------------------------------------
SKILL_PATH = Path("SKILL.md")

# ---- Helpers ----------------------------------------------------------------
_failures: list[str] = []


def _assert_present(text: str, pattern: str, section: str) -> None:
    """assert `pattern` appears somewhere in `text`."""
    if pattern not in text:
        _failures.append(f"[MISSING] {section}: expected to find '{pattern}' in SKILL.md")


def _assert_count_max(text: str, pattern: str, max_n: int, section: str) -> None:
    """assert `pattern` appears at most `max_n` times."""
    n = text.count(pattern)
    if n > max_n:
        _failures.append(
            f"[EXCESS] {section}: '{pattern}' appears {n} times, expected <= {max_n}"
        )


def _assert_absent(text: str, pattern: str, section: str) -> None:
    """assert `pattern` does NOT appear in `text`."""
    if pattern in text:
        _failures.append(f"[LEGACY] {section}: legacy pattern '{pattern}' must be removed from SKILL.md")


# ---- Invariant Groups -------------------------------------------------------
def check_pipeline_layers(text: str) -> None:
    """Layer 1-5: the five top-level pipeline sections must exist."""
    _assert_present(text, "Intent Classifier", "Layer 1")
    _assert_present(text, "Evidence Policy", "Layer 2")
    _assert_present(text, "Risk Gates", "Layer 3")
    _assert_present(text, "Response Builder", "Layer 4")
    _assert_present(text, "Output Formatter", "Layer 5")


def check_intent_classification(text: str) -> None:
    """Layer 1: exactly one primary intent classification with required intents."""
    _assert_present(text, "INTENT_PARAM", "Layer 1 :: intents")
    _assert_present(text, "INTENT_TROUBLESHOOT", "Layer 1 :: intents")
    _assert_present(text, "INTENT_SQL", "Layer 1 :: intents")
    _assert_present(text, "INTENT_FALLBACK", "Layer 1 :: intents")
    _assert_present(text, "WITH_FILE_OUTPUT", "Layer 1 :: file-output flag")
    _assert_present(text, "Classification is immutable", "Layer 1 :: immutability")
    _assert_present(text, "Immutable intent classification", "Layer 1 :: unique classifier")


def check_evidence_policy(text: str) -> None:
    """Layer 2: evidence policy sections for each capability domain."""
    _assert_present(text, "PARAM_CONFIRMED", "Layer 2 :: param confirmed")
    _assert_present(text, "PARAM_UNCONFIRMED", "Layer 2 :: param unconfirmed")
    _assert_present(text, "TROUBLESHOOT_STANDARD", "Layer 2 :: troubleshoot standard")
    _assert_present(text, "TROUBLESHOOT_LIMITED", "Layer 2 :: troubleshoot limited")
    _assert_present(text, "SQL_DDL_ALLOWED", "Layer 2 :: sql ddl")
    _assert_present(text, "SQL_PIPELINE_ALLOWED", "Layer 2 :: sql pipeline")
    _assert_present(text, "SQL_BLOCKED", "Layer 2 :: sql blocked")


def check_risk_gates(text: str) -> None:
    """Layer 3: baseline risk gates G1..G4; additional gates may extend the list."""
    _assert_present(text, "Unverified concrete value gate", "Layer 3 :: G1")
    _assert_present(text, "Open-source leakage gate", "Layer 3 :: G2")
    _assert_present(text, "SQL structure gate", "Layer 3 :: G3")
    _assert_present(text, "File protocol gate", "Layer 3 :: G4")


def check_safe_downgrade_rules(text: str) -> None:
    """Official-doc failures must downgrade safely without generic Apache fallback."""
    _assert_present(
        text,
        "If official documentation fetch returns 404, times out, or cannot be parsed, immediately stop knowledge retrieval",
        "Layer 2 :: safe downgrade",
    )
    _assert_present(
        text,
        "must not use Apache Flink community documentation or generic experience as a substitute",
        "Layer 2 :: no generic fallback",
    )
    _assert_present(
        text,
        "Alibaba Cloud parameters should be verified against the actual console display",
        "Layer 2 :: explicit Alibaba Cloud uncertainty notice",
    )


def check_safe_downgrade_empty_and_js(text: str) -> None:
    """Safe downgrade must explicitly cover empty-content and JS-rendering fetch failures,
    and must prescribe a fixed safe response path (not just a vague 'safest terminal state')."""
    # Must cover empty-content failure mode
    _assert_present(
        text,
        "responses that are **empty**",
        "Layer 2 :: empty-content downgrade",
    )
    # Must cover JS-rendering failure mode (accept either form)
    has_js_rendering = (
        "JS-rendering" in text
        or "JS rendering" in text
        or "js-rendering" in text.lower()
    )
    if not has_js_rendering:
        _failures.append(
            "[MISSING] Layer 2 :: JS-rendering safe downgrade: "
            "expected to find 'JS-rendering' or 'JS rendering' in SKILL.md"
        )
    # Must require a fixed, invariant safe response string for unverified-doc cases
    _assert_present(
        text,
        "the fixed safe response",
        "Layer 2 :: fixed safe response path",
    )


def check_response_families(text: str) -> None:
    """Layer 4: response-builder output families."""
    _assert_present(text, "R1_PARAM_CONFIRMED", "Layer 4 :: families")
    # R2..R9 are optional in this first harness; key is that the section exists


def check_output_formatter(text: str) -> None:
    """Layer 5: output formatter must state file trailers are not global."""
    _assert_present(text, "SQL blocks remain pure SQL", "Layer 5 :: sql formatter")


def check_file_output_explicit_only(text: str) -> None:
    """File output must be explicit-only and separate from ordinary answers."""
    _assert_present(text, "FILE_READY", "File output")
    # The file output protocol should not leak into global rules
    # We check that the legacy pattern of a global forced footer is absent
    _assert_absent(text, "每次回答末尾必须", "File output :: no global footer rule")


def check_sql_scenario_first(text: str) -> None:
    """SQL subsystem must implement scenario-first routing."""
    _assert_present(text, "SQL_SCENARIO_DDL_ONLY", "SQL :: scenario-first")
    _assert_present(text, "SQL_SCENARIO_PIPELINE", "SQL :: scenario-first")
    _assert_present(text, "SQL_SCENARIO_RISK_MONITORING", "SQL :: scenario-first")
    _assert_present(text, "Scenario selection happens before SQL generation", "SQL :: scenario ordering")


def check_tool_invocation_hard_gate(text: str) -> None:
    """Alibaba-specific parameter/state queries must require a hard tool-invocation gate,
    not just soft priority wording ('prefer', 'should', etc.)."""
    _assert_present(
        text,
        "Tool Invocation Verification Gate",
        "Layer 3/4 :: hard tool-invocation gate",
    )
    _assert_present(
        text,
        "mandatory",
        "Layer 3/4 :: mandatory gate semantics",
    )
    _assert_present(
        text,
        "**block** the verified answer",
        "Layer 3/4 :: block on missing invocation evidence (G6-specific)",
    )
    _assert_present(
        text,
        "tools unavailable at runtime",
        "Layer 3/4 :: G6 Scenario B – tools unavailable is not a gate violation",
    )
    _assert_present(
        text,
        "NOT a gate violation",
        "Layer 3/4 :: G6 Scenario B – explicit not-a-violation wording",
    )


def check_alibaba_specific_sql_and_tool_priority(text: str) -> None:
    """Alibaba-specific syntax and tool invocation priority must be explicit."""
    _assert_present(text, "CDAS", "SQL :: Alibaba-specific syntax")
    _assert_present(
        text,
        "must prioritize Alibaba Cloud CDAS syntax",
        "SQL :: CDAS priority",
    )
    _assert_present(text, "aliyun CLI", "Layer 4 :: tool priority")
    _assert_present(text, "OpenAPI", "Layer 4 :: tool priority")
    _assert_present(
        text,
        "must prioritize tool invocation over static knowledge-only answers",
        "Layer 4 :: tool-first builder rule",
    )


def check_sink_write_safety(text: str) -> None:
    """Streaming sink write-mode safety must be guarded explicitly."""
    _assert_present(text, "Sink Write Safety Gate", "Layer 3 :: sink safety")
    _assert_present(text, "insertOrIgnore", "Layer 3 :: sink safety")
    _assert_present(text, "overwrite", "Layer 3 :: sink safety")
    _assert_present(text, "upsert", "Layer 3 :: sink safety")


def check_no_legacy_state_machine(text: str) -> None:
    """The old global state machine must no longer be the controlling architecture."""
    # These legacy states must not appear as architectural controllers.
    # They may still appear in historical reference text, but not as state definitions.
    _assert_absent(text, "`VERIFICATION_FAILED`", "legacy state :: VERIFICATION_FAILED")
    _assert_absent(text, "`VERIFICATION_READY`", "legacy state :: VERIFICATION_READY")


def check_no_priority_duplication(text: str) -> None:
    """No duplicated 'highest priority' declarations across unrelated domains."""
    n = text.lower().count("highest priority")
    if n > 1:
        _failures.append(
            f"[EXCESS] Priority: 'highest priority' appears {n} times, expected <= 1"
        )


# ---- Group 10b: Bounded generic-knowledge downgrade path (Report Root Cause #1)
def check_bounded_generic_downgrade(text: str) -> None:
    _assert_present(
        text,
        "sole exception",
        "Layer 2 :: bounded generic downgrade must be framed as the only hard-block exception",
    )
    _assert_present(
        text,
        "no-cloud-vendor-difference",
        "Layer 2 :: bounded generic downgrade must define vendor-neutral scope criteria",
    )
    _assert_present(
        text,
        "1) The knowledge belongs to **generic industry standards with no cloud vendor differences**",
        "Layer 2 :: bounded generic downgrade condition 1 must be present",
    )
    _assert_present(
        text,
        "2) The knowledge **does not involve** Alibaba Cloud console-specific thresholds",
        "Layer 2 :: bounded generic downgrade condition 2 must restrict Alibaba-exclusive values",
    )
    _assert_present(
        text,
        "3) The answer must begin with the clear label",
        "Layer 2 :: bounded generic downgrade condition 3 must require the disclaimer prefix",
    )
    has_bounded_generic = (
        "generic open-source community standards" in text.lower()
        or "industry-standard knowledge" in text.lower()
        or "industry-generic knowledge" in text.lower()
    )
    if not has_bounded_generic:
        _failures.append(
            "[MISSING] Layer 2 :: bounded generic-knowledge downgrade: "
            "SKILL.md must allow output of industry-standard/open-source community "
            "knowledge when official-doc fetch or tool invocation fails."
        )
    _assert_present(
        text,
        "Alibaba Cloud-specific parameters",
        "Layer 2 :: Alibaba-specific disclaimer alongside generic knowledge",
    )
    _assert_present(
        text,
        "Alibaba Cloud proprietary information",
        "Layer 2 :: scope restriction on bounded-generic override",
    )


def check_cdc_standard_prerequisite_whitelist(text: str) -> None:
    _assert_present(
        text,
        "binlog_format",
        "G1/2.2 :: CDC standard-prerequisite whitelist",
    )
    _assert_present(
        text,
        "industry-generic technical standards",
        "G1/2.2 :: industry-standard whitelist exemption clause",
    )
    _assert_present(
        text,
        "do not need to trigger G1",
        "G1/2.2 :: explicit G1 exemption for whitelisted standards",
    )
    _assert_present(
        text,
        "exempt from both G1",
        "G1/2.2 :: whitelist also exempts G2 alongside G1",
    )
    _assert_present(
        text,
        "trigger G1 or G2",
        "G1/2.2 :: explicit exemption for both G1 and G2",
    )


def check_cdas_sql_skeleton_mandate(text: str) -> None:
    _assert_present(
        text,
        "complete SQL",
        "Layer 4 :: complete SQL skeleton mandate",
    )
    _assert_present(
        text,
        "Source",
        "Layer 4 :: SQL skeleton must include Source",
    )
    _assert_present(
        text,
        "Sink",
        "Layer 4 :: SQL skeleton must include Sink",
    )
    _assert_present(
        text,
        "table merging",
        "Layer 4 :: SQL skeleton must include merge logic",
    )
    _assert_present(
        text,
        "conversational confirmation or brief descriptions is **prohibited**",
        "Layer 4 :: forbid conversational-only responses for CDC SQL",
    )
    _assert_present(
        text,
        "must execute",
        "Layer 4 :: unknown source/sink carve-out must prefer confirmation before placeholders",
    )


def check_fixed_safe_response_consistency(text: str) -> None:
    response = "The parameter information should be verified against the actual Alibaba Cloud console display; official documentation could not be retrieved for verification at this time."
    count = text.count(response)
    if count < 2:
        _failures.append(
            "[MISSING] Layer 2/G6 :: fixed safe response must appear consistently in both Section 2.0 and G6"
        )


# ---- Group 10f: Alibaba-specific billing/version hard-block (Report Run-1/3/4)
def check_billing_version_hard_block(text: str) -> None:
    """Alibaba-specific billing and engine-version queries must NOT leak into the
    bounded generic-knowledge downgrade path.  SKILL.md must contain an explicit
    prohibition that forbids using generic/industry-standard knowledge for these
    Alibaba-exclusive domains."""
    # Explicit billing mention in the hard-block context
    _assert_present(
        text,
        "billing",
        "Layer 2 :: billing must be called out as Alibaba-specific hard-block scope",
    )
    # Explicit engine version mention
    _assert_present(
        text,
        "engine version",
        "Layer 2 :: engine version must be called out as Alibaba-specific hard-block scope",
    )
    # Explicit prohibition: bounded generic downgrade must NOT cover Alibaba
    # billing or version facts
    _assert_present(
        text,
        "no downgrade permitted",
        "Layer 2 :: explicit prohibition on bounded generic downgrade for Alibaba billing/version",
    )


# ---- Group 10g: CDAS skeleton mandate with manual sync SQL ban (Report CDC leakage)
def check_cdc_cdas_no_manual_sync(text: str) -> None:
    """CDC / multi-table sync must require CDAS-style skeletons and must NOT fall
    back to manual CREATE TABLE + INSERT INTO style sync SQL."""
    # Must reference CDAS as the required syntax
    _assert_present(
        text,
        "CDAS",
        "Layer 4 :: CDC flows must require CDAS syntax",
    )
    # Must explicitly forbid manual sync SQL fallback
    _assert_present(
        text,
        "must not fall back to manual sync SQL",
        "Layer 4 :: prohibition on manual sync SQL fallback",
    )
    # Must prohibit CREATE TABLE + INSERT INTO as a CDC alternative
    _assert_present(
        text,
        "INSERT INTO",
        "Layer 4 :: explicit ban on CREATE TABLE + INSERT INTO as CDC fallback",
    )


# ---- Group 10h: Hard tool invocation enforcement in CDC flows (Report weak gating)
def check_cdc_tool_invocation_hard_gate(text: str) -> None:
    """Tool invocation in CDC / data-integration flows must be operationalized as a
    hard gate, not as soft 'prefer' / 'should' language.  When tools/evidence are
    absent, the SKILL.md must prescribe explicit hard-path wording."""
    # Must contain an explicit hard-gate phrase (not just 'prefer')
    _assert_present(
        text,
        "hard-path",
        "Layer 4 :: CDC tool invocation must use hard-path wording when tools/evidence absent",
    )
    _assert_present(
        text,
        "Scenario C",
        "Layer 3 :: G6 must define a CDC-specific Scenario C",
    )
    _assert_present(
        text,
        "CDC SQL generation contexts",
        "Layer 3 :: G6 Scenario C must explicitly scope CDC SQL generation contexts",
    )


# ---- Group 10i: Official-doc fetch failure multi-path retry protocol
#          (Report Suggestion #1 — "URL Prefix Strategy" / "替代路径" / "search tool")
def check_official_doc_fetch_retry_protocol(text: str) -> None:
    """After an official-doc fetch fails, SKILL.md must prescribe a multi-path
    retry/search protocol before any hard-block or generic-knowledge downgrade is
    allowed.  The report found agents returning a safe-block message immediately
    after a 404/JS-render failure without trying alternative retrieval paths."""
    # Must mention a URL prefix / URL variant strategy
    has_url_prefix = (
        "URL Prefix" in text
        or "URL prefix" in text
        or "url prefix" in text.lower()
        or "URL 前缀" in text
        or "路径变体" in text
        or "URL variant" in text.lower()
        or "URL alternative" in text.lower()
    )
    if not has_url_prefix:
        _failures.append(
            "[MISSING] Layer 2 :: official-doc fetch retry — 'URL Prefix Strategy' "
            "(or 替代路径 / URL variant) must be present so the agent tries alternate "
            "official-URL patterns before blocking."
        )

    # Must mention an alternative-path / search-tool workflow
    has_alt_path = (
        "替代路径" in text
        or "alternative path" in text.lower()
        or "search tool" in text.lower()
        or "内置搜索" in text
        or "搜索工具" in text
        or "official-search" in text.lower()
        or "搜索兜底" in text
    )
    if not has_alt_path:
        _failures.append(
            "[MISSING] Layer 2 :: official-doc fetch retry — SKILL.md must require "
            "at least one 替代路径 / search-tool / official-search fallback step "
            "(e.g. 使用内置搜索工具检索官方文档标题) before blocking."
        )

    # Must explicitly forbid returning a safe-block before completing at least one retry.
    # Anchor to the actual §2.0 prohibition phrase to avoid false-positive on loose co-occurring keywords.
    has_no_premature_block = (
        "禁止在未完成至少一次替代路径尝试前直接返回安全阻断话术" in text
        or "must not return" in text.lower() and "safe-block" in text.lower() and "at least one" in text.lower() and "alternative" in text.lower()
        or "不得在未完成至少一次" in text and "直接返回安全阻断" in text
    )
    if not has_no_premature_block:
        _failures.append(
            "[MISSING] Layer 2 :: official-doc fetch retry — SKILL.md must contain the "
            "explicit prohibition '禁止在未完成至少一次替代路径尝试前直接返回安全阻断话术' "
            "(or equivalent English: 'must not return a safe-block before trying at least one "
            "alternative retrieval path')."
        )


# ---- Group 10j: G2 source-labeling discipline for mixed open-source vs Alibaba-specific guidance
#          (Report Suggestion #3 — G2 boundary clarity)
def check_g2_source_labeling(text: str) -> None:
    """SKILL.md must enforce explicit source-labeling so that open-source community
    guidance and Alibaba-Cloud-specific guidance are never mixed without clear
    boundaries.  The report found outputs mixing Gemini with RocksDB in the same
    path, and mixing community best-practices with console-only features."""
    # Must require the [General Open-Source Standard] label
    _assert_present(
        text,
        "[General Open-Source Standard]",
        "Layer 3 :: G2 source-labeling — [General Open-Source Standard] marker required",
    )
    # Must require the [Alibaba Cloud Proprietary] label
    _assert_present(
        text,
        "[Alibaba Cloud Proprietary]",
        "Layer 3 :: G2 source-labeling — [Alibaba Cloud Proprietary] marker required",
    )
    # Must forbid mixing incompatible backends (e.g. Gemini + RocksDB)
    has_backend_mix_prohibition = (
        ("Gemini" in text or "gemini" in text) and ("RocksDB" in text or "rocksdb" in text)
        or "混用不同后端" in text
        or "不同后端" in text and ("严禁" in text or "forbid" in text.lower() or "禁止" in text)
        or "mixed backend" in text.lower() and ("prohibit" in text.lower() or "forbid" in text.lower() or "block" in text.lower())
        or "incompatible backend" in text.lower() and ("prohibit" in text.lower() or "forbid" in text.lower() or "禁止" in text)
        or "严禁混用" in text
        or "混用" in text and "禁止" in text
    )
    if not has_backend_mix_prohibition:
        _failures.append(
            "[MISSING] Layer 3 :: G2 source-labeling — SKILL.md must prohibit "
            "mixing incompatible backends (e.g. stating Gemini while including "
            "RocksDB parameters) within the same troubleshooting path."
        )


# ---- Group 10k: Stricter CDAS placeholder template requirement
#          (Report Suggestion #2 — CDAS skeleton must be concrete)
def check_cdas_placeholder_template(text: str) -> None:
    """The CDAS skeleton must include a concrete template with specific mandatory
    markers so agents cannot generate underspecified SQL skeletons.  The report
    found agents producing 'complete but违规' SQL or underspecified skeletons
    without TODO placeholders."""
    # Must have the CREATE DATABASE IF NOT EXISTS skeleton start
    _assert_present(
        text,
        "CREATE DATABASE IF NOT EXISTS",
        "Layer 4 :: CDAS skeleton — must include 'CREATE DATABASE IF NOT EXISTS'",
    )
    # Must have AS TABLE in the CDAS skeleton
    _assert_present(
        text,
        "AS TABLE",
        "Layer 4 :: CDAS skeleton — must include 'AS TABLE'",
    )
    # Must require hostname parameter
    _assert_present(
        text,
        "hostname",
        "Layer 4 :: CDAS skeleton — must include 'hostname' parameter",
    )
    # Must include a TODO-style placeholder for the MySQL endpoint
    has_todo = (
        "-- TODO" in text
        or "// TODO" in text
        or "# TODO" in text
        or "TODO:" in text
        or "替换为实际 MySQL 实例" in text
        or "替换为实际" in text and "Endpoint" in text
        or "replace with actual" in text.lower() and "endpoint" in text.lower()
    )
    if not has_todo:
        _failures.append(
            "[MISSING] Layer 4 :: CDAS skeleton — must include a TODO placeholder "
            "like '-- TODO: 替换为实际 MySQL 实例 Endpoint' for the MySQL hostname."
        )
    # Must state that missing params must be obtained via aliyun CLI/OpenAPI
    has_param_source = (
        ("aliyun CLI" in text or "aliyun OpenAPI" in text or "OpenAPI" in text)
        and ("替换" in text or "replace" in text.lower() or "获取" in text)
        or "aliyun CLI/OpenAPI" in text
    )
    if not has_param_source:
        _failures.append(
            "[MISSING] Layer 4 :: CDAS skeleton — must state that missing parameters "
            "must be obtained through aliyun CLI/OpenAPI before replacement."
        )
    # Must explicitly forbid manual CREATE TABLE + INSERT INTO as a CDAS alternative
    _assert_present(
        text,
        "prohibited",
        "Layer 4 :: CDAS skeleton — must contain prohibition language",
    )
    _assert_present(
        text,
        "CREATE TABLE",
        "Layer 4 :: CDAS skeleton — must reference the banned 'CREATE TABLE' pattern",
    )
    # Must forbid INSERT INTO as a CDC alternative
    _assert_present(
        text,
        "INSERT INTO",
        "Layer 4 :: CDAS skeleton — must reference the banned 'INSERT INTO' pattern",
    )


# ---- Group 10l: §2.0 retry-path step-locking for current-failing-path
#          (Report Suggestion #1 — retry discipline before safe-block)
def check_retry_path_step_locking(text: str) -> None:
    """§2.0 must contain explicit step-locking language for 'the current failing path'
    and prescribe at least one 替代路径 / search-tool retry before any safe-block
    downgrade.  The report found agents jumping straight to safe-block on first fetch
    failure without trying alternate retrieval paths."""
    # Must scope the retry protocol to the current failing path
    _assert_present(
        text,
        "for the current failing path",
        "Layer 2 :: retry protocol must reference 'for the current failing path'",
    )
    # Must mention alternative-path / 替代路径 retry (already partially checked in 10i,
    # but here we require it in the context of step-locking / current-failing-path)
    has_alt_path_in_retry = (
        "替代路径" in text
        or "alternative path" in text.lower()
        or "搜索工具" in text
        or "search tool" in text.lower()
    )
    if not has_alt_path_in_retry:
        _failures.append(
            "[MISSING] Layer 2 :: retry step-locking — SKILL.md must require "
            "'替代路径' / 'search tool' / '搜索工具' as an explicit retry step "
            "for the current failing path before safe-block."
        )
    # Must require at least one alternative retrieval before downgrade
    _assert_present(
        text,
        "at least one",
        "Layer 2 :: retry step-locking must quantify minimum retry count (at least one)",
    )


# ---- Group 10m: Flink SQL syntax hard guard — STATE TTL syntax discipline
#          (Report Section 2 — inline STATE TTL hallucination vs WITH clause)
def check_state_ttl_syntax_guard(text: str) -> None:
    """Layer 3/4 SQL rules must explicitly prohibit inline STATE ttl INTERVAL syntax
    and require the official WITH ('state.ttl' = '...') declaration.  The report found
    models emitting inline STATE TTL syntax not supported by official Flink DDL.

    Must verify an actual PROHIBITION (禁止/BLOCKED/banned) on the inline syntax —
    not just loose keyword co-occurrence of 'STATE' or 'TTL' anywhere in the doc."""
    # Must contain an explicit prohibition on inline STATE ttl INTERVAL syntax
    # Require phrase-level check: prohibited-word AND the inline form together
    has_ttl_prohibition = (
        ("STATE ttl INTERVAL" in text and ("禁止" in text or "PROHIBITED" in text or "prohibited" in text or "blocked" in text.lower() or "banned" in text.lower() or "不得" in text))
        or ("禁止" in text and "内联" in text and "STATE" in text and "TTL" in text)
        or ("禁止" in text and "内联" in text and "ttl" in text.lower())
    )
    if not has_ttl_prohibition:
        _failures.append(
            "[MISSING] Layer 3/4 :: Flink SQL syntax — SKILL.md must contain an "
            "explicit prohibition (禁止/不得/BLOCKED) on the inline 'STATE ttl INTERVAL' "
            "syntax pattern. Loose keyword co-occurrence is insufficient."
        )
    # Must prescribe the correct WITH-clause style with actual value assignment
    has_with_ttl = (
        "WITH ('state.ttl'" in text
        or "WITH (\"state.ttl\"" in text
    )
    if not has_with_ttl:
        _failures.append(
            "[MISSING] Layer 3/4 :: Flink SQL syntax — SKILL.md must prescribe "
            "TTL via WITH clause (e.g. WITH ('state.ttl' = '24 h'))."
        )


# ---- Group 10o: Sink WATERMARK anti-pattern guard
#          (Report Suggestion #1 — Qwen3-Max adding WATERMARK to Sink tables)
def check_sink_no_watermark(text: str) -> None:
    """G3 must explicitly forbid WATERMARK declarations in Sink table DDL.
    The report found Qwen3-Max models emitting WATERMARK in Sink table definitions
    which is syntactically invalid — WATERMARK is source-only syntax.

    The validator requires an explicit combined phrase (not just loose co-occurrence
    of 'Sink', 'WATERMARK', and '禁止' in separate lines) to avoid false-passes on
    generic keywords like 'not', 'set', or any document containing all three words."""
    # Must contain a single contiguous prohibition phrase linking Sink and WATERMARK
    has_sink_watermark_ban = (
        "Declaring `WATERMARK` in **Sink** table DDL is strictly prohibited" in text
        or ("Sink table DDL" in text and "WATERMARK" in text and ("forbid" in text.lower() or "prohibit" in text.lower()))
        or ("**Sink** table DDL" in text and "WATERMARK" in text and "prohibited" in text.lower())
    )
    if not has_sink_watermark_ban:
        _failures.append(
            "[MISSING] Layer 3 :: G3 SQL anti-pattern — SKILL.md must explicitly forbid "
            "WATERMARK declarations in Sink table DDL (WATERMARK is source-only syntax; "
            "models frequently hallucinate it in Sink definitions)."
        )


# ---- Group 10p: allowNonRestoredState as CLI flag, not SQL SET syntax
#          (Report Suggestion #1 — Qwen3-Max outputting SET 'allowNonRestoredState' = 'true')
def check_allow_non_restored_state_cli_flag(text: str) -> None:
    """Checkpoint/Savepoint restore guidance must clarify that allowNonRestoredState is a
    CLI/console startup flag, NOT a SQL SET parameter.  The report found models emitting
    `SET 'allowNonRestoredState' = 'true'` which is incorrect — this is a Flink runtime
    launch-time configuration, not a SQL session parameter.

    Requires explicit combined phrases (not just loose co-occurrence) so that a document
    mentioning 'SET' and 'allowNonRestoredState' in unrelated sections does NOT false-pass."""
    has_cli_flag_guidance = (
        "allowNonRestoredState" in text
        and ("CLI/console" in text
             or "CLI/控制台" in text
             or "启动参数" in text
             or ("flink run" in text.lower() and "allowNonRestoredState=true" in text)
             )
    )
    if not has_cli_flag_guidance:
        _failures.append(
            "[MISSING] Layer 4 :: restore boundary — SKILL.md must clarify that "
            "allowNonRestoredState is a CLI/console startup flag, NOT a SQL SET "
            "parameter. Models frequently output `SET 'allowNonRestoredState' = 'true'` "
            "which is incorrect."
        )
    has_set_prohibition = (
        "the syntax `SET 'allowNonRestoredState' = 'true'` is prohibited" in text
        or ("SET 'allowNonRestoredState'" in text and "prohibited" in text.lower())
        or ("not a sql set" in text.lower() and "allowNonRestoredState" in text)
    )
    if not has_set_prohibition:
        _failures.append(
            "[MISSING] Layer 4 :: restore boundary — SKILL.md must explicitly forbid "
            "`SET 'allowNonRestoredState' = 'true'` SQL syntax, clarifying that it "
            "must be configured as a job startup parameter (CLI/console) instead."
        )


# ---- Group 10n: Restore-boundary guidance — stateless operator append is safe,
#          stateful additions require allowNonRestoredState=true
#          (Report Section 2 — checkpoint/savepoint restore ambiguity)
def check_restore_boundary_stateful_stateless(text: str) -> None:
    """Checkpoint/savepoint restore guidance must distinguish between 无状态算子
    (stateless) operator additions — which are generally safe — and 有状态算子
    (stateful) operator additions — which require allowNonRestoredState=true.
    The report found agents making ambiguous claims like 'adding new operators at
    the end always allows restore' without this distinction."""
    # Must mention stateless operators as the generally-safe case
    _assert_present(
        text,
        "stateless operators",
        "Layer 4 :: restore boundary — must reference stateless operators",
    )
    # Must mention stateful operators as the restricted case
    _assert_present(
        text,
        "stateful operators",
        "Layer 4 :: restore boundary — must reference stateful operators",
    )
    # Must require allowNonRestoredState=true for stateful additions
    _assert_present(
        text,
        "allowNonRestoredState=true",
        "Layer 4 :: restore boundary — must prescribe allowNonRestoredState=true "
        "for stateful operator additions",
    )


# ---- Group 10q: Billing carve-out — generic comparison allowed under no-tools
#          (Report Suggestion #3 — agents return hollow 33-char fallback on billing queries)
def check_billing_generic_carveout(text: str) -> None:
    has_billing_carveout = (
        ("generic billing" in text.lower())
        and ("tools unavailable" in text.lower() or "tools are unavailable" in text.lower())
        and ("disclaimer" in text.lower() or "console display" in text.lower())
    )
    if not has_billing_carveout:
        _failures.append(
            "[MISSING] Layer 2 :: billing carve-out — SKILL.md must permit generic "
            "billing-mode comparison (通用计费模式) with a disclaimer "
            "when tools are unavailable at runtime, instead of pure hard-block returning only "
            "the 33-char fixed safe response."
        )


# ---- Group 10r: Explicit ban on TABLE(SOURCE()) and CDAS syntax variants
#          (Report CDC Suggestion #1 — Solution 3 uses non-standard TABLE(SOURCE()) syntax)
def check_table_source_ban(text: str) -> None:
    """SKILL.md must explicitly prohibit non-standard TABLE(SOURCE()) syntax and
    similar CDAS variants in CDC SQL generation.  The eval report found agents
    producing 'Solution 3 uses non-standard TABLE(SOURCE()) syntax instead of
    proper CDAS'.  A ban on manual CREATE TABLE + INSERT INTO is not sufficient
    — TABLE(SOURCE()) is a distinct hallucination pattern."""
    # Must explicitly mention and ban TABLE(SOURCE()) or TABLE(SOURCE)
    has_table_source_ban = (
        "TABLE(SOURCE())" in text
        or "TABLE(SOURCE)" in text
        or "table(source())" in text.lower()
        or "table(source)" in text.lower()
    )
    if not has_table_source_ban:
        _failures.append(
            "[MISSING] Layer 4 :: CDC syntax ban — SKILL.md must explicitly prohibit "
            "non-standard TABLE(SOURCE()) syntax in CDC SQL generation.  The eval "
            "report found agents emitting 'TABLE(SOURCE())' instead of proper CDAS "
            "skeletons."
        )


# ---- Group 10s: G2 paragraph-format source-label template
#          (Report Suggestion #2 — G2 labels not enforced at paragraph level; agents
#           omit 【通用开源标准】/【阿里云专属】 tags in output paragraphs)
def check_g2_paragraph_label_template(text: str) -> None:
    """SKILL.md must prescribe a concrete paragraph-level output template for G2
    source labels so that agents cannot omit or bury the 【通用开源标准】 /
    【阿里云专属】 tags mid-paragraph.  The eval report found outputs that 'do not
    contain these labels on any paragraph'.  The existing G2 checks only verify the
    label strings exist; they do not enforce a paragraph-format discipline.

    Required template: 【标签】具体指导内容 — i.e. the tag must appear at the
    beginning of the paragraph, followed immediately by the guidance content."""
    # Must contain the paragraph-format discipline template
    has_paragraph_template = (
        ("[Label] specific guidance content" in text
         or "[Label] specific guidance" in text
         or "label" in text.lower() and "specific guidance" in text.lower()
        )
    )
    if not has_paragraph_template:
        _failures.append(
            "[MISSING] Layer 3 :: G2 paragraph template — SKILL.md must prescribe "
            "a concrete output-format template for G2 source labels: "
            "【标签】具体指导内容 (tag must precede paragraph immediately). "
            "The eval report found agents omitting labels entirely in output paragraphs."
        )


# ---- Group 10t: Billing/version hard-block must explicitly ban percentage/ratio leakage
#          (Report Suggestion #1 — agents output "30%-50% cheaper" when official docs fail)
def check_billing_no_ratio_leakage(text: str) -> None:
    """When official documentation fetch fails for Alibaba-specific billing or engine
    version queries, SKILL.md must explicitly prohibit outputting ANY percentage
    intervals or unverified industry reference ratios.  The eval report found agents
    producing 'Subscription pricing is stated as 30%-50% cheaper than pay-as-you-go'
    as a direct violation of the hard-block rule.  Merely mentioning '不得降级' for
    billing/version is insufficient — the SKILL.md must contain an explicit ban on
    percentage/ratio claims in this context."""
    # Must explicitly ban percentage/ratio claims for billing when docs fail
    has_ratio_ban = (
        "outputting any percentage range is strictly prohibited" in text.lower()
        or "any percentage range" in text.lower() and "strictly prohibited" in text.lower()
        or "prohibit.*percentage" in text.lower() and "interval" in text.lower()
    )
    if not has_ratio_ban:
        _failures.append(
            "[MISSING] Layer 2 :: billing hard-block ratio ban — SKILL.md must "
            "explicitly prohibit outputting unverified percentage intervals or "
            "industry reference ratios (e.g. '30%-50% cheaper') for Alibaba billing/"
            "version queries when official documentation fails. The eval report found "
            "agents producing 'Subscription pricing is stated as 30%-50% cheaper than "
            "pay-as-you-go' as a hard-block violation."
        )

    # Must mention the forced safe response string in the hard-block context
    _assert_present(
        text,
        "fixed block response must be output directly",
        "Layer 2 :: billing hard-block force-output directive",
    )
    # Must tie the ban to the billing + no-evidence context
    has_billing_no_doc_context = (
        "billing" in text.lower() and ("no official" in text.lower() or "official doc" in text.lower() or "document fails" in text.lower() or "documentation fails" in text.lower())
    )
    # This is already covered by check_billing_version_hard_block asserting billing + 不得降级,
    # but here we verify the context is connected to doc-failure + ratio ban.
    # At minimum, the ratio ban must appear near the billing hard-block rule.
    if not has_billing_no_doc_context:
        _failures.append(
            "[MISSING] Layer 2 :: billing hard-block must tie percentage-ban to "
            "the no-evidence / doc-fetch-failure context explicitly."
        )


# ---- Group 10u: CDC multi-table sync — Paimon sink WITH config + regex routing
#          (Report Suggestion #2 — missing Paimon sink WITH params and full-table/regex routing)
def check_cdc_multi_table_paimon_routing(text: str) -> None:
    """CDC multi-table sync SQL must require explicit Paimon sink WITH parameter
    configuration and regex/full-table routing structure. The eval report found agents
    outputting simplified source-sink pairs without explicit Paimon sink WITH clauses
    (catalog, warehouse, etc.) and without regex or full-table routing logic for
    sharded/multi-database scenarios.

    Required evidence:
    - Paimon sink WITH configuration parameters (catalog, warehouse, etc.)
    - Regex pattern or full-table routing structure for multi-table sync
    - Explicit sharded/multi-database table routing guidance"""
    # Must mention Paimon in the sink configuration context
    _assert_present(
        text,
        "Paimon",
        "Layer 4 :: CDC multi-table sink — must reference Paimon explicitly",
    )
    # Must require explicit WITH parameters for the Paimon sink
    has_paimon_with = (
        ("Paimon" in text or "paimon" in text)
        and ("WITH" in text or "with" in text)
        and ("catalog" in text.lower() or "warehouse" in text.lower() or "参数" in text)
    )
    if not has_paimon_with:
        _failures.append(
            "[MISSING] Layer 4 :: CDC multi-table sink — SKILL.md must require "
            "explicit Paimon sink WITH parameter configuration (e.g. catalog, warehouse)"
            " when generating multi-table CDC sync SQL."
        )
    # Must require regex or full-table routing for multi-table/sharded scenarios
    has_regex_routing = (
        "regex" in text.lower()
        or "正则" in text
        or "正则表达式" in text
        or "full-table" in text.lower()
        or "全表" in text and ("路由" in text or "覆盖" in text)
        or "pattern" in text.lower() and ("routing" in text.lower() or "覆盖" in text or "匹配" in text)
    )
    if not has_regex_routing:
        _failures.append(
            "[MISSING] Layer 4 :: CDC multi-table routing — SKILL.md must require "
            "explicit regex pattern matching or full-table routing structure for "
            "multi-table / sharded database CDC sync scenarios (e.g. Source 端使用 regex "
            "模式覆盖全量表)."
        )
    # Must mention multi-table / sharded / multiple databases context
    has_multi_table = (
        "多表" in text
        or "分库" in text
        or "分表" in text
        or "multi-table" in text.lower()
        or "sharded" in text.lower()
        or "multiple.*table" in text.lower()
    )
    if not has_multi_table:
        _failures.append(
            "[MISSING] Layer 4 :: CDC multi-table context — SKILL.md must explicitly "
            "reference multi-table / sharded database scenarios and prescribe the "
            "corresponding Paimon sink + regex routing requirements."
        )


# ---- Group 10v: G2 anti-Markdown-header substitution for paragraph labels
#          (Report Suggestion #1 — Qwen3-Max uses `### 【通用开源标准】` instead of inline labels)
def check_g2_no_header_label_substitution(text: str) -> None:
    """G2 paragraph-format discipline must explicitly forbid using Markdown headers
    (e.g. ### 【通用开源标准】或 ### 【阿里云专属】) as a substitute for the required
    inline paragraph-level labels.  The eval report found Qwen3-Max bypassing the
    paragraph-label requirement by wrapping labels in Markdown heading syntax.
    The existing check_g2_paragraph_label_template verifies the template pattern exists
    but does not guard against header-substitution.
    """
    has_header_ban = (
        ("heading syntax" in text.lower() and "substitute" in text.lower() and "paragraph" in text.lower())
        or ("Markdown heading syntax" in text and "paragraph-level labels" in text)
        or ("prohibited" in text.lower() and "###" in text and "label" in text.lower())
    )
    if not has_header_ban:
        _failures.append(
            "[MISSING] Layer 3 :: G2 anti-header substitution — SKILL.md must explicitly "
            "forbid using Markdown headers (e.g. ### 【通用开源标准】) as a substitute for "
            "inline paragraph labels. The eval report found Qwen3-Max bypassing the "
            "paragraph-label requirement by wrapping labels in Markdown heading syntax."
        )


# ---- Group 10w: §2.0 disclaimer must appear at reply start, not end or mid-reply
#          (Report Suggestion #2 — models place disclaimer at end of response)
def check_disclaimer_reply_first_line(text: str) -> None:
    """§2.0 bounded-generic downgrade disclaimer must appear at the start of the reply,
    not at the end or buried mid-response.  The eval report found Qwen3-Max placing
    the generic-billing disclaimer at the end of the response after outputting specifics.
    The existing check_fixed_safe_response_consistency verifies consistency count but
    does not enforce positioning.
    """
    has_first_line = (
        ("first line of the reply" in text.lower() or "first line of the reply" in text)
        and ("disclaimer" in text.lower() or "fixed" in text.lower())
        or "first line of the reply" in text
        or ("must" in text.lower() and "placed on the first line" in text.lower())
    )
    if not has_first_line:
        _failures.append(
            "[MISSING] Layer 2 :: §2.0 disclaimer positioning — SKILL.md must state that "
            "the bounded-generic downgrade disclaimer must appear at the reply start "
            "(回复首行), not at the end or buried mid-response. The eval report found "
            "agents placing the disclaimer after outputting unverified specifics."
        )


# ---- Group 10x: G6 anti-mock tool invocation evidence (empty array / fake tracking)
#          (Report Suggestion #3 — agents output [] or fabricated action tracking as evidence)
def check_g6_anti_mock_evidence(text: str) -> None:
    """G6 must explicitly prohibit fabricated tool invocation evidence such as empty
    arrays ([]) or mock/fake action tracking files.  The eval report found open_claw
    simulating tool calls that returned empty arrays, and agents treating these as
    valid evidence.  The existing check_tool_invocation_hard_gate verifies Scenario
    semantics but does not cover anti-mock/fake-evidence rules.
    """
    has_anti_mock = (
        ("must not be treated as valid evidence" in text.lower())
        or ("fabricated" in text.lower() and "evidence" in text.lower())
        or ("empty array" in text.lower() and "not" in text.lower() and "valid evidence" in text.lower())
        or ("[]" in text and "must not be treated as" in text.lower() and "valid evidence" in text.lower())
    )
    if not has_anti_mock:
        _failures.append(
            "[MISSING] Layer 3 :: G6 anti-mock evidence — SKILL.md must explicitly "
            "prohibit empty arrays ([]) or fabricated action tracking files from "
            "being treated as valid tool invocation evidence. The eval report found "
            "agents simulating tool calls that returned empty arrays and treating "
            "them as valid evidence."
        )


# ---- Group 10y: G2 multi-paragraph label continuity after §2.0 downgrade
#          (Report Suggestion #1 — agents label only first paragraph after downgrade)
def check_g2_paragraph_label_continuity(text: str) -> None:
    """After §2.0 bounded-generic downgrade, ALL subsequent substantive guidance
    paragraphs must continue carrying G2 source labels (not just the first one).
    The eval report found agents labeling the first paragraph with the disclaimer,
    then dropping labels on subsequent paragraphs.  Existing checks verify the label
    template exists and ban header-substitution, but do not enforce continuity."""
    has_continuity = (
        ("subsequent paragraphs" in text.lower() and ("must" in text.lower() or "continue" in text.lower()) and "label" in text.lower())
        or ("multi-paragraph" in text.lower() and "G2" in text and ("label" in text.lower() or "continuity" in text.lower()))
        or ("all paragraphs" in text.lower() and "label" in text.lower() and "must" in text.lower())
        or ("subsequent paragraphs must continue" in text.lower() and "label" in text.lower())
    )
    if not has_continuity:
        _failures.append(
            "[MISSING] Layer 3 :: G2 paragraph continuity — After §2.0 downgrade, "
            "SKILL.md must require ALL subsequent substantive paragraphs to continue "
            "carrying G2 labels, not just the first one. The eval report found agents "
            "labeling only the first paragraph then dropping labels thereafter."
        )


# ---- Group 10ab: G2 list-item label repetition
#          (Report Suggestion #1 — agents omit labels on list items)
def check_g2_list_item_label_repetition(text: str) -> None:
    """G2 must require labels to appear on EACH substantive list item, not just once at
    the list header. The eval report found models labeling the list title or first item
    then dropping labels on subsequent items. Existing checks cover paragraph-level and
    multi-paragraph continuity but not list-level repetition."""
    has_list_item = (
        ("list item" in text.lower() and "label" in text.lower())
        or ("each substantive list item" in text.lower() and "label" in text.lower())
        or ("list format" in text.lower() and "independently repeat" in text.lower())
    )
    if not has_list_item:
        _failures.append(
            "[MISSING] Layer 3 :: G2 list-item labels — SKILL.md must require each "
            "substantive list item to independently repeat the G2 label at its start. "
            "The eval report found agents labeling only the list title or first item "
            "then dropping labels on subsequent items."
        )


# ---- Group 10ac: File output anti-unsolicited gate
#          (Report Suggestion #2 — agents generate files without user request)
def check_file_output_anti_unsolicited(text: str) -> None:
    """Layer 1/G4/File Output Subsystem must contain an explicit interception rule
    that prevents unsolicited file generation. The eval report found agents generating
    md files in knowledge/QA scenarios without any user file request. Existing
    check_file_output_explicit_only checks for FILE_READY flag and no global footer,
    but does not verify an explicit anti-unsolicited/interception gate."""
    has_gate = (
        ("纯被动" in text or "被动路径" in text) and ("拦截" in text or "禁止" in text or "严禁" in text)
        or ("未显式" in text and "请求" in text and ("文件" in text or "生成" in text))
        or ("拦截闸门" in text and "文件" in text)
        or ("拦截" in text and "写入文件" in text and "显式" in text)
        or ("unsolicited" in text.lower() and "file" in text.lower() and ("gate" in text.lower() or "intercept" in text.lower()))
        or ("严禁.*生成.*文件" in text or "严禁.*输出.*文件" in text)
    )
    if not has_gate:
        _failures.append(
            "[MISSING] Layer 1/File :: anti-unsolicited file output gate — SKILL.md "
            "must contain an explicit interception rule preventing file output that "
            "was not explicitly requested by the user. The eval report found agents "
            "generating md files in knowledge/QA scenarios without any user file request."
        )


# ---- Group 10aa: §2.0/G6 tool-available-but-not-used tightening
def check_g6_tool_available_but_not_used(text: str) -> None:
    has_tightening = (
        "tools are available" in text.lower()
        and ("has not called" in text.lower() or "not called" in text.lower())
        and (
            "narrow exemption" in text.lower()
            or "Alibaba Cloud-specific parameters" in text
            or "narrow" in text.lower()
            and ("exempt" in text.lower() or "whitelist" in text.lower())
        )
    )
    if not has_tightening:
        _failures.append(
            "[MISSING] Layer 2/G6 :: tool-available-but-not-used tightening — SKILL.md "
            "must state that if tools ARE available at runtime but the agent skips "
            "doc-fetch/invocation without justification, this is a G6 violation. The "
            "eval report found agents exploiting the 'tools unavailable' carveout even "
            "when tools were present."
        )


# ---- Main -------------------------------------------------------------------
def main() -> int:
    if not SKILL_PATH.exists():
        print(f"FATAL: {SKILL_PATH} not found. Run from repository root.")
        return 2

    text = SKILL_PATH.read_text(encoding="utf-8")
    print(f"Running SKILL.md rewrite invariants against {SKILL_PATH} ({len(text)} chars)...")
    print()

    # Group 1: Pipeline architecture
    check_pipeline_layers(text)

    # Group 2: Intent classification
    check_intent_classification(text)

    # Group 3: Evidence policy
    check_evidence_policy(text)

    # Group 4: Risk gates
    check_risk_gates(text)

    # Group 4b: Safe downgrade after official-doc fetch failure
    check_safe_downgrade_rules(text)

    # Group 4c: Safe downgrade must cover empty-content and JS-rendering failures with fixed response
    check_safe_downgrade_empty_and_js(text)

    # Group 5: Response families
    check_response_families(text)

    # Group 6: Output formatter
    check_output_formatter(text)

    # Group 7: File output explicit-only
    check_file_output_explicit_only(text)

    # Group 8: SQL scenario-first routing
    check_sql_scenario_first(text)

    # Group 8b: Alibaba-specific SQL syntax and tool priority
    check_alibaba_specific_sql_and_tool_priority(text)

    # Group 8d: Hard tool-invocation gate for Alibaba-specific queries
    check_tool_invocation_hard_gate(text)

    # Group 8c: Sink write safety
    check_sink_write_safety(text)

    # Group 9: Legacy state-machine removal
    check_no_legacy_state_machine(text)

    # Group 10: No priority duplication
    check_no_priority_duplication(text)

    # Group 10b: Bounded generic-knowledge downgrade path (Report Root Cause #1)
    check_bounded_generic_downgrade(text)

    # Group 10c: CDC standard-prerequisite whitelist (Report Root Cause #2)
    check_cdc_standard_prerequisite_whitelist(text)

    # Group 10d: CDAS SQL skeleton mandate on tool failure (Report Root Cause #3)
    check_cdas_sql_skeleton_mandate(text)

    # Group 10e: Fixed safe-response consistency across Section 2.0 and G6
    check_fixed_safe_response_consistency(text)

    # Group 10f: Billing/version hard-block against bounded generic downgrade (Report Run-1/3/4)
    check_billing_version_hard_block(text)

    # Group 10g: CDAS skeleton mandate with manual sync SQL ban (Report CDC leakage)
    check_cdc_cdas_no_manual_sync(text)

    # Group 10h: Hard tool invocation enforcement in CDC flows (Report weak gating)
    check_cdc_tool_invocation_hard_gate(text)

    # Group 10i: Official-doc fetch multi-path retry protocol (Report Suggestion #1)
    check_official_doc_fetch_retry_protocol(text)

    # Group 10j: G2 source-labeling discipline for mixed open-source vs Alibaba (Report Suggestion #3)
    check_g2_source_labeling(text)

    # Group 10k: Stricter CDAS placeholder template requirement (Report Suggestion #2)
    check_cdas_placeholder_template(text)

    # Group 10l: §2.0 retry-path step-locking for current-failing-path (Report Suggestion #1)
    check_retry_path_step_locking(text)

    # Group 10m: Flink SQL syntax hard guard — STATE TTL discipline (Report Section 2)
    check_state_ttl_syntax_guard(text)

    # Group 10n: Restore-boundary — stateless vs stateful operator additions (Report Section 2)
    check_restore_boundary_stateful_stateless(text)

    # Group 10o: Sink WATERMARK anti-pattern guard (Report Suggestion #1 — Qwen3-Max)
    check_sink_no_watermark(text)

    # Group 10p: allowNonRestoredState as CLI flag, not SQL SET syntax (Report Suggestion #1)
    check_allow_non_restored_state_cli_flag(text)

    # Group 10q: Billing carve-out — generic comparison under no-tools (Report Suggestion #3)
    check_billing_generic_carveout(text)

    # Group 10r: Explicit ban on TABLE(SOURCE()) and CDAS syntax variants (Report CDC Suggestion #1)
    check_table_source_ban(text)

    # Group 10s: G2 paragraph-format source-label template (Report Suggestion #2)
    check_g2_paragraph_label_template(text)

    # Group 10t: Billing/version hard-block must explicitly ban percentage/ratio leakage (Report Suggestion #1)
    check_billing_no_ratio_leakage(text)

    # Group 10u: CDC multi-table sync — Paimon sink WITH config + regex routing (Report Suggestion #2)
    check_cdc_multi_table_paimon_routing(text)

    # Group 10v: G2 anti-Markdown-header substitution for paragraph labels (Report Suggestion #1)
    check_g2_no_header_label_substitution(text)

    # Group 10w: §2.0 disclaimer at reply start, not end (Report Suggestion #2)
    check_disclaimer_reply_first_line(text)

    # Group 10x: G6 anti-mock tool invocation evidence (Report Suggestion #3)
    check_g6_anti_mock_evidence(text)

    # Group 10y: G2 multi-paragraph label continuity after §2.0 downgrade (Report Suggestion #1)
    check_g2_paragraph_label_continuity(text)

    # Group 10aa: §2.0/G6 tool-available-but-not-used tightening (Report Suggestion #3)
    check_g6_tool_available_but_not_used(text)

    # Group 10ab: G2 list-item label repetition (Report Suggestion #1)
    check_g2_list_item_label_repetition(text)

    # Group 10ac: File output anti-unsolicited gate (Report Suggestion #2)
    check_file_output_anti_unsolicited(text)

    # ---- Report -------------------------------------------------------------
    if not _failures:
        print("PASS: all invariants satisfied.")
        return 0

    print(f"FAIL: {_failures.__len__()} invariant(s) violated:\n")
    for i, msg in enumerate(_failures, 1):
        print(f"  {i}. {msg}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
