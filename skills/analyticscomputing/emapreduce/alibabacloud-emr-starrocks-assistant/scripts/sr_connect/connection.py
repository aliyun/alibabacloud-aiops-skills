"""pymysql-based StarRocks connection helpers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import pymysql

from .errors import ConnectionError as SRConnectionError


@dataclass
class ConnParams:
    host: str
    port: int = 9030
    user: str = ""
    password: str = ""
    ssl: bool = False
    database: str | None = None
    connect_timeout: int = 10


def connect(params: ConnParams) -> pymysql.connections.Connection:
    """Open a pymysql connection. Raises SRConnectionError on failure."""
    kwargs = dict(
        host=params.host,
        port=params.port,
        user=params.user,
        password=params.password,
        connect_timeout=params.connect_timeout,
        charset="utf8mb4",
        autocommit=True,
    )
    if params.database:
        kwargs["database"] = params.database
    if params.ssl:
        # Empty dict is the pymysql idiom for "enable TLS with defaults".
        kwargs["ssl"] = {}
    try:
        return pymysql.connect(**kwargs)
    except pymysql.err.OperationalError as e:
        raise SRConnectionError(
            f"Cannot connect to {params.host}:{params.port} as {params.user}: "
            f"{e.args[1] if len(e.args) > 1 else e}"
        ) from e


@contextmanager
def connection(params: ConnParams) -> Iterator[pymysql.connections.Connection]:
    conn = connect(params)
    try:
        yield conn
    finally:
        conn.close()


def ping(params: ConnParams) -> None:
    """Verify connection + run SELECT 1. Raises on any failure."""
    with connection(params) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()


def capture_grants(conn) -> str:
    """Run SHOW GRANTS FOR CURRENT_USER() and return joined raw text.

    Returns empty string on failure (older StarRocks may not support this);
    callers should treat capabilities as unknown in that case.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW GRANTS FOR CURRENT_USER()")
            rows = cur.fetchall()
    except pymysql.err.MySQLError:
        return ""
    lines: list[str] = []
    for row in rows:
        for v in row:
            if isinstance(v, str) and v.strip():
                lines.append(v.strip())
    return "\n".join(lines)
