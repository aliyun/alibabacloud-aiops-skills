"""sr-whoami: print current profile state — host, user, login time, grants summary."""

from __future__ import annotations

import click

from . import config
from .errors import SRConnectError


def run_whoami(profile: str) -> None:
    cfg_path = config.config_path(profile)
    if not cfg_path.exists():
        raise SRConnectError(
            f"No profile '{profile}'. Run sr-login first."
        )
    cfg = config.read(profile)
    grants = config.read_grants(profile)
    grant_lines = [ln for ln in grants.splitlines() if ln.strip()]

    click.echo(f"profile:        {profile}")
    click.echo(f"host:           {cfg.host}:{cfg.port}")
    click.echo(f"user:           {cfg.user}")
    click.echo(f"ssl:            {'yes' if cfg.ssl else 'no'}")
    click.echo(f"logged_in_at:   {cfg.logged_in_at or '(unknown)'}")
    click.echo(f"config_file:    {cfg_path}")

    if grant_lines:
        click.echo("")
        click.echo(f"grants ({len(grant_lines)} line(s)):")
        for ln in grant_lines:
            click.echo(f"  {ln}")
    else:
        click.echo("")
        click.echo("grants:         (not captured — SHOW GRANTS unavailable at login)")
