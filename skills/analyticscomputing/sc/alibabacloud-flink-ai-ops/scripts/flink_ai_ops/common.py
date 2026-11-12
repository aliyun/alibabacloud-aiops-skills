"""Shared validation, structured failures and detached output redaction."""

import argparse
import math

from .redaction import REDACTED, redact_sensitive


class OpsError(Exception):
    """Carry service errors and partial evidence through the CLI boundary."""

    def __init__(self, code, message, request_id="", data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.data = data


def validate_object(value, name, allowed, *, code="ValidationError"):
    """Reject non-object values and unsupported fields before serialization."""
    if not isinstance(value, dict):
        raise OpsError(code, f"{name} must be a JSON object.")
    unknown = set(value) - allowed
    if unknown:
        raise OpsError(code, f"{name} contains unsupported fields: {', '.join(sorted(map(str, unknown)))}.")


def validate_string(value, name, *, code="ValidationError"):
    """Require a nonempty string without changing the original value."""
    if not isinstance(value, str) or not value.strip():
        raise OpsError(code, f"{name} must be a non-empty string.")


def positive_number(value, name, *, code="ValidationError"):
    """Require finite, positive seconds or intervals, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise OpsError(code, f"{name} must be a finite positive number.")
    return value


def positive_seconds(value):
    """Parse finite, positive CLI durations with argparse-compatible errors."""
    try:
        return positive_number(float(value), "timeout/interval")
    except (ValueError, OpsError) as error:
        raise argparse.ArgumentTypeError("Must be a finite positive number.") from error


def add_body_arguments(parser):
    """Share official JSON body inputs and explicit confirmation flags."""
    body = parser.add_mutually_exclusive_group(required=True)
    body.add_argument("--body_json", help="Complete official JSON request body.")
    body.add_argument("--body_file", help="UTF-8 JSON request file.")
    parser.add_argument("--confirm", action="store_true", help="Confirm an already authorized operation; does not replace user authorization.")
