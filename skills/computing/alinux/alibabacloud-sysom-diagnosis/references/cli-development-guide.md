# SysOM CLI Development Guide

Welcome to `sysom_cli` development. This guide provides an implementation-oriented overview for adding or extending commands.

> Notes:
> - `memory` subsystem includes `classify` / `memgraph` / `oom` / `javamem` (default: quick local triage).
> - Optional `--deep-diagnosis` triggers remote deep diagnosis.
> - Non-memory remote entrypoints are `io` / `net` / `load`.
> - For OpenAPI invocation contract, see [invoke-diagnosis.md](./invoke-diagnosis.md).
> - For capability overview and behavior constraints, see [SKILL.md](../SKILL.md).

## Table of Contents

- [Architecture](#architecture)
- [Environment Setup](#environment-setup)
- [Adding Commands](#adding-commands)
- [Execution Modes](#execution-modes)
- [Coding Conventions](#coding-conventions)
- [Testing and Debugging](#testing-and-debugging)
- [Troubleshooting](#troubleshooting)

## Architecture

### Directory Layout (Simplified)

```text
sysom_cli/
├── lib/             # shared utilities (schema, auth, specialty args, helpers)
├── core/            # framework (BaseCommand, registry, executor)
├── precheck/        # top-level precheck command
├── memory/          # memory subsystem commands
├── io/              # IO subsystem commands
├── net/             # network subsystem commands
├── load/            # load subsystem commands
├── diagnosis/       # remote invoke subsystem (maintainer-facing)
└── __main__.py      # CLI entrypoint
```

### Command Types

1. **Top-level commands**
   - Own directory directly under `sysom_cli/`
   - Contain `command.py`
   - Example: `precheck`
   - Usage: `osops precheck`

2. **Subsystem commands**
   - Reside under a subsystem directory
   - Each subcommand has its own `command.py`
   - Examples: `memory classify`, `io iofsstat`, `net packetdrop`, `load delay`

### Core Components

- `BaseCommand`: abstract command base class
- `CommandRegistry`: auto discovery and registration via `@command_metadata`
- `CommandExecutor`: execution dispatch by mode/environment

## Environment Setup

### 1) Initialize dependencies

```bash
cd /path/to/sysom-diagnosis
./scripts/init.sh
```

### 2) Set PYTHONPATH (if needed)

```bash
export PYTHONPATH="/path/to/sysom-diagnosis/scripts:$PYTHONPATH"
```

### 3) Verify CLI

```bash
python3 -m sysom_cli --list-capabilities
```

## Adding Commands

### Add a subsystem command (example: `memory leak`)

#### Step 1: create directory

```bash
mkdir -p scripts/sysom_cli/memory/leak
touch scripts/sysom_cli/memory/leak/__init__.py
```

#### Step 2: create `command.py`

```python
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata


@command_metadata(
    name="leak",
    help="Memory leak detection and analysis",
    subsystem="memory",
    args=[
        (["--pid"], {"type": int, "help": "Process PID"}),
        (["--duration"], {"type": int, "default": 60, "help": "Observation time in seconds"}),
        (["--threshold"], {"type": float, "default": 10.0, "help": "Leak threshold (MB/s)"}),
    ],
)
class LeakCommand(BaseCommand):
    @property
    def command_name(self) -> str:
        return "leak"

    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }

    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        from sysom_cli.lib.schema import envelope, agent_block

        pid = getattr(ns, "pid", None)
        duration = getattr(ns, "duration", 60)
        result_data = {
            "pid": pid,
            "leak_detected": False,
            "leak_rate_mb_s": 0.0,
        }
        return envelope(
            action="memory_leak",
            ok=True,
            agent=agent_block("normal", f"Observed process {pid} for {duration}s, no leak detected."),
            data=result_data,
            execution={"mode": "local", "stage": "leak"},
        )
```

#### Step 3: use command directly

No extra registration file changes are required.

```bash
./scripts/osops.sh memory leak --help
./scripts/osops.sh memory leak --pid 1234 --duration 120
```

### Add a top-level command (example: `version`)

Use the same pattern under `scripts/sysom_cli/version/command.py` and set `subsystem` accordingly (or omit subsystem for top-level).

## Execution Modes

Typical modes:

- `LOCAL`: execute local quick checks/collection
- `REMOTE`: execute remote diagnosis through SysOM
- `HYBRID`: combine local and remote phases

Select mode through framework logic and command capability declarations.

## Coding Conventions

- Keep command implementation thin; move shared logic to `lib/`.
- Reuse envelope schema helpers; keep output machine-consumable.
- Preserve existing field contracts in `agent` and `data`.
- Keep security boundaries: no secrets in logs/chat output.
- For remote paths, prefer precheck-gated flows.

## Testing and Debugging

- Unit-test parser and command behavior under `scripts/sysom_cli/tests`.
- Validate envelope fields with representative success/failure cases.
- For remote features, run `./scripts/osops.sh precheck` before invoking diagnosis.
- Inspect `error.code`, `agent.findings`, and `data.remediation` for failure triage.

## Troubleshooting

- Command not discovered:
  - ensure `command.py` exists in correct directory
  - ensure `@command_metadata` is present and valid
- Runtime import issues:
  - verify `PYTHONPATH` and project initialization (`./scripts/init.sh`)
- Remote calls fail:
  - run precheck
  - verify permissions and activation through [openapi-permission-guide.md](./openapi-permission-guide.md)
  - verify invocation contract through [invoke-diagnosis.md](./invoke-diagnosis.md)
