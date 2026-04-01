"""Custom exceptions for Data Agent SDK.

Author: Tinker
Created: 2026-03-01
"""

from typing import Optional


class DataAgentException(Exception):
    """Base exception for all Data Agent errors."""

    def __init__(self, message: str, request_id: Optional[str] = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)

    def __str__(self) -> str:
        if self.request_id:
            return f"{self.message} (RequestId: {self.request_id})"
        return self.message


class ConfigurationError(DataAgentException):
    """Raised when configuration is invalid or missing."""

    pass


class AuthenticationError(DataAgentException):
    """Raised when authentication fails (invalid AccessKey, signature mismatch)."""

    def __init__(self, message: str, code: Optional[str] = None, request_id: Optional[str] = None):
        self.code = code
        super().__init__(message, request_id)


class SessionError(DataAgentException):
    """Base exception for session-related errors."""

    pass


class SessionCreationError(SessionError):
    """Raised when session creation fails."""

    pass


class SessionTimeoutError(SessionError):
    """Raised when session fails to reach RUNNING state within timeout."""

    def __init__(self, message: str, session_id: Optional[str] = None, waited_seconds: int = 0):
        self.session_id = session_id
        self.waited_seconds = waited_seconds
        super().__init__(message)


class SessionNotFoundError(SessionError):
    """Raised when session does not exist."""

    pass


class MessageError(DataAgentException):
    """Base exception for message-related errors."""

    pass


class MessageSendError(MessageError):
    """Raised when message sending fails."""

    pass


class ContentFetchError(MessageError):
    """Raised when content fetching fails or times out."""

    def __init__(self, message: str, partial_content: Optional[str] = None, request_id: Optional[str] = None):
        self.partial_content = partial_content
        super().__init__(message, request_id)


class FileError(DataAgentException):
    """Base exception for file-related errors."""

    pass


class FileUploadError(FileError):
    """Raised when file upload fails."""

    def __init__(self, message: str, file_path: Optional[str] = None, request_id: Optional[str] = None):
        self.file_path = file_path
        super().__init__(message, request_id)


class FileDownloadError(FileError):
    """Raised when file download fails."""

    pass


class ApiError(DataAgentException):
    """Raised for general API errors with error code."""

    def __init__(
        self,
        message: str,
        code: str,
        request_id: Optional[str] = None,
        http_status: Optional[int] = None,
    ):
        self.code = code
        self.http_status = http_status
        super().__init__(message, request_id)

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.http_status:
            parts.append(f"(HTTP {self.http_status})")
        if self.request_id:
            parts.append(f"(RequestId: {self.request_id})")
        return " ".join(parts)
