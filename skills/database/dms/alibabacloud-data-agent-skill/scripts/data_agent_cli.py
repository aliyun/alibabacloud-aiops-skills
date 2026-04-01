#!/usr/bin/env python3
"""Data Agent Unified CLI Tool - Entry Point.

See ``cli/`` package for implementation details.

Author: Tinker
Created: 2026-03-03
"""

import sys
from pathlib import Path

# Ensure local packages (data_agent, cli) are importable
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Re-export public API for backward compatibility (tests patch "data_agent_cli.XXX")
from cli import *  # noqa: F401,F403
from cli.parser import main


if __name__ == "__main__":
    main()
