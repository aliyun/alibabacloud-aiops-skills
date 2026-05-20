"""Custom exceptions for sr_connect."""


class SRConnectError(Exception):
    """Base error for sr_connect."""


class ConfigNotFoundError(SRConnectError):
    """Profile config file not found."""


class ConnectionError(SRConnectError):
    """Failed to connect to StarRocks."""
