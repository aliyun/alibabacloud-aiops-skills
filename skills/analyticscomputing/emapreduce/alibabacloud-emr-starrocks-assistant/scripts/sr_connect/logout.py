"""sr-logout: remove the local profile + grants for a cluster."""

from __future__ import annotations

import click

from . import config


def run_logout(profile: str) -> None:
    """Delete local profile files. No cluster-side action."""
    cfg_path = config.config_path(profile)
    if not cfg_path.exists():
        click.echo(f"[..] No profile '{profile}' to remove", err=True)
        return
    config.remove(profile)
    click.echo(f"[OK] Removed profile '{profile}' ({cfg_path})", err=True)
