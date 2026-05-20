"""click CLI entry points: sr-login / sr-logout / sr-whoami / srsql."""

from __future__ import annotations

import os
import sys

import click

from . import doctor as doctor_mod
from . import login as login_mod
from . import logout as logout_mod
from . import query as query_mod
from . import whoami as whoami_mod
from .errors import SRConnectError


def _read_password_interactive(prompt: str) -> str:
    if not sys.stdin.isatty():
        _fail(
            "sr-login needs a password but stdin is not a TTY. "
            "Set SR_PASSWORD in the environment for non-interactive login, "
            "or run sr-login from an interactive terminal."
        )
    return click.prompt(prompt, hide_input=True, err=True)


def _fail(msg: str, code: int = 1) -> None:
    click.echo(f"ERROR: {msg}", err=True)
    sys.exit(code)


@click.command(name="sr-login")
@click.option("--host", default=None, help="StarRocks FE host (required unless --from-env)")
@click.option("--port", default=9030, show_default=True, type=int)
@click.option("--user", default=None, help="StarRocks user account (required unless --from-env)")
@click.option(
    "--password", default=None, envvar="SR_PASSWORD",
    help="Password. Prefer interactive prompt; SR_PASSWORD env var supported."
)
@click.option(
    "--profile", default="default", show_default=True,
    help="Local profile name; supports multi-cluster (use SR_PROFILE to select at runtime)."
)
@click.option("--ssl", is_flag=True, help="Enable TLS (rarely needed; EMR Serverless uses plain TCP)")
@click.option(
    "--from-env", "from_env", is_flag=True,
    help=(
        "Non-interactive login for CI / sandbox setup scripts. "
        "Reads required SR_HOST / SR_USER / SR_PASSWORD and optional SR_PORT (default 9030) "
        "from the environment. Exits 2 if any required variable is missing."
    ),
)
def login_cmd(host, port, user, password, profile, ssl, from_env):
    """Log into a StarRocks cluster (registers credentials locally; overwrites if exists)."""
    if from_env:
        host = host or os.environ.get("SR_HOST")
        user = user or os.environ.get("SR_USER")
        sr_port = os.environ.get("SR_PORT")
        if sr_port:
            try:
                port = int(sr_port)
            except ValueError:
                _fail(f"SR_PORT must be an integer, got: {sr_port!r}")
        missing = [
            name for name, value in (
                ("SR_HOST", host),
                ("SR_USER", user),
                ("SR_PASSWORD", password),
            ) if not value
        ]
        if missing:
            _fail(
                "--from-env requires these environment variables to be set: "
                + ", ".join(missing),
                code=2,
            )
    else:
        if not host:
            _fail("Missing --host")
        if not user:
            _fail("Missing --user")
        if password is None:
            password = _read_password_interactive(f"Password for {user}@{host}")
    try:
        login_mod.run_login(
            host=host, port=port, user=user, password=password,
            profile=profile, ssl=ssl,
        )
    except SRConnectError as e:
        _fail(str(e))


@click.command(name="sr-logout")
@click.option(
    "--profile",
    default=lambda: os.environ.get("SR_PROFILE", "default"),
    show_default="default or $SR_PROFILE",
)
def logout_cmd(profile):
    """Remove local profile for a cluster."""
    try:
        logout_mod.run_logout(profile=profile)
    except SRConnectError as e:
        _fail(str(e))


@click.command(name="sr-whoami")
@click.option(
    "--profile",
    default=lambda: os.environ.get("SR_PROFILE", "default"),
    show_default="default or $SR_PROFILE",
)
def whoami_cmd(profile):
    """Print current profile state and captured grants."""
    try:
        whoami_mod.run_whoami(profile=profile)
    except SRConnectError as e:
        _fail(str(e))


@click.command(name="sr-doctor")
@click.option(
    "--host",
    default=lambda: os.environ.get("SR_HOST"),
    help="StarRocks FE host to diagnose (defaults to SR_HOST env var)",
)
@click.option(
    "--port",
    default=lambda: int(os.environ.get("SR_PORT", "9030")),
    show_default="9030 or $SR_PORT",
    type=int,
)
def doctor_cmd(host, port):
    """Diagnose connection failures and print actionable next steps."""
    if not host:
        _fail("Missing --host (or set SR_HOST in the environment)")
    sys.exit(doctor_mod.run_doctor(host, port))


@click.command(name="srsql")
@click.option("-e", "--execute", "sql", required=True, help="SQL to execute")
@click.option(
    "--profile",
    default=lambda: os.environ.get("SR_PROFILE", "default"),
    show_default="default or $SR_PROFILE",
)
@click.option(
    "-f", "--format", "fmt",
    default=lambda: os.environ.get("SR_FORMAT", "tsv"),
    type=click.Choice(query_mod.SUPPORTED_FORMATS),
    help="Output format",
)
@click.option("--yes", is_flag=True, help="Confirm execution of non-READ statements")
@click.option(
    "--dry-run", is_flag=True,
    help="Classify SQL and print verdict; do not execute"
)
def srsql_cmd(sql, profile, fmt, yes, dry_run):
    """Execute SQL against a logged-in cluster. Non-READ statements require --yes."""
    try:
        rc = query_mod.run_query(
            profile=profile, sql=sql, fmt=fmt,
            confirm=yes, dry_run=dry_run,
        )
        sys.exit(rc)
    except SRConnectError as e:
        _fail(str(e))
