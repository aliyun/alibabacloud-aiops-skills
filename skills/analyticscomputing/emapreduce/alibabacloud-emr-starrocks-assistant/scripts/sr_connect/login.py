"""sr-login: register a cluster credential locally + smoke-test connection."""

from __future__ import annotations

from datetime import datetime, timezone

import click

from . import config, connection, doctor
from .errors import ConnectionError as SRConnectionError


def run_login(
    host: str,
    port: int,
    user: str,
    password: str,
    profile: str,
    ssl: bool,
) -> None:
    """Connect with user-provided creds, capture grants, write profile."""
    click.echo(f"[..] Connecting to {host}:{port} as {user}", err=True)
    params = connection.ConnParams(
        host=host, port=port, user=user, password=password, ssl=ssl
    )
    try:
        ctx = connection.connection(params)
        conn = ctx.__enter__()
    except SRConnectionError:
        click.echo("", err=True)
        click.echo(doctor.format_diagnosis(doctor.diagnose(host, port)), err=True)
        raise
    try:
        click.echo("[OK] Connection verified", err=True)
        grants = connection.capture_grants(conn)
    finally:
        ctx.__exit__(None, None, None)

    config.write(
        profile,
        config.ProfileConfig(
            host=host, port=port, user=user, password=password, ssl=ssl,
            logged_in_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    if grants:
        config.write_grants(profile, grants)
        click.echo(f"[OK] Captured {len(grants.splitlines())} grant line(s)", err=True)
    else:
        click.echo("[!!] SHOW GRANTS unavailable; capability hints disabled", err=True)

    cfg_path = config.config_path(profile)
    click.echo(f"[OK] Profile '{profile}' written to {cfg_path}", err=True)
    click.echo("", err=True)
    click.echo(f"   Try: srsql -e \"SELECT CURRENT_VERSION()\"", err=True)
    if profile != "default":
        click.echo(f"   Or:  SR_PROFILE={profile} srsql -e \"...\"", err=True)
