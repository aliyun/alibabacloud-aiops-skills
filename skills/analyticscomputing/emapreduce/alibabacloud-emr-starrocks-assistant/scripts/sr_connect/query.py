"""srsql: classify SQL → READ executes; non-READ requires --yes; supports multiple output formats."""

from __future__ import annotations

import json
import sys
from typing import Any, Iterable

import click
import pymysql

from . import config, connection
from .classify import classify_one
from .errors import SRConnectError


SUPPORTED_FORMATS = ("tsv", "json", "table", "markdown", "vertical")


def run_query(
    profile: str,
    sql: str,
    fmt: str = "tsv",
    confirm: bool = False,
    dry_run: bool = False,
) -> int:
    """Execute sql and print results. Returns exit code.

    Gate:
      - READ executes directly.
      - non-READ (including UNKNOWN / parse failures) requires confirm=True.
      - dry_run prints classification verdict only; never executes.
    """
    if fmt not in SUPPORTED_FORMATS:
        click.echo(f"Unknown format: {fmt} (supported: {', '.join(SUPPORTED_FORMATS)})", err=True)
        return 2

    cls = classify_one(sql)

    if dry_run:
        _print_classification(cls)
        return 0

    if not cls.is_read_only and not confirm:
        lines = [
            "Refusing to execute non-READ SQL without --yes.",
            f"  verdict:        {cls.verdict.value}",
            f"  statement_type: {cls.statement_type}",
        ]
        if cls.target:
            lines.append(f"  target:         {cls.target}")
        if cls.warning:
            lines.append(f"  warning:        {cls.warning}")
        lines.append("  Re-run with --yes to confirm execution.")
        raise SRConnectError("\n".join(lines))

    if not cls.is_read_only and cls.warning:
        click.echo(f"[!!] {cls.warning}", err=True)

    cfg = config.read(profile)  # raises ConfigNotFoundError
    params = connection.ConnParams(
        host=cfg.host, port=cfg.port, user=cfg.user, password=cfg.password, ssl=cfg.ssl,
    )

    try:
        with connection.connection(params) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description is None:
                    click.echo(f"Affected rows: {cur.rowcount}", err=True)
                    return 0
                columns = [d[0] for d in cur.description]
                rows = cur.fetchall()
    except pymysql.err.MySQLError as e:
        errno = e.args[0] if e.args else "?"
        msg = e.args[1] if len(e.args) > 1 else str(e)
        raise SRConnectError(f"SQL error [{errno}]: {msg}") from e

    _render(columns, rows, fmt)
    return 0


def _print_classification(cls) -> None:
    click.echo(f"verdict:        {cls.verdict.value}", err=True)
    click.echo(f"statement_type: {cls.statement_type}", err=True)
    if cls.target:
        click.echo(f"target:         {cls.target}", err=True)
    if cls.warning:
        click.echo(f"warning:        {cls.warning}", err=True)
    click.echo(f"would_execute:  {'yes' if cls.is_read_only else 'requires --yes'}", err=True)


def _render(columns: list[str], rows: Iterable[tuple], fmt: str) -> None:
    rows = list(rows)
    if fmt == "tsv":
        _render_tsv(columns, rows)
    elif fmt == "json":
        _render_json(columns, rows)
    elif fmt == "table":
        _render_table(columns, rows)
    elif fmt == "markdown":
        _render_markdown(columns, rows)
    elif fmt == "vertical":
        _render_vertical(columns, rows)


def _s(v: Any) -> str:
    if v is None:
        return "NULL"
    return str(v)


def _render_tsv(columns: list[str], rows: list[tuple]) -> None:
    sys.stdout.write("\t".join(columns) + "\n")
    for r in rows:
        sys.stdout.write("\t".join(_s(v) for v in r) + "\n")


def _render_json(columns: list[str], rows: list[tuple]) -> None:
    out = [dict(zip(columns, (_s_json(v) for v in r))) for r in rows]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


def _s_json(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def _render_table(columns: list[str], rows: list[tuple]) -> None:
    widths = [len(c) for c in columns]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(_s(v)))

    def sep() -> str:
        return "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def fmt_row(vals: Iterable[Any]) -> str:
        return "| " + " | ".join(_s(v).ljust(widths[i]) for i, v in enumerate(vals)) + " |"

    print(sep())
    print(fmt_row(columns))
    print(sep())
    for r in rows:
        print(fmt_row(r))
    print(sep())


def _render_markdown(columns: list[str], rows: list[tuple]) -> None:
    print("| " + " | ".join(columns) + " |")
    print("| " + " | ".join("---" for _ in columns) + " |")
    for r in rows:
        print("| " + " | ".join(_s(v).replace("|", "\\|") for v in r) + " |")


def _render_vertical(columns: list[str], rows: list[tuple]) -> None:
    width = max((len(c) for c in columns), default=0)
    for i, r in enumerate(rows, 1):
        print(f"*************************** {i}. row ***************************")
        for c, v in zip(columns, r):
            print(f"{c.rjust(width)}: {_s(v)}")
