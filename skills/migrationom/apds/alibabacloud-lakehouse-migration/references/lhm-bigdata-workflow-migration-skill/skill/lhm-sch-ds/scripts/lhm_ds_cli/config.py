"""Configuration management for LHM Scheduler Datasource CLI.

Only endpoint / region are resolved here. Credentials are handled by the
aliyun CLI default credential chain at call time (environment variables /
RAM Role / ~/.alibabacloud/credentials) and are never parsed by this module.

Endpoint / region resolution order:
1. Session config written by lhm-sch-env (authoritative, already merged)
2. Environment variables
3. User config file

See the `credentials` module for the full search chain.
"""

import os
from dataclasses import dataclass
from typing import Optional

from lhm_ds_cli import credentials as credential_file

DEFAULT_ENDPOINT = "lhm-pre.cn-hangzhou.aliyuncs.com"
DEFAULT_REGION_ID = "cn-hangzhou"


@dataclass(frozen=True)
class LhmConfig:
    """Immutable configuration for LHM Scheduler API client.

    Only endpoint / region are carried here. Credentials are resolved by the
    aliyun CLI default credential chain at call time and are never parsed by
    this module.
    """

    endpoint: str
    region_id: str

    @classmethod
    def from_environment(
        cls,
        endpoint_override: Optional[str] = None,
        region_override: Optional[str] = None,
    ) -> "LhmConfig":
        """Resolve endpoint / region from session file, environment, then user file.

        Endpoint / region priority: CLI override > session config >
        environment variable > user file > built-in default. The session config
        comes first because lhm-sch-env has already merged the user's
        configuration with the environment; letting a stale shell variable
        override it would silently contradict what the user just configured.

        Credentials are NOT resolved here — the aliyun CLI default credential
        chain (environment variables / RAM Role / ~/.alibabacloud/credentials)
        handles them at call time.

        Args:
            endpoint_override: If provided, takes precedence over everything else.
            region_override: If provided, takes precedence over everything else.

        Returns:
            LhmConfig instance with resolved endpoint / region.
        """
        session_config = credential_file.load_session_file()
        file_config = session_config or credential_file.load_credential_file()

        file_endpoint = file_config.value("lhm", "endpoint") if file_config else ""
        file_region = file_config.value("lhm", "region_id") if file_config else ""

        # 会话配置是权威结果，其 endpoint/region 也应压过环境变量
        if session_config is not None:
            endpoint = (
                endpoint_override
                or file_endpoint
                or os.environ.get("LHM_ENDPOINT", "").strip()
                or DEFAULT_ENDPOINT
            )
            region_id = (
                region_override
                or file_region
                or os.environ.get("REGION_ID", "").strip()
                or DEFAULT_REGION_ID
            )
        else:
            endpoint = (
                endpoint_override
                or os.environ.get("LHM_ENDPOINT", "").strip()
                or file_endpoint
                or DEFAULT_ENDPOINT
            )
            region_id = (
                region_override
                or os.environ.get("REGION_ID", "").strip()
                or file_region
                or DEFAULT_REGION_ID
            )

        return cls(endpoint=endpoint, region_id=region_id)
