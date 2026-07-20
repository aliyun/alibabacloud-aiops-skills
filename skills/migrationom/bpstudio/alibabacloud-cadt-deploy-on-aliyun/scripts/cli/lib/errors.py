"""Error code dictionary and CadtError exception family.

13 error codes mirror SPEC §7. Agents branch on `code` (not message).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Error codes (mirrors ops/_common/error_codes.json)
# ---------------------------------------------------------------------------
OP_NOT_FOUND = "OP_NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
MISSING_FIELD = "MISSING_FIELD"
FORBIDDEN_FIELD = "FORBIDDEN_FIELD"
PRECONDITION_FAILED = "PRECONDITION_FAILED"
PRE_HOOK_REJECTED = "PRE_HOOK_REJECTED"
IDENTITY_NOT_FOUND = "IDENTITY_NOT_FOUND"
API_ERROR = "API_ERROR"
BUSINESS_FAILURE = "BUSINESS_FAILURE"
TIMEOUT = "TIMEOUT"
OUTPUT_SCHEMA_DRIFT = "OUTPUT_SCHEMA_DRIFT"
POSTVERIFY_FAILED = "POSTVERIFY_FAILED"
CADT_INTERNAL = "CADT_INTERNAL"


# ---------------------------------------------------------------------------
# Exceptions — runner uses these; cadt-deploy-on-aliyun.main() converts them to envelopes.
# ---------------------------------------------------------------------------
class CadtError(Exception):
    """Base exception. Carries everything needed to build a failure envelope."""

    code: str = CADT_INTERNAL

    def __init__(
        self,
        message: str,
        *,
        fix_hint: str = "",
        fields: Optional[List[Dict[str, Any]]] = None,
        docs_ref: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.fix_hint = fix_hint
        self.fields = fields
        self.docs_ref = docs_ref


class OpNotFound(CadtError):
    code = OP_NOT_FOUND


class ValidationFailed(CadtError):
    code = VALIDATION_FAILED


class MissingField(CadtError):
    code = MISSING_FIELD


class ForbiddenField(CadtError):
    code = FORBIDDEN_FIELD


class PreconditionFailed(CadtError):
    code = PRECONDITION_FAILED


class HookReject(CadtError):
    """Raised by user-level hooks. Code is overridable per hook."""

    def __init__(self, code: str, message: str, fix_hint: str = "") -> None:
        super().__init__(message, fix_hint=fix_hint)
        self.code = code


class IdentityNotFound(CadtError):
    code = IDENTITY_NOT_FOUND


class ApiError(CadtError):
    code = API_ERROR


class BusinessFailure(CadtError):
    code = BUSINESS_FAILURE

    def __init__(
        self,
        message: str,
        *,
        fix_hint: str = "",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message, fix_hint=fix_hint)
        self.details = details


class CadtTimeout(CadtError):
    code = TIMEOUT

    def __init__(
        self, message: str, *, invocation_id: str = "", fix_hint: str = ""
    ) -> None:
        super().__init__(message, fix_hint=fix_hint)
        self.invocation_id = invocation_id


class OutputSchemaDrift(CadtError):
    code = OUTPUT_SCHEMA_DRIFT


class PostVerifyFailed(CadtError):
    code = POSTVERIFY_FAILED
