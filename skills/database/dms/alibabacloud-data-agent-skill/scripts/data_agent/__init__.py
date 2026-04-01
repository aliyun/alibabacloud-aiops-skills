"""
Alibaba Cloud Yaoichi Data Agent Python SDK

A Python SDK for interacting with Alibaba Cloud's Data Agent service,
enabling natural language data analysis across various data sources.

Author: Tinker
Created: 2026-03-01
"""

from data_agent.config import DataAgentConfig
from data_agent.client import DataAgentClient, AsyncDataAgentClient
from data_agent.session import SessionManager, AsyncSessionManager
from data_agent.message import MessageHandler, AsyncMessageHandler
from data_agent.file_manager import FileManager, AsyncFileManager
from data_agent.sse_client import SSEClient, AsyncSSEClient, SSEEvent
from data_agent.models import SessionInfo, ContentBlock, FileInfo, DataSource
from data_agent.mcp_tools import DmsMcpTools, AsyncDmsMcpTools, DmsInstance, AskDatabaseResult, PagedResult
from data_agent.api_adapter import APIAdapter
from data_agent.exceptions import (
    DataAgentException,
    ConfigurationError,
    AuthenticationError,
    SessionError,
    SessionTimeoutError,
    MessageError,
    ContentFetchError,
    FileUploadError,
    ApiError,
)

__version__ = "0.1.0"

__all__ = [
    # Config
    "DataAgentConfig",
    # Clients
    "DataAgentClient",
    "AsyncDataAgentClient",
    # SSE Clients
    "SSEClient",
    "AsyncSSEClient",
    "SSEEvent",
    # Session Management
    "SessionManager",
    "AsyncSessionManager",
    # Message Handling
    "MessageHandler",
    "AsyncMessageHandler",
    # File Management
    "FileManager",
    "AsyncFileManager",
    # MCP Tools
    "DmsMcpTools",
    "AsyncDmsMcpTools",
    "PagedResult",
    "DmsInstance",
    "AskDatabaseResult",
    # API Adapter
    "APIAdapter",
    # Models
    "SessionInfo",
    "ContentBlock",
    "FileInfo",
    "DataSource",
    # Exceptions
    "DataAgentException",
    "ConfigurationError",
    "AuthenticationError",
    "SessionError",
    "SessionTimeoutError",
    "MessageError",
    "ContentFetchError",
    "FileUploadError",
    "ApiError",
]
