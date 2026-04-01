"""Configuration management for Data Agent SDK.

Author: Tinker
Created: 2026-03-01
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

from data_agent.exceptions import ConfigurationError


@dataclass
class DataAgentConfig:
    """Configuration for Data Agent client.

    Attributes:
        api_key: API Key for alternative authentication (optional)
        region: Region for DMS endpoint (default: cn-hangzhou)
        endpoint: Custom endpoint (auto-generated if not set)
        timeout: API timeout in seconds (default: 300)
        max_retry: Maximum retry attempts (default: 3)
        poll_interval: Interval between polls in seconds (default: 2)
        max_poll_count: Maximum poll attempts (default: 60)
    
    Note:
        For AK/SK authentication, the SDK uses Alibaba Cloud default credential chain
        (environment variables, ~/.aliyun/config.json, instance role, etc.)
        Do NOT pass AK/SK explicitly to this config.
    """

    api_key: Optional[str] = None
    region: str = "cn-hangzhou"
    endpoint: Optional[str] = None
    timeout: int = 300
    max_retry: int = 3
    poll_interval: int = 2
    max_poll_count: int = 60

    def __post_init__(self) -> None:
        """Generate endpoint if not provided and validate config."""
        if not self.endpoint:
            if self.api_key:
                # For API key auth, use the dataagent domain format with /apikey suffix
                self.endpoint = f"dataagent-{self.region}.aliyuncs.com/apikey"
            else:
                # Standard DMS endpoint for AK/SK auth (uses default credential chain)
                self.endpoint = f"dms.{self.region}.aliyuncs.com"
        self.validate()

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If required configuration is missing or invalid.
        """
        # API key is optional - if not provided, SDK will use default credential chain
        pass

        if self.timeout <= 0:
            raise ConfigurationError(f"Invalid timeout value: {self.timeout}. Must be positive.")
        if self.max_retry < 0:
            raise ConfigurationError(f"Invalid max_retry value: {self.max_retry}. Must be non-negative.")
        if self.poll_interval <= 0:
            raise ConfigurationError(f"Invalid poll_interval value: {self.poll_interval}. Must be positive.")
        if self.max_poll_count <= 0:
            raise ConfigurationError(f"Invalid max_poll_count value: {self.max_poll_count}. Must be positive.")

    @classmethod
    def from_env(cls, dotenv_path: Optional[str] = None) -> DataAgentConfig:
        """Create configuration from environment variables.

        Args:
            dotenv_path: Optional path to .env file to load.

        Returns:
            DataAgentConfig instance.

        Note:
            AK/SK credentials are NOT read from environment variables here.
            The Alibaba Cloud SDK uses its default credential chain.
        """
        if dotenv_path:
            load_dotenv(dotenv_path)
        else:
            load_dotenv()

        return cls(
            api_key=os.environ.get("DATA_AGENT_API_KEY") or None,
            region=os.environ.get("DATA_AGENT_REGION", "cn-hangzhou"),
            endpoint=os.environ.get("DATA_AGENT_ENDPOINT"),
            timeout=int(os.environ.get("DATA_AGENT_TIMEOUT", "300")),
            max_retry=int(os.environ.get("DATA_AGENT_MAX_RETRY", "3")),
            poll_interval=int(os.environ.get("DATA_AGENT_POLL_INTERVAL", "2")),
            max_poll_count=int(os.environ.get("DATA_AGENT_MAX_POLL_COUNT", "60")),
        )

    @classmethod
    def from_dict(cls, config_dict: dict) -> DataAgentConfig:
        """Create configuration from a dictionary.

        Args:
            config_dict: Dictionary containing configuration values.

        Returns:
            DataAgentConfig instance.
        
        Note:
            Do NOT pass AK/SK credentials in config_dict.
            Use Alibaba Cloud default credential chain instead.
        """
        return cls(
            api_key=config_dict.get("api_key"),
            region=config_dict.get("region", "cn-hangzhou"),
            endpoint=config_dict.get("endpoint"),
            timeout=config_dict.get("timeout", 300),
            max_retry=config_dict.get("max_retry", 3),
            poll_interval=config_dict.get("poll_interval", 2),
            max_poll_count=config_dict.get("max_poll_count", 60),
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary (excluding secrets).

        Returns:
            Dictionary with non-sensitive configuration values.
        """
        result = {
            "region": self.region,
            "endpoint": self.endpoint,
            "timeout": self.timeout,
            "max_retry": self.max_retry,
            "poll_interval": self.poll_interval,
            "max_poll_count": self.max_poll_count,
        }
        # Only indicate auth type
        if self.api_key:
            result["auth_type"] = "api_key"
        else:
            result["auth_type"] = "default_credential_chain"
        return result

    def __repr__(self) -> str:
        """String representation (hides secrets)."""
        return (
            f"DataAgentConfig(region='{self.region}', endpoint='{self.endpoint}', "
            f"timeout={self.timeout}, max_retry={self.max_retry})"
        )
