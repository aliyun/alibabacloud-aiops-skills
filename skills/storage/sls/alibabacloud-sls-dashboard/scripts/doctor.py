#!/usr/bin/env python3
"""Check local dashboard prerequisites and print suggested commands.

    python3 scripts/doctor.py
    python3 scripts/doctor.py --offline
    python3 scripts/doctor.py --aliyun /path/to/aliyun --with-sdk
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib
from importlib import metadata
import io
import platform
import re
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

CLI_MINIMUM = (3, 3, 22)
PACKAGES = (
    ("jsonschema", "jsonschema", "Draft202012Validator", (4, 18, 0), (5, 0, 0)),
    ("alibabacloud-credentials", "alibabacloud_credentials.client", "Client", (1, 0, 3), (2, 0, 0)),
    ("alibabacloud-sls20201230", "alibabacloud_sls20201230.client", "Client", (5, 15, 1), (6, 0, 0)),
)
SLS_COMMANDS = ("get-logs-v2", "get-dashboard", "create-dashboard", "update-dashboard", "delete-dashboard")


def version_number(value):
    match = re.search(r"(?<![\d.])(\d+)\.(\d+)\.(\d+)(?![\d.])", value)
    return tuple(map(int, match.groups())) if match else None


def probe(command, timeout):
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None, ""
    return process.returncode, process.stdout.strip()


def shell_command(arguments):
    if platform.system() == "Windows":
        return "& " + " ".join("'" + argument.replace("'", "''") + "'" for argument in arguments)
    return shlex.join(arguments)


def cli_install_commands():
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin":
        archive = "macosx-latest-universal.tgz"
    elif system == "Linux" and machine in {"x86_64", "amd64", "arm64", "aarch64"}:
        architecture = "arm64" if machine in {"arm64", "aarch64"} else "amd64"
        archive = "linux-latest-" + architecture + ".tgz"
    elif system == "Windows":
        return [
            'New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\\AliyunCLI"',
            'Invoke-WebRequest https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip '
            '-OutFile "$env:TEMP\\aliyun-cli.zip"',
            'Expand-Archive -Force "$env:TEMP\\aliyun-cli.zip" "$env:LOCALAPPDATA\\AliyunCLI"',
            '$env:PATH = "$env:LOCALAPPDATA\\AliyunCLI;" + $env:PATH',
        ]
    else:
        return []
    return [
        'mkdir -p "$HOME/.local/bin"',
        'curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-' + archive +
        ' | tar -xz -C "$HOME/.local/bin" aliyun',
        'chmod +x "$HOME/.local/bin/aliyun"',
        'export PATH="$HOME/.local/bin:$PATH"',
    ]


def check_environment(aliyun="aliyun", offline=False, with_sdk=False, timeout=15):
    checks = []

    def add(name, status, detail, commands=()):
        checks.append({"name": name, "status": status, "detail": detail, "commands": list(commands)})

    python_ok = sys.version_info >= (3, 10)
    add("Python", "ok" if python_ok else "outdated",
        platform.python_version() + " at " + sys.executable + " (requires 3.10+)",
        () if python_ok else ("python3.10 scripts/doctor.py",))
    for name, module_name, attribute, minimum, maximum in PACKAGES[:3 if with_sdk else 1]:
        requirement = (name + ">=" + ".".join(map(str, minimum[:2] if name == "jsonschema" else minimum)) +
                       ",<" + str(maximum[0]))
        command = shell_command([sys.executable, "-m", "pip", "install", "--upgrade", requirement])
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            add(name, "missing", "Not installed in this Python environment", (command,))
            continue
        numeric = version_number(version)
        if numeric is None or not minimum <= numeric < maximum:
            add(name, "incompatible", version + " (requires " + requirement + ")", (command,))
            continue
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                getattr(importlib.import_module(module_name), attribute)
        except Exception:
            reinstall = shell_command([sys.executable, "-m", "pip", "install", "--force-reinstall", requirement])
            add(name, "unavailable", version + " is installed but cannot be imported", (reinstall,))
        else:
            add(name, "ok", version)
    if offline:
        return checks

    executable = shutil.which(aliyun)
    if executable is None:
        add("Aliyun CLI", "missing", aliyun + " was not found; install in a user-writable directory",
            cli_install_commands())
        return checks
    code, output = probe([executable, "version"], timeout)
    numeric = version_number(output)
    if code != 0 or numeric is None:
        add("Aliyun CLI", "unavailable", "Could not obtain the version at " + executable,
            (shell_command([executable, "version"]),))
        return checks
    cli_ok = numeric >= CLI_MINIMUM
    add("Aliyun CLI", "ok" if cli_ok else "outdated",
        ".".join(map(str, numeric)) + " at " + executable + " (requires 3.3.22+)",
        () if cli_ok else cli_install_commands())
    code, _ = probe([executable, "configure", "list"], timeout)
    if code == 0:
        add("CLI profiles", "ok", "configure list succeeded")
    else:
        add("CLI profiles", "needs_configuration",
            "Profile check failed. User action required: configure an Aliyun CLI profile before cloud operations.",
            (shell_command([executable, "configure"]),))
    code, output = probe([executable, "sls", "version"], timeout)
    numeric = version_number(output)
    if code != 0 or numeric is None:
        status = "unavailable" if code is None else "missing"
        add("SLS plugin", status, "Could not obtain the SLS plugin version",
            (shell_command([executable, "plugin", "install", "--names", "sls"]),))
        return checks
    add("SLS plugin", "ok", ".".join(map(str, numeric)))
    missing = []
    for name in SLS_COMMANDS:
        code, output = probe([executable, "help", "sls", name], timeout)
        if code != 0 or not output:
            missing.append(name)
    if missing:
        add("SLS commands", "unavailable", "Help unavailable for: " + ", ".join(missing),
            (shell_command([executable, "plugin", "update", "--name", "sls"]),))
    else:
        add("SLS commands", "ok", ", ".join(SLS_COMMANDS))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliyun", default="aliyun", help="Aliyun CLI executable name or path")
    parser.add_argument("--offline", action="store_true", help="Check only Python dependencies")
    parser.add_argument("--with-sdk", action="store_true", help="Also check Metric StoreView and Report SDK packages")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout in seconds for each local CLI check")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    checks = check_environment(args.aliyun, args.offline, args.with_sdk, args.timeout)
    for item in checks:
        print("[" + item["status"].upper() + "] " + item["name"] + ": " + item["detail"])
        if item["commands"]:
            print("Suggested commands:")
            for command in item["commands"]:
                print("  " + command)
    if any(item["name"] == "Aliyun CLI" and item["status"] in {"missing", "outdated"} for item in checks):
        print('Use the installed CLI through PATH or pass --aliyun "$HOME/.local/bin/aliyun" '
              'to doctor.py and cloud commands on Linux/macOS.')
    return 0 if all(item["status"] == "ok" for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
