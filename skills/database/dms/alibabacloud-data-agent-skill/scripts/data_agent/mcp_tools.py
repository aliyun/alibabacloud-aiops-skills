"""MCP (Model Context Protocol) tools integration for DMS.

This module provides integration with Alibaba Cloud DMS MCP Server tools:
- listInstances: Search for database instances in DMS
- askDatabase: Natural language query database (NL2SQL + execute SQL)

Author: Tinker
Created: 2026-03-05
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from alibabacloud_dms_enterprise20181101 import models as dms_models
from alibabacloud_dms_enterprise20181101.client import Client as DmsClient
from alibabacloud_tea_openapi import models as open_api_models

from data_agent.config import DataAgentConfig
from data_agent.exceptions import ApiError


@dataclass
class DmsInstance:
    """DMS Instance information."""
    instance_id: str
    instance_alias: str
    instance_type: str
    host: str
    port: int
    state: str
    env_type: str
    instance_source: str
    instance_resource_id: Optional[str] = None


@dataclass
class AskDatabaseResult:
    """Result from askDatabase query."""
    sql: str
    result: str
    explanation: Optional[str] = None


@dataclass
class DmsDatabase:
    """DMS Database information."""
    database_id: str
    schema_name: str
    host: str
    port: int
    instance_id: str
    instance_alias: str
    db_type: str
    env_type: str


@dataclass
class DmsTable:
    """DMS Table information."""
    table_id: str
    table_name: str
    table_guid: str
    database_id: str
    schema_name: str
    engine: Optional[str] = None
    table_comment: Optional[str] = None


@dataclass
class PagedResult:
    """Paginated result with metadata."""
    items: List[Any]
    page_number: int
    page_size: int
    total_count: int
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page_number < self.total_pages


class DmsMcpTools:
    """MCP tools for DMS integration.
    
    Provides access to DMS MCP Server functionality:
    - listInstances: Search and list database instances
    - askDatabase: Natural language to SQL query execution
    """

    def __init__(self, config: DataAgentConfig):
        """Initialize DMS MCP tools.
        
        Args:
            config: Data Agent configuration containing credentials.
        """
        self._config = config
        self._dms_client: Optional[DmsClient] = None
        self._init_dms_client()

    def _init_dms_client(self) -> None:
        """Initialize DMS Enterprise client using default credential chain."""
        from alibabacloud_credentials.client import Client as CredentialClient
        
        credential_client = CredentialClient()
        
        sdk_config = open_api_models.Config()
        sdk_config.credential = credential_client
        
        # Use DMS Enterprise endpoint
        region = self._config.region
        sdk_config.endpoint = f"dms-enterprise.{region}.aliyuncs.com"
        sdk_config.user_agent = "AlibabaCloud-Agent-Skills"
        
        self._dms_client = DmsClient(sdk_config)

    def list_instances(
        self,
        search_key: Optional[str] = None,
        db_type: Optional[str] = None,
        env_type: Optional[str] = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> PagedResult:
        """Search for database instances in DMS.
        
        Args:
            search_key: Optional search key (e.g., instance host, alias).
            db_type: Optional database type (e.g., mysql, polardb, oracle).
            env_type: Optional environment type (e.g., product, dev, test).
            page_number: Page number (default: 1).
            page_size: Page size (default: 50, max: 100).
            
        Returns:
            PagedResult with list of DmsInstance objects and pagination info.
            
        Raises:
            ApiError: If the API call fails.
        """
        try:
            page_size = min(page_size, 100)  # Max 100
            
            req = dms_models.ListInstancesRequest()
            req.page_number = page_number
            req.page_size = page_size
            if search_key:
                req.search_key = search_key
            if db_type:
                req.db_type = db_type
            if env_type:
                req.env_type = env_type
            
            resp = self._dms_client.list_instances(req)
            instance_data = resp.body.to_map()
            
            total_count = instance_data.get("TotalCount", 0)
            result = []
            
            if "InstanceList" in instance_data:
                instance_list = instance_data["InstanceList"]
                if "Instance" in instance_list:
                    instances = instance_list["Instance"]
                    if isinstance(instances, list):
                        for item in instances:
                            # Skip DELETED instances
                            state = item.get("State", "")
                            if state == "DELETED":
                                continue
                            
                            # Handle EcsInstanceId -> InstanceResourceId mapping
                            resource_id = item.get("EcsInstanceId") or item.get("InstanceResourceId")
                            
                            instance = DmsInstance(
                                instance_id=str(item.get("InstanceId", "")),
                                instance_alias=item.get("InstanceAlias", ""),
                                instance_type=item.get("InstanceType", ""),
                                host=item.get("Host", ""),
                                port=int(item.get("Port", 0)) if item.get("Port") else 0,
                                state=state,
                                env_type=item.get("EnvType", ""),
                                instance_source=item.get("InstanceSource", ""),
                                instance_resource_id=resource_id,
                            )
                            result.append(instance)
            
            return PagedResult(
                items=result,
                page_number=page_number,
                page_size=page_size,
                total_count=total_count,
            )
            
        except Exception as e:
            raise ApiError(f"Failed to list instances: {e}", code="ListInstancesError")

    def ask_database(
        self,
        question: str,
        database_id: str,
    ) -> AskDatabaseResult:
        """Natural language query database (NL2SQL + execute SQL).
        
        Note: This is a placeholder implementation. The actual askDatabase
        functionality requires the Data Agent Analytics API which handles
        NL2SQL conversion and SQL execution.
        
        Args:
            question: Natural language question to query the database.
            database_id: DMS database ID to query.
            
        Returns:
            AskDatabaseResult containing the generated SQL and query result.
            
        Raises:
            ApiError: If the query fails.
        """
        # This functionality is provided by the Data Agent Analytics API
        # which is already implemented in DataAgentClient
        # This method serves as a wrapper for MCP tool compatibility
        raise NotImplementedError(
            "askDatabase is implemented via DataAgentClient. "
            "Use DataAgentClient with ASK_DATA mode for NL2SQL queries."
        )

    def search_database(
        self,
        search_key: str,
        page_number: int = 1,
        page_size: int = 200,
    ) -> List[DmsDatabase]:
        """Search databases by schema name in DMS.
        
        Args:
            search_key: Schema name search keyword (required).
            page_number: Page number for pagination (default: 1).
            page_size: Page size for pagination (default: 200, max: 1000).
            
        Returns:
            List of DmsDatabase objects.
            
        Raises:
            ApiError: If the API call fails.
        """
        try:
            req = dms_models.SearchDatabaseRequest()
            req.search_key = search_key
            req.page_number = page_number
            req.page_size = min(page_size, 1000)  # Max 1000
            
            resp = self._dms_client.search_database(req)
            data = resp.body.to_map()
            
            # API returns 'SearchDatabaseList' not 'DatabaseList'
            db_list_key = "SearchDatabaseList" if "SearchDatabaseList" in data else "DatabaseList"
            
            if db_list_key not in data:
                return []
            
            db_list = data[db_list_key]
            
            # Handle different response structures
            # API returns {'SearchDatabase': [...]} instead of {'Database': [...]}
            if isinstance(db_list, list):
                databases = db_list
            elif isinstance(db_list, dict):
                if "SearchDatabase" in db_list:
                    databases = db_list["SearchDatabase"]
                elif "Database" in db_list:
                    databases = db_list["Database"]
                else:
                    return []
            else:
                return []
            if not isinstance(databases, list) or not databases:
                return []
            
            result = []
            for item in databases:
                # SearchDatabase API returns different fields than expected
                # Use Alias as instance_alias if InstanceAlias not present
                instance_alias = item.get("InstanceAlias", "") or item.get("Alias", "")
                # SearchDatabase doesn't return InstanceId, use empty string
                instance_id = str(item.get("InstanceId", ""))
                
                db = DmsDatabase(
                    database_id=str(item.get("DatabaseId", "")),
                    schema_name=item.get("SchemaName", ""),
                    host=item.get("Host", ""),
                    port=int(item.get("Port", 0)) if item.get("Port") else 0,
                    instance_id=instance_id,
                    instance_alias=instance_alias,
                    db_type=item.get("DbType", ""),
                    env_type=item.get("EnvType", ""),
                )
                result.append(db)
            
            return result
            
        except Exception as e:
            raise ApiError(f"Failed to search database: {e}", code="SearchDatabaseError")

    def list_tables(
        self,
        database_id: str,
        search_name: Optional[str] = None,
        page_number: int = 1,
        page_size: int = 200,
    ) -> List[DmsTable]:
        """List tables in a database.
        
        Args:
            database_id: Database ID to search tables in (required).
            search_name: Table name search keyword (optional).
            page_number: Page number for pagination (default: 1).
            page_size: Page size for pagination (default: 200, max: 200).
            
        Returns:
            List of DmsTable objects.
            
        Raises:
            ApiError: If the API call fails.
        """
        try:
            req = dms_models.ListTablesRequest()
            req.database_id = database_id
            if search_name:
                req.search_name = search_name
            req.page_number = page_number
            req.page_size = min(page_size, 200)  # Max 200
            
            resp = self._dms_client.list_tables(req)
            data = resp.body.to_map()
            
            if "TableList" not in data:
                return []
            
            table_list = data["TableList"]
            if "Table" not in table_list:
                return []
            
            tables = table_list["Table"]
            if not isinstance(tables, list) or not tables:
                return []
            
            result = []
            for item in tables:
                table = DmsTable(
                    table_id=str(item.get("TableId", "")),
                    table_name=item.get("TableName", ""),
                    table_guid=item.get("TableGuid", ""),
                    database_id=str(item.get("DatabaseId", "")),
                    schema_name=item.get("SchemaName", ""),
                    engine=item.get("Engine"),
                    table_comment=item.get("TableComment"),
                )
                result.append(table)
            
            return result
            
        except Exception as e:
            raise ApiError(f"Failed to list tables: {e}", code="ListTablesError")


class AsyncDmsMcpTools:
    """Async version of DMS MCP tools."""

    def __init__(self, config: DataAgentConfig):
        """Initialize async DMS MCP tools.
        
        Args:
            config: Data Agent configuration.
        """
        self._config = config
        self._dms_client: Optional[DmsClient] = None

    async def _init_dms_client(self) -> None:
        """Initialize async DMS Enterprise client using default credential chain."""
        from alibabacloud_credentials.client import Client as CredentialClient
        
        credential_client = CredentialClient()
        
        sdk_config = open_api_models.Config()
        sdk_config.credential = credential_client
        
        region = self._config.region
        sdk_config.endpoint = f"dms-enterprise.{region}.aliyuncs.com"
        sdk_config.user_agent = "AlibabaCloud-Agent-Skills"
        
        self._dms_client = DmsClient(sdk_config)

    async def list_instances(
        self,
        search_key: Optional[str] = None,
        db_type: Optional[str] = None,
        env_type: Optional[str] = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> PagedResult:
        """Async search for database instances in DMS.
        
        Args:
            search_key: Optional search key.
            db_type: Optional database type.
            env_type: Optional environment type.
            page_number: Page number (default: 1).
            page_size: Page size (default: 50, max: 100).
            
        Returns:
            PagedResult with list of DmsInstance objects and pagination info.
        """
        if not self._dms_client:
            await self._init_dms_client()
        
        try:
            page_size = min(page_size, 100)  # Max 100
            
            req = dms_models.ListInstancesRequest()
            req.page_number = page_number
            req.page_size = page_size
            if search_key:
                req.search_key = search_key
            if db_type:
                req.db_type = db_type
            if env_type:
                req.env_type = env_type
            
            resp = await self._dms_client.list_instances_async(req)
            instance_data = resp.body.to_map()
            
            total_count = instance_data.get("TotalCount", 0)
            result = []
            
            if "InstanceList" in instance_data:
                instance_list = instance_data["InstanceList"]
                if "Instance" in instance_list:
                    instances = instance_list["Instance"]
                    if isinstance(instances, list):
                        for item in instances:
                            # Skip DELETED instances
                            state = item.get("State", "")
                            if state == "DELETED":
                                continue
                            
                            resource_id = item.get("EcsInstanceId") or item.get("InstanceResourceId")
                            
                            instance = DmsInstance(
                                instance_id=str(item.get("InstanceId", "")),
                                instance_alias=item.get("InstanceAlias", ""),
                                instance_type=item.get("InstanceType", ""),
                                host=item.get("Host", ""),
                                port=int(item.get("Port", 0)) if item.get("Port") else 0,
                                state=state,
                                env_type=item.get("EnvType", ""),
                                instance_source=item.get("InstanceSource", ""),
                                instance_resource_id=resource_id,
                            )
                            result.append(instance)
            
            return PagedResult(
                items=result,
                page_number=page_number,
                page_size=page_size,
                total_count=total_count,
            )
            
        except Exception as e:
            raise ApiError(f"Failed to list instances: {e}", code="ListInstancesError")
