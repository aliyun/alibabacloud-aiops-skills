"""Classify SQL statements as READ vs non-READ for the srsql execution gate.

Uses sqlglot with dialect="starrocks". Conservative: only inspects AST root
node class names; does not depend on deep parsing accuracy.

When sqlglot cannot parse a statement (StarRocks-specific syntax it doesn't
model yet, or genuine syntax errors), falls back to a leading-keyword match.
The fallback is best-effort and marked with a warning so the gate / Skill
can surface it to the user.

Verdict semantics for the gate:
    READ        -> executes directly
    everything else (incl. UNKNOWN) -> requires --yes
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import sqlglot
import sqlglot.errors
import sqlglot.expressions as exp


DIALECT = "starrocks"


class Verdict(str, Enum):
    READ = "read"
    WRITE_DML = "write_dml"   # INSERT / UPDATE / DELETE / MERGE / LOAD
    DDL = "ddl"               # CREATE / ALTER / DROP / TRUNCATE
    ADMIN = "admin"           # GRANT / REVOKE / CREATE USER / SET CONFIG ...
    SESSION = "session"       # SET / USE / COMMIT / ROLLBACK
    UNKNOWN = "unknown"       # parse failure and no keyword match


# AST root class name -> Verdict.
# Stable surface: depends only on root-level node identity, never deep AST.
_ROOT_CLASS_TO_VERDICT: dict[str, Verdict] = {
    # Read
    "Select": Verdict.READ,
    "Union": Verdict.READ,
    "Intersect": Verdict.READ,
    "Except": Verdict.READ,
    "With": Verdict.READ,
    "Subquery": Verdict.READ,
    "Show": Verdict.READ,
    "Describe": Verdict.READ,
    "Pragma": Verdict.READ,
    # Write (DML)
    "Insert": Verdict.WRITE_DML,
    "Update": Verdict.WRITE_DML,
    "Delete": Verdict.WRITE_DML,
    "Merge": Verdict.WRITE_DML,
    # DDL
    "Create": Verdict.DDL,
    "Drop": Verdict.DDL,
    "Alter": Verdict.DDL,
    "AlterColumn": Verdict.DDL,
    "TruncateTable": Verdict.DDL,
    # Admin (sqlglot has dedicated classes for some)
    "Kill": Verdict.ADMIN,
    # Session-scoped
    "Set": Verdict.SESSION,
    "Use": Verdict.SESSION,
    "Transaction": Verdict.SESSION,
    "Commit": Verdict.SESSION,
    "Rollback": Verdict.SESSION,
}


# Leading-keyword -> Verdict, used by:
#   (a) exp.Command (sqlglot's catch-all for un-modeled statements)
#   (b) Parse-failure fallback (sqlglot couldn't parse at all)
# Ordering is critical: longer / more-specific prefixes MUST come before
# shorter ones, because the first prefix match wins.
_COMMAND_VERBS: list[tuple[str, Verdict]] = [
    # Two-word: user/role admin
    ("CREATE USER", Verdict.ADMIN),
    ("CREATE ROLE", Verdict.ADMIN),
    ("DROP USER", Verdict.ADMIN),
    ("DROP ROLE", Verdict.ADMIN),
    ("ALTER USER", Verdict.ADMIN),
    ("ALTER ROLE", Verdict.ADMIN),
    ("SET PASSWORD", Verdict.ADMIN),
    ("SET DEFAULT", Verdict.ADMIN),       # SET DEFAULT ROLE
    ("SET ROLE", Verdict.SESSION),
    # Two-word: write/refresh
    ("SUBMIT TASK", Verdict.WRITE_DML),
    ("REFRESH MATERIALIZED", Verdict.WRITE_DML),
    # Single-word admin
    ("GRANT", Verdict.ADMIN),
    ("REVOKE", Verdict.ADMIN),
    ("ADMIN", Verdict.ADMIN),             # ADMIN SET CONFIG / REPAIR / ...
    ("CANCEL", Verdict.ADMIN),
    ("PAUSE", Verdict.ADMIN),
    ("RESUME", Verdict.ADMIN),
    ("STOP", Verdict.ADMIN),
    ("KILL", Verdict.ADMIN),
    ("ANALYZE", Verdict.ADMIN),
    ("BACKUP", Verdict.ADMIN),
    ("RESTORE", Verdict.ADMIN),
    ("RECOVER", Verdict.ADMIN),
    ("INSTALL", Verdict.ADMIN),
    ("UNINSTALL", Verdict.ADMIN),
    # Write (job-level commands)
    ("LOAD", Verdict.WRITE_DML),
    ("REFRESH", Verdict.WRITE_DML),
    # Read
    ("EXPLAIN", Verdict.READ),
    ("DESCRIBE", Verdict.READ),
    ("DESC", Verdict.READ),
    ("HELP", Verdict.READ),
    ("SHOW", Verdict.READ),
    ("WITH", Verdict.READ),
    ("SELECT", Verdict.READ),
    # Session
    ("USE", Verdict.SESSION),
    ("SET", Verdict.SESSION),
    # DDL fallback (must come AFTER more-specific user/role variants above)
    ("CREATE", Verdict.DDL),
    ("DROP", Verdict.DDL),
    ("ALTER", Verdict.DDL),
    ("TRUNCATE", Verdict.DDL),
    ("RENAME", Verdict.DDL),
    # DML fallback
    ("INSERT", Verdict.WRITE_DML),
    ("UPDATE", Verdict.WRITE_DML),
    ("DELETE", Verdict.WRITE_DML),
    ("MERGE", Verdict.WRITE_DML),
]


_TYPE_LABEL: dict[str, str] = {
    "Select": "SELECT",
    "Union": "UNION",
    "Intersect": "INTERSECT",
    "Except": "EXCEPT",
    "With": "WITH (CTE)",
    "Subquery": "SUBQUERY",
    "Show": "SHOW",
    "Describe": "DESCRIBE",
    "Pragma": "PRAGMA",
    "Insert": "INSERT",
    "Update": "UPDATE",
    "Delete": "DELETE",
    "Merge": "MERGE",
    "Create": "CREATE",
    "Drop": "DROP",
    "Alter": "ALTER",
    "AlterColumn": "ALTER COLUMN",
    "TruncateTable": "TRUNCATE TABLE",
    "Kill": "KILL",
    "Set": "SET",
    "Use": "USE",
    "Transaction": "TRANSACTION",
    "Commit": "COMMIT",
    "Rollback": "ROLLBACK",
}


@dataclass(frozen=True)
class Classification:
    verdict: Verdict
    statement_type: str
    target: str | None = None
    warning: str | None = None

    @property
    def is_read_only(self) -> bool:
        return self.verdict == Verdict.READ


def classify(sql: str) -> list[Classification]:
    """Classify each top-level statement in `sql`. Multi-statement supported."""
    if not sql or not sql.strip():
        return [Classification(
            verdict=Verdict.UNKNOWN,
            statement_type="EMPTY",
            warning="no SQL statement detected",
        )]
    try:
        asts = sqlglot.parse(sql, dialect=DIALECT)
    except sqlglot.errors.ParseError as e:
        return [_fallback_keyword_classify(sql, parse_error=str(e))]
    if not asts:
        return [_fallback_keyword_classify(sql, parse_error="no statement detected (comments only?)")]
    results = []
    for ast in asts:
        if ast is None:
            results.append(_fallback_keyword_classify(sql, parse_error="statement could not be parsed"))
        else:
            results.append(_classify_node(ast))
    return results


def classify_one(sql: str) -> Classification:
    """Single decision for a SQL blob. Multi-statement aggregates to the
    most permission-demanding verdict (any non-READ wins)."""
    results = classify(sql)
    if not results:
        return Classification(
            verdict=Verdict.UNKNOWN,
            statement_type="EMPTY",
            warning="no SQL statement detected",
        )
    if len(results) == 1:
        return results[0]
    non_reads = [r for r in results if not r.is_read_only]
    if non_reads:
        first = non_reads[0]
        return Classification(
            verdict=first.verdict,
            statement_type=f"MIXED ({len(results)} stmts, first non-READ: {first.statement_type})",
            target=first.target,
            warning=f"batch contains {len(results)} statements; gating on first non-READ",
        )
    return Classification(
        verdict=Verdict.READ,
        statement_type=f"MULTI READ ({len(results)} stmts)",
    )


def _classify_node(ast: exp.Expression) -> Classification:
    cls_name = type(ast).__name__
    verdict = _ROOT_CLASS_TO_VERDICT.get(cls_name)
    if verdict is not None:
        return Classification(
            verdict=verdict,
            statement_type=_TYPE_LABEL.get(cls_name, cls_name.upper()),
            target=_extract_target(ast),
        )
    if isinstance(ast, exp.Command):
        verb = (ast.this or "").upper().strip()
        rest = ""
        if ast.expression is not None:
            rest = getattr(ast.expression, "name", "") or ""
        full = f"{verb} {rest}".upper().strip()
        for prefix, v in _COMMAND_VERBS:
            if full.startswith(prefix):
                return Classification(verdict=v, statement_type=prefix)
        return Classification(
            verdict=Verdict.UNKNOWN,
            statement_type=verb or "UNKNOWN",
            warning=f"unrecognized statement verb: {verb!r}",
        )
    return Classification(
        verdict=Verdict.UNKNOWN,
        statement_type=cls_name.upper(),
        warning=f"unrecognized AST root: {cls_name}",
    )


def _fallback_keyword_classify(sql: str, parse_error: str) -> Classification:
    """Best-effort classification by leading keyword when sqlglot fails."""
    leader = _leading_keyword(sql)
    if not leader:
        return Classification(
            verdict=Verdict.UNKNOWN,
            statement_type="EMPTY",
            warning=parse_error,
        )
    for prefix, v in _COMMAND_VERBS:
        if leader.startswith(prefix):
            return Classification(
                verdict=v,
                statement_type=prefix,
                warning=(
                    f"sqlglot could not parse; classified by leading keyword "
                    f"(best-effort). Reason: {parse_error[:120]}"
                ),
            )
    one_word = leader.split()[0]
    return Classification(
        verdict=Verdict.UNKNOWN,
        statement_type=one_word,
        warning=f"unrecognized leading keyword {one_word!r}; parse error: {parse_error[:120]}",
    )


def _leading_keyword(sql: str) -> str:
    """Strip leading comments + whitespace, return up to 3 leading words uppercased."""
    s = sql
    while True:
        s = s.lstrip()
        if s.startswith("--"):
            nl = s.find("\n")
            s = s[nl + 1:] if nl >= 0 else ""
        elif s.startswith("#"):
            nl = s.find("\n")
            s = s[nl + 1:] if nl >= 0 else ""
        elif s.startswith("/*"):
            end = s.find("*/")
            s = s[end + 2:] if end >= 0 else ""
        else:
            break
    if not s:
        return ""
    parts = s.split(None, 3)
    return " ".join(parts[:3]).upper()


def _extract_target(ast: exp.Expression) -> str | None:
    """Best-effort target table/object name for display. Returns None when
    the target is not a simple identifier (e.g. SELECT subqueries)."""
    target_node = getattr(ast, "this", None)
    if target_node is None:
        return None
    if isinstance(target_node, exp.Table):
        return target_node.sql(dialect=DIALECT)
    if isinstance(target_node, exp.Schema):
        inner = target_node.this
        if isinstance(inner, exp.Table):
            return inner.sql(dialect=DIALECT)
    if hasattr(target_node, "sql"):
        try:
            s = target_node.sql(dialect=DIALECT)
            if len(s) <= 100 and "\n" not in s:
                return s
        except Exception:
            pass
    return None
