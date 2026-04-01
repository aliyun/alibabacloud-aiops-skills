"""Data models for Data Agent SDK.

Author: Tinker
Created: 2026-03-01
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
from .api_adapter import APIAdapter


class SessionStatus(str, Enum):
    """Session status enumeration."""

    CREATING = "CREATING"
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    WAIT_INPUT = "WAIT_INPUT"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class ContentType(str, Enum):
    """Content block type enumeration."""

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"
    CODE = "code"


@dataclass
class SessionInfo:
    """Information about a Data Agent session."""

    agent_id: str
    session_id: str
    status: SessionStatus = SessionStatus.CREATING
    database_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    request_id: Optional[str] = None

    def is_running(self) -> bool:
        """Check if session is in an active/usable state (RUNNING, IDLE or WAIT_INPUT)."""
        return self.status in (SessionStatus.RUNNING, SessionStatus.IDLE, SessionStatus.WAIT_INPUT)

    def update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used_at = datetime.now()


@dataclass
class ContentBlock:
    """A block of content from Data Agent response."""

    content_type: ContentType
    content: str
    checkpoint: Optional[str] = None
    sequence_id: Optional[int] = None
    is_final: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class FileInfo:
    """Information about an uploaded or generated file."""

    file_id: str
    filename: str
    file_type: str
    size: int
    upload_url: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class DatabaseSource:
    """Database source configuration for analysis.

    This is the legacy model. Use DataSource for SendChatMessage API.
    """

    database_id: str
    database_type: str  # PolarDB, RDS, AnalyticDB, MaxCompute, etc.
    instance_id: Optional[str] = None
    schema_name: Optional[str] = None
    description: Optional[str] = None


@dataclass
class DataSource:
    """Data source configuration for SendChatMessage API.

    Contains complete database metadata required by Data Agent.

    Attributes:
        dms_instance_id: DMS instance ID (e.g., 1234567)
        dms_database_id: DMS database ID (e.g., 12345678)
        instance_name: RDS instance name (e.g., "rm-xxxxxx")
        db_name: Database name (e.g., "chinook")
        tables: List of table names to include
        table_ids: List of table IDs from ListDataCenterTable
        engine: Database engine type (e.g., "mysql")
        region_id: Region ID (e.g., "cn-hangzhou")
        data_source_type: Data source type, default "database"
        file_id: File ID for file-based analysis (when data_source_type="FILE")
    """

    dms_instance_id: Optional[int] = None
    dms_database_id: Optional[int] = None
    instance_name: str = ""
    db_name: str = ""
    tables: list[str] = field(default_factory=list)
    table_ids: list[str] = field(default_factory=list)
    engine: str = "mysql"
    region_id: str = "cn-hangzhou"
    data_source_type: str = "database"
    file_id: str = ""

    def to_api_dict(self) -> dict:
        """Convert to API request format."""
        result = {
            "DataSourceType": self.data_source_type,
        }

        if self.data_source_type == "FILE":
            # File-based analysis uses remote_data_center type with FileId
            # Extract filename from file_id path for Database field
            file_name = self.file_id.split("/")[-1] if "/" in self.file_id else self.file_id
            result.update({
                "DataSourceType": "remote_data_center",
                "FileId": self.file_id,
                "Database": file_name,
                "Tables": [file_name.replace(".csv", "").replace(".xlsx", "").replace(".xls", "")],
                "RegionId": self.region_id,
            })
        else:
            # Database analysis needs full connection info
            result.update({
                "DmsInstanceId": str(self.dms_instance_id) if self.dms_instance_id else "",
                "DmsDatabaseId": str(self.dms_database_id) if self.dms_database_id else "",
                "FileId": self.instance_name,
                "DbName": self.db_name,
                "Database": self.db_name,
                "Tables": self.tables,
                "TableIds": self.table_ids,
                "Engine": self.engine,
                "RegionId": self.region_id,
            })

        # Apply API parameter formatting with PascalCase
        return APIAdapter.prepare_request_params(result)


@dataclass
class ChatMessage:
    """A chat message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of a data analysis query."""

    query: str
    response: str
    content_blocks: list[ContentBlock] = field(default_factory=list)
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    generated_files: list[FileInfo] = field(default_factory=list)
