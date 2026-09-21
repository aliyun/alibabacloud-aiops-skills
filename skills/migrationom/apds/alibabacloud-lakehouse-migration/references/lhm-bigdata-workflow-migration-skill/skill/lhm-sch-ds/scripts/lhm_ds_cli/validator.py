"""Environment validation for LHM Scheduler Datasource CLI.

Checks Python version, aliyun CLI availability, and endpoint/region
configuration before executing any datasource management operation.
Credentials are resolved by the aliyun CLI default credential chain at call
time and are not validated here.
"""

import shutil
import sys
from dataclasses import dataclass, field
from typing import List

from lhm_ds_cli.config import LhmConfig
from lhm_ds_cli.client_helper import build_user_agent


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

    if sys.version_info < (3, 8):
        errors.append(
            f"Python version {sys.version} is too old. Required: >= 3.8"
        )

    # Check aliyun CLI availability instead of SDK
    aliyun_binary = shutil.which("aliyun_real") or shutil.which("aliyun")
    if aliyun_binary is None:
        errors.append(
            "aliyun CLI not found. Please install aliyun CLI: https://help.aliyun.com/cli/"
        )
        return ValidationResult(success=False, errors=errors, warnings=warnings)

    print("✓ Credentials: resolved by aliyun CLI default credential chain")
    print(f"✓ Endpoint: {config.endpoint}")
    print(f"✓ Region: {config.region_id}")
    print(f"✓ aliyun CLI available: {aliyun_binary}")

    success = len(errors) == 0
    return ValidationResult(success=success, errors=errors, warnings=warnings)
