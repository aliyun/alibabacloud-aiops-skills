#!/usr/bin/env python3
"""Environment bootstrap — zero third-party dependencies.

This module MUST only use the Python standard library so it can run
before any pip packages are installed.
"""

from __future__ import annotations

import subprocess
import sys

_MIN_PYTHON = (3, 8)

_REQUIRED_PACKAGES = [
    ("alibabacloud_credentials", "alibabacloud_credentials==1.0.8"),
    ("alibabacloud_tea_openapi", "alibabacloud_tea_openapi==0.4.4"),
    ("darabonba", "darabonba-core==1.0.5"),
]


def ensure_dependencies() -> None:
    """Check Python version and install missing pip packages.

    Call this once at the start of a session before any API work.
    Raises SystemExit if the Python version is too old.
    """
    if sys.version_info < _MIN_PYTHON:
        sys.exit(
            f"Python >= {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]} is required, "
            f"but current version is {sys.version.split()[0]}."
        )

    missing: list[str] = []
    for import_name, pip_spec in _REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_spec)

    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        # only install packages in _REQUIRED_PACKAGES, these packages are Alibaba Cloud's official SDK.
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing],
            stdout=subprocess.DEVNULL,
        )
