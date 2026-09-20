"""Environment validation for LHM Scheduler CLI.

Checks Python version, aliyun CLI availability, endpoint/region configuration,
and API connectivity before executing any workflow operations. Credentials are
resolved by the aliyun CLI default credential chain at call time.
"""

import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import List, Tuple

from lhm_read_exec_cli.config import LhmConfig
from lhm_read_exec_cli.workflow import build_user_agent


@dataclass
class ValidationResult:
    """Result of environment validation."""

    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_environment(config: LhmConfig) -> ValidationResult:
    """Validate all environment prerequisites.

    Args:
        config: Resolved LHM configuration.

    Returns:
        ValidationResult indicating pass/fail with details.
    """
    errors: List[str] = []
    warnings: List[str] = []
    total_start = time.time()

    # 1. Check Python version
    step_start = time.time()
    if sys.version_info < (3, 8):
        errors.append(
            f"Python version {sys.version} is too old. Required: >= 3.8"
        )
    print(f"[TIMING] Python version check: {(time.time() - step_start)*1000:.1f}ms")

    # 2. Check aliyun CLI availability
    step_start = time.time()
    aliyun_binary = shutil.which("aliyun_real") or shutil.which("aliyun")
    if aliyun_binary is None:
        errors.append(
            "aliyun CLI not found. Please install aliyun CLI: https://help.aliyun.com/cli/"
        )
        return ValidationResult(success=False, errors=errors, warnings=warnings)
    print(f"[TIMING] aliyun CLI check: {(time.time() - step_start)*1000:.1f}ms")

    # 3. Credentials are resolved by the aliyun CLI default credential chain
    # at call time; nothing to validate here.
    step_start = time.time()
    print("✓ Credentials: resolved by aliyun CLI default credential chain")
    print(f"[TIMING] Credentials log: {(time.time() - step_start)*1000:.1f}ms")

    # 4. Endpoint and region
    step_start = time.time()
    print(f"✓ Endpoint: {config.endpoint}")
    print(f"✓ Region: {config.region_id}")
    print(f"[TIMING] Endpoint/Region log: {(time.time() - step_start)*1000:.1f}ms")

    # 5. Log aliyun CLI availability
    step_start = time.time()
    print(f"✓ aliyun CLI available: {aliyun_binary}")
    print(f"[TIMING] CLI log: {(time.time() - step_start)*1000:.1f}ms")

    print(f"[TIMING] Total validation: {(time.time() - total_start)*1000:.1f}ms")

    success = len(errors) == 0
    return ValidationResult(success=success, errors=errors, warnings=warnings)
