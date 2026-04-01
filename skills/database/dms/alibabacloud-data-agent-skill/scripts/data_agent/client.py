"""Data Agent client for API interactions.

Author: Tinker
Created: 2026-03-01
"""

from __future__ import annotations

import asyncio
import time
import functools
import json
import os
from typing import Optional, Any, Callable, TypeVar
import requests

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from Tea.exceptions import TeaException

from data_agent.config import DataAgentConfig
from data_agent.models import SessionInfo, SessionStatus, DataSource
from data_agent.api_adapter import APIAdapter
from data_agent.exceptions import (
    ApiError,
    AuthenticationError,
    SessionCreationError,
    ConfigurationError,
)


T = TypeVar("T")


def retry_on_error(max_retries: int = 3, retry_codes: tuple = ("Throttling", "ServiceUnavailable")):
    """Decorator to retry API calls on transient errors with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except ApiError as e:
                    last_exception = e
                    if e.code not in retry_codes or attempt == max_retries:
                        raise
                    wait_time = 2**attempt
                    time.sleep(wait_time)
            raise last_exception

        return wrapper

    return decorator


class DataAgentClient:
    """Synchronous client for Data Agent API.

    This client wraps the Alibaba Cloud DMS SDK and provides methods
    to interact with Data Agent sessions.
    """

    def __init__(self, config: DataAgentConfig):
        """Initialize the Data Agent client.

        Args:
            config: Configuration for the client.
        """
        self._config = config
        self._sdk_client: Optional[OpenApiClient] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the underlying SDK client based on authentication type."""
        # Determine authentication type
        if self._config.api_key:
            # API_KEY authentication - don't initialize the Tea SDK client
            self._sdk_client = None
            self._auth_type = "api_key"
        else:
            # Use Alibaba Cloud default credential chain
            # Supports: env vars, ~/.aliyun/config.json, ECS role, OIDC role, etc.
            from alibabacloud_credentials.client import Client as CredentialClient
            
            try:
                self._credential_client = CredentialClient()
                credential = self._credential_client.get_credential()
                
                sdk_config = open_api_models.Config()
                sdk_config.endpoint = self._config.endpoint
                sdk_config.user_agent = "AlibabaCloud-Agent-Skills"
                sdk_config.credential = self._credential_client
                    
                self._sdk_client = OpenApiClient(sdk_config)
                self._auth_type = "default_credential_chain"
            except Exception as e:
                raise AuthenticationError(
                    f"Failed to get credentials from default credential chain: {e}. "
                    "Please configure credentials via ~/.aliyun/config.json, "
                    "environment variables, or instance role."
                )

    def _call_api(
        self,
        action: str,
        version: str,
        params: dict,
        method: str = "POST",
        body: dict = None,
    ) -> dict:
        """Make a generic API call.

        Args:
            action: API action name.
            version: API version.
            params: Request parameters (for query string).
            method: HTTP method (default: POST).
            body: Request body (for JSON body).

        Returns:
            API response as dictionary.

        Raises:
            ApiError: If the API call fails.
            AuthenticationError: If authentication fails.
        """
        if self._auth_type == "api_key":
            # Handle API_KEY authentication using direct HTTP requests
            return self._call_api_with_api_key(action, version, params, method, body)
        else:
            # Handle traditional AK/SK authentication using Tea SDK
            return self._call_api_with_ak_sk(action, version, params, method, body)

    def _call_api_with_api_key(
        self,
        action: str,
        version: str,
        params: dict,
        method: str = "POST",
        body: dict = None,
    ) -> dict:
        """Make an API call using API_KEY authentication."""
        # Determine if this is a control plane or data plane API based on action
        control_plane_actions = [
            'ListDataAgentSession', 'CreateDataAgentSession', 'DescribeDataAgentSession',
            'DescribeFileUploadSignature', 'FileUploadCallback'
        ]

        data_plane_actions = [
            'SendChatMessage', 'GetChatContent', 'DescribeDataAgentUsage',
            'UpdateDataAgentSession', 'ListFileUpload', 'CreateDataAgentFeedback'
        ]

        # Choose the correct endpoint based on the action type
        if action in control_plane_actions:
            # Use control plane endpoint format - FIX: hyphen instead of dot
            base_endpoint = f"dataagent-{self._config.region}.aliyuncs.com/apikey"
        elif action in data_plane_actions:
            # Use data plane endpoint format - FIX: hyphen instead of dot
            base_endpoint = f"dataagent-stream-{self._config.region}.aliyuncs.com/apikey"
        else:
            # Default to control plane if action is not recognized - FIX: hyphen instead of dot
            base_endpoint = f"dataagent-{self._config.region}.aliyuncs.com/apikey"

        # Add the required RegionId parameter to params
        params['RegionId'] = self._config.region

        # Prepare request with PascalCase parameters
        prepared_params = APIAdapter.prepare_request_params(params, api_action=action)

        # For API_KEY authentication, we should put Action and Version in the body
        # according to standard OpenAPI practices
        if body is None:
            body = {}

        # Add action and version to the body instead of query params
        body.update({
            'Action': action,
            'Version': version
        })

        # Update body with prepared parameters
        body.update(prepared_params)

        prepared_body = APIAdapter.prepare_request_body(body)

        # Build the URL for the API call (without Action and Version in query)
        base_url = f"https://{base_endpoint}"

        # Construct the URL without action/version in query string since they're in body
        full_url = base_url

        # Set up headers with API_KEY
        headers = {
            'x-api-key': self._config.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'AlibabaCloud-Agent-Skills',
        }

        # Add debug logging if enabled via environment variable
        if os.getenv("DATA_AGENT_DEBUG_API", "").lower() in ('true', '1', 'yes'):
            import pprint
            auth_type_display = "API_KEY" if self._auth_type == "api_key" else "AK/SK"
            print(f"[DEBUG] API Call: {action}")
            print(f"[DEBUG] Authentication Type: {auth_type_display}")
            print(f"[DEBUG] Method: {method}")
            print(f"[DEBUG] URL: {full_url}")
            print(f"[DEBUG] Headers: {pprint.pformat(headers)}")
            if prepared_body:
                print(f"[DEBUG] Body: {pprint.pformat(prepared_body)}")

        try:
            # Make the API call - Action and Version are now in the body
            if method.upper() == "GET":
                # For GET requests, we might still need to put action/version in query
                query_params = {'Action': action, 'Version': version}
                import urllib.parse
                query_string = urllib.parse.urlencode(query_params)
                full_url_with_params = f"{full_url}?{query_string}"
                response = requests.get(full_url_with_params, headers=headers, timeout=self._config.timeout)
            elif method.upper() == "POST":
                # For POST requests, Action and Version are in the body
                response = requests.post(full_url, headers=headers, json=prepared_body, timeout=self._config.timeout)
            else:
                # For other methods, default to POST with body
                response = requests.request(method, full_url, headers=headers, json=prepared_body, timeout=self._config.timeout)

            # Check response status
            response.raise_for_status()

            # Parse response JSON
            response_data = response.json()

            # Process response to convert keys to camelCase
            processed_response = APIAdapter.process_response(response_data, api_action=action)

            # Add debug logging for response if enabled
            if os.getenv("DATA_AGENT_DEBUG_API", "").lower() in ('true', '1', 'yes'):
                import pprint
                print(f"[DEBUG] Response for {action}: {pprint.pformat(processed_response)}")

            return processed_response
        except requests.exceptions.RequestException as e:
            # Handle HTTP request errors
            error_msg = f"API call failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f", Status: {e.response.status_code}, Body: {e.response.text[:500]}"
            raise ApiError(error_msg, code="HTTPRequestError", request_id=None)

    def _call_api_with_ak_sk(
        self,
        action: str,
        version: str,
        params: dict,
        method: str = "POST",
        body: dict = None,
    ) -> dict:
        """Make an API call using AK/SK authentication."""
        # Prepare request with PascalCase parameters
        prepared_params = APIAdapter.prepare_request_params(params, api_action=action)
        prepared_body = APIAdapter.prepare_request_body(body) if body else None

        api_params = open_api_models.Params(
            action=action,
            version=version,
            protocol="HTTPS",
            method=method,
            auth_type="AK",
            style="RPC",
            pathname="/",
            req_body_type="json",
            body_type="json",
        )

        request = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(prepared_params),
            body=prepared_body,
        )

        runtime = util_models.RuntimeOptions(
            read_timeout=self._config.timeout * 1000,
            connect_timeout=30000,
        )

        # Add debug logging if enabled via environment variable
        if os.getenv("DATA_AGENT_DEBUG_API", "").lower() in ('true', '1', 'yes'):
            import pprint
            auth_type_display = "API_KEY" if self._auth_type == "api_key" else "AK/SK"
            print(f"[DEBUG] API Call: {action}")
            print(f"[DEBUG] Authentication Type: {auth_type_display}")
            print(f"[DEBUG] Method: {method}")
            print(f"[DEBUG] Params: {pprint.pformat(prepared_params)}")
            if prepared_body:
                print(f"[DEBUG] Body: {pprint.pformat(prepared_body)}")

        try:
            response = self._sdk_client.call_api(api_params, request, runtime)

            # Process response to convert keys to camelCase
            processed_response = APIAdapter.process_response(response.get("body", {}), api_action=action)

            # Add debug logging for response if enabled
            if os.getenv("DATA_AGENT_DEBUG_API", "").lower() in ('true', '1', 'yes'):
                import pprint
                print(f"[DEBUG] Response for {action}: {pprint.pformat(processed_response)}")

            return processed_response
        except TeaException as e:
            self._handle_tea_exception(e)

    def _handle_tea_exception(self, e: TeaException) -> None:
        """Convert TeaException to appropriate custom exception.

        Args:
            e: The TeaException to handle.

        Raises:
            AuthenticationError: For authentication-related errors.
            ApiError: For other API errors.
        """
        code = getattr(e, "code", "Unknown")
        message = getattr(e, "message", str(e))
        request_id = None
        if hasattr(e, "data") and isinstance(e.data, dict):
            request_id = e.data.get("RequestId")

        auth_error_codes = ("InvalidAccessKeyId.NotFound", "SignatureDoesNotMatch", "Forbidden")
        if code in auth_error_codes:
            raise AuthenticationError(message, code=code, request_id=request_id)

        raise ApiError(message, code=code, request_id=request_id)

    @retry_on_error(max_retries=3)
    def create_session(
        self,
        database_id: Optional[str] = None,
        title: str = "data-agent-session",
        mode: Optional[str] = None,
        enable_search: bool = False,
        file_id: Optional[str] = None,  # 添加文件ID参数
    ) -> SessionInfo:
        """Create a new Data Agent session.

        Args:
            database_id: Optional database ID to bind to the session.
            title: Session title (required by API).
            mode: Optional session mode, such as "ASK_DATA", "ANALYSIS", "INSIGHT".
            enable_search: Whether to enable search capability in the session.
            file_id: Optional file ID for file-based analysis session.

        Returns:
            SessionInfo with agent_id and session_id.

        Raises:
            SessionCreationError: If session creation fails.
        """
        params = {
            "Title": title,
            "DMSUnit": self._config.region,
        }
        if database_id:
            params["DatabaseId"] = database_id
        if mode:
            params["Mode"] = mode
        if file_id:
            # 当指定了文件ID时，会话将是基于文件的分析
            params["File"] = file_id

        # Ensure session configuration (language/mode/search) is persisted on server
        session_config = {"Language": "CHINESE", "EnableSearch": enable_search}
        if mode:
            session_config["Mode"] = mode

        # For API_KEY auth, SessionConfig should be a JSON object, not string
        # For AK/SK auth, SessionConfig should be a JSON string
        if self._auth_type == "api_key":
            params["SessionConfig"] = session_config
        else:
            params["SessionConfig"] = json.dumps(session_config)

        try:
            response = self._call_api(
                action="CreateDataAgentSession",
                version="2025-04-14",
                params=params,
            )

            # Response data is nested under 'Data' field
            # After API adapter processing, the keys are in camelCase
            data = response.get("data", response)  # Changed from "Data" to "data"
            agent_id = data.get("agentId", "")  # Changed from "AgentId" to "agentId"
            session_id = data.get("sessionId", "")  # Changed from "SessionId" to "sessionId"
            agent_status = data.get("agentStatus", "").upper()  # Changed from "AgentStatus" to "agentStatus"

            if not agent_id or not session_id:
                raise SessionCreationError(
                    f"Invalid response: missing AgentId or SessionId. Response: {response}"
                )

            # Map AgentStatus to SessionStatus.
            # AgentStatus reflects the underlying agent compute readiness:
            # when RUNNING, the session can accept messages even though
            # DescribeDataAgentSession may still report SessionStatus as
            # CREATING for a prolonged period.
            if agent_status == "RUNNING":
                status = SessionStatus.RUNNING
            elif agent_status == "STOPPED":
                status = SessionStatus.STOPPED
            elif agent_status == "FAILED":
                status = SessionStatus.FAILED
            else:
                status = SessionStatus.CREATING

            return SessionInfo(
                agent_id=agent_id,
                session_id=session_id,
                status=status,
                database_id=database_id,
            )
        except ApiError as e:
            raise SessionCreationError(f"Failed to create session: {e.message}", request_id=e.request_id)

    @retry_on_error(max_retries=3)
    def describe_session(self, session_id: str, agent_id: str = "") -> SessionInfo:
        """Get the status of a session.

        Args:
            session_id: The session ID.
            agent_id: The agent ID (optional, but used to construct the request properly).

        Returns:
            SessionInfo with current status.
        """
        params = {
            "SessionId": session_id,
            "DMSUnit": self._config.region,
        }
        # Only include AgentId in the request if it's provided
        # According to API spec, DescribeDataAgentSession doesn't require AgentId
        if agent_id:
            params["AgentId"] = agent_id

        response = self._call_api(
            action="DescribeDataAgentSession",
            version="2025-04-14",
            params=params,
        )

        request_id = response.get("requestId", "")  # Changed from "RequestId" to "requestId"
        data = response.get("data", response)  # Changed from "Data" to "data"
        status_str = data.get("sessionStatus", data.get("status", "CREATING"))  # Changed from "SessionStatus"/"Status" to "sessionStatus"/"status"
        try:
            status = SessionStatus(status_str)
        except ValueError:
            status = SessionStatus.CREATING

        # Capture the real AgentId from response if available
        # The agent_id in the response should take precedence over the one passed in
        real_agent_id = data.get("agentId") or data.get("AgentId") or agent_id  # Try both transformed and original

        return SessionInfo(
            agent_id=real_agent_id,
            session_id=session_id,
            status=status,
            database_id=data.get("databaseId"),  # Changed from "DatabaseId" to "databaseId"
            request_id=request_id,
        )

    @retry_on_error(max_retries=3)
    def send_message(
        self,
        agent_id: str,
        session_id: str,
        message: str,
        message_type: str = "primary",
        data_source: Optional[DataSource] = None,
        language: str = "CHINESE",
    ) -> dict:
        """Send a message to the Data Agent.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            message: The user's natural language query.
            message_type: Message type (default: "primary").
            data_source: Optional DataSource with database metadata.
            language: Response language (default: "CHINESE").

        Returns:
            Response from the API.
        """
        # Query parameters for RPC style API
        params = {
            "AgentId": agent_id,
            "SessionId": session_id,
            "Message": message,
            "MessageType": message_type,
            "DMSUnit": self._config.region,
        }

        # SessionConfig format depends on auth type
        # For API_KEY auth: JSON object
        # For AK/SK auth: JSON string
        session_config = {"Language": language}
        if self._auth_type == "api_key":
            params["SessionConfig"] = session_config
        else:
            params["SessionConfig"] = json.dumps(session_config)

        # DataSource format depends on auth type
        # For API_KEY auth: JSON object
        # For AK/SK auth: JSON string
        if data_source:
            if self._auth_type == "api_key":
                params["DataSource"] = data_source.to_api_dict()
            else:
                params["DataSource"] = json.dumps(data_source.to_api_dict())

        return self._call_api(
            action="SendChatMessage",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def get_chat_content(
        self,
        agent_id: str,
        session_id: str,
        checkpoint: Optional[str] = None,
    ) -> dict:
        """Get chat content from the Data Agent.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            checkpoint: Optional checkpoint for incremental fetching.

        Returns:
            Response containing content blocks.
        """
        params = {
            "AgentId": agent_id,
            "SessionId": session_id,
        }
        if checkpoint:
            params["Checkpoint"] = checkpoint

        return self._call_api(
            action="GetChatContent",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def get_file_upload_signature(
        self,
        filename: str,
        file_size: int,
    ) -> dict:
        """Get OSS upload signature for file upload.

        Args:
            filename: Name of the file to upload.
            file_size: Size of the file in bytes.

        Returns:
            Response containing upload URL and credentials.
        """
        params = {
            "FileName": filename,
            "FileSize": file_size,
        }

        return self._call_api(
            action="DescribeFileUploadSignature",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def file_upload_callback(self, file_id: str, filename: str, upload_location: str, file_size: int = None) -> dict:
        """Notify the service that file upload is complete.

        Args:
            file_id: The file ID from upload signature (uploadDir).
            filename: The original filename.
            upload_location: The full OSS path (UploadHost/UploadDir/Filename).
            file_size: The file size in bytes (required for API_KEY auth).

        Returns:
            Response confirming the upload.
        """
        params = {
            "Filename": filename,
            "UploadLocation": upload_location,
            "FileFrom": "Skill",
        }
        if file_size:
            params["FileSize"] = file_size

        return self._call_api(
            action="FileUploadCallback",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def list_files(self, session_id: str, file_category: Optional[str] = None) -> dict:
        """List files associated with a session.

        Args:
            session_id: The session ID.
            file_category: Optional filter, e.g. "WebReport" for agent-generated
                           reports, or None to list all files.

        Returns:
            Response containing file list.
        """
        params = {
            "SessionId": session_id,
        }
        if file_category:
            params["FileCategory"] = file_category

        return self._call_api(
            action="ListFileUpload",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def list_databases(
        self,
        search_key: Optional[str] = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> dict:
        """List databases registered in DMS Data Center.

        Args:
            search_key: Optional keyword to filter by database or instance name.
            page_number: Page number (1-based).
            page_size: Number of results per page.

        Returns:
            Raw API response containing Data.List with database metadata.
        """
        params: dict = {
            "PageNumber": page_number,
            "PageSize": page_size,
        }
        if search_key:
            params["SearchKey"] = search_key
        return self._call_api(
            action="ListDataCenterDatabase",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def list_tables(
        self,
        instance_name: str,
        database_name: str,
        page_number: int = 1,
        page_size: int = 200,
    ) -> dict:
        """List tables inside a DMS Data Center database.

        Args:
            instance_name: The InstanceName returned by list_databases.
            database_name: The DatabaseName returned by list_databases.
            page_number: Page number (1-based).
            page_size: Number of results per page.

        Returns:
            Raw API response containing Data.List with table metadata.
        """
        return self._call_api(
            action="ListDataCenterTable",
            version="2025-04-14",
            params={
                "InstanceName": instance_name,
                "DatabaseName": database_name,
                "PageNumber": page_number,
                "PageSize": page_size,
            },
        )

    @retry_on_error(max_retries=3)
    def delete_file(self, file_id: str) -> dict:
        """Delete an uploaded file.

        Args:
            file_id: The file ID to delete.

        Returns:
            Response confirming deletion.
        """
        params = {
            "FileId": file_id,
        }

        return self._call_api(
            action="DeleteFileUpload",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def add_data_center_table(
        self,
        instance_name: str,
        database_name: str,
        dms_instance_id: int,
        dms_db_id: int,
        table_name_list: list[str],
        db_type: str = "mysql",
        region_id: Optional[str] = None,
    ) -> dict:
        """Add DMS database tables to Data Agent Data Center.

        This method imports DMS database tables into Data Agent's Data Center
        using the AddDataCenterTable API.

        Args:
            instance_name: RDS instance name (e.g., "rm-xxxxx").
            database_name: Database name (e.g., "employees").
            dms_instance_id: DMS instance ID (e.g., 1234567).
            dms_db_id: DMS database ID (e.g., 12345678).
            table_name_list: List of table names to import (required).
            db_type: Database type (default: "mysql").
            region_id: Optional region ID (defaults to config.region).

        Returns:
            API response containing the import result.

        Raises:
            ApiError: If the API call fails.
        """
        region = region_id or self._config.region

        # Convert table_name_list to JSON string for RPC API
        import json
        table_list_json = json.dumps(table_name_list, ensure_ascii=False)

        params = {
            "DMSUnit": region,
            "RegionId": region,
            "ImportType": "DMS",
            "InstanceName": instance_name,
            "DmsInstanceId": dms_instance_id,
            "DbType": db_type,
            "DatabaseName": database_name,
            "DmsDbId": dms_db_id,
            "TableNameList": table_list_json,
        }

        return self._call_api(
            action="AddDataCenterTable",
            version="2025-04-14",
            params=params,
        )

    @retry_on_error(max_retries=3)
    def list_sessions(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page_number: int = 1,
        page_size: int = 10,
    ) -> dict:
        """List Data Agent sessions.

        For API_KEY authentication, uses startTime/endTime parameters.
        For AK/SK authentication, uses createStartTime/createEndTime parameters.

        Args:
            start_time: Start time for filtering sessions (ISO format).
            end_time: End time for filtering sessions (ISO format).
            page_number: Page number (1-based).
            page_size: Number of results per page.

        Returns:
            Response containing list of sessions.
        """
        params = {
            "PageNumber": page_number,
            "PageSize": page_size,
        }

        # Add time parameters based on authentication type
        if self._auth_type == "api_key":
            # For API_KEY auth, use the new parameter names
            if start_time:
                params["StartTime"] = start_time
            if end_time:
                params["EndTime"] = end_time
        else:
            # For AK/SK auth, use the original parameter names
            if start_time:
                params["CreateStartTime"] = start_time
            if end_time:
                params["CreateEndTime"] = end_time

        return self._call_api(
            action="ListDataAgentSession",
            version="2025-04-14",
            params=params,
        )

    @property
    def config(self) -> DataAgentConfig:
        """Get the client configuration."""
        return self._config


class AsyncDataAgentClient:
    """Asynchronous client for Data Agent API.

    This client provides async/await support for all API operations.
    """

    def __init__(self, config: DataAgentConfig):
        """Initialize the async Data Agent client.

        Args:
            config: Configuration for the client.
        """
        self._config = config
        self._sync_client = DataAgentClient(config)

    async def _run_in_executor(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Run a synchronous function in an executor.

        Args:
            func: The function to run.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            The result of the function.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(func, *args, **kwargs),
        )

    async def create_session(
        self,
        database_id: Optional[str] = None,
        title: str = "data-agent-session",
        mode: Optional[str] = None,
        enable_search: bool = False,
        file_id: Optional[str] = None,  # 添加文件ID参数
    ) -> SessionInfo:
        """Create a new Data Agent session asynchronously.

        Args:
            database_id: Optional database ID to bind to the session.
            title: Session title (required by API).
            mode: Optional session mode, such as "ASK_DATA", "ANALYSIS", "INSIGHT".
            enable_search: Whether to enable search capability in the session.
            file_id: Optional file ID for file-based analysis session.

        Returns:
            SessionInfo with agent_id and session_id.
        """
        return await self._run_in_executor(
            self._sync_client.create_session,
            database_id=database_id,
            title=title,
            mode=mode,
            enable_search=enable_search,
            file_id=file_id,
        )

    async def describe_session(self, session_id: str, agent_id: str = "") -> SessionInfo:
        """Get the status of a session asynchronously.

        Args:
            session_id: The session ID.
            agent_id: The agent ID (optional).

        Returns:
            SessionInfo with current status.
        """
        return await self._run_in_executor(
            self._sync_client.describe_session,
            session_id=session_id,
            agent_id=agent_id,
        )

    async def send_message(
        self,
        agent_id: str,
        session_id: str,
        message: str,
        message_type: str = "primary",
        data_source: Optional[DataSource] = None,
        language: str = "CHINESE",
    ) -> dict:
        """Send a message to the Data Agent asynchronously.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            message: The user's natural language query.
            message_type: Message type (default: "primary").
            data_source: Optional DataSource with database metadata.
            language: Response language (default: "CHINESE").

        Returns:
            Response from the API.
        """
        return await self._run_in_executor(
            self._sync_client.send_message,
            agent_id=agent_id,
            session_id=session_id,
            message=message,
            message_type=message_type,
            data_source=data_source,
            language=language,
        )

    async def get_chat_content(
        self,
        agent_id: str,
        session_id: str,
        checkpoint: Optional[str] = None,
    ) -> dict:
        """Get chat content from the Data Agent asynchronously.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            checkpoint: Optional checkpoint for incremental fetching.

        Returns:
            Response containing content blocks.
        """
        return await self._run_in_executor(
            self._sync_client.get_chat_content,
            agent_id=agent_id,
            session_id=session_id,
            checkpoint=checkpoint,
        )

    async def get_file_upload_signature(
        self,
        filename: str,
        file_size: int,
    ) -> dict:
        """Get OSS upload signature asynchronously.

        Args:
            filename: Name of the file to upload.
            file_size: Size of the file in bytes.

        Returns:
            Response containing upload URL and credentials.
        """
        return await self._run_in_executor(
            self._sync_client.get_file_upload_signature,
            filename=filename,
            file_size=file_size,
        )

    async def file_upload_callback(self, file_id: str, filename: str, upload_location: str, file_size: int = None) -> dict:
        """Notify file upload completion asynchronously.

        Args:
            file_id: The file ID from upload signature.
            filename: The original filename.
            upload_location: The full OSS path.
            file_size: The file size in bytes (required for API_KEY auth).

        Returns:
            Response confirming the upload.
        """
        return await self._run_in_executor(
            self._sync_client.file_upload_callback,
            file_id=file_id,
            filename=filename,
            upload_location=upload_location,
            file_size=file_size,
        )

    async def list_files(self, session_id: str, file_category: Optional[str] = None) -> dict:
        """List files asynchronously.

        Args:
            session_id: The session ID.
            file_category: Optional filter, e.g. "WebReport" for agent-generated reports.

        Returns:
            Response containing file list.
        """
        return await self._run_in_executor(
            self._sync_client.list_files,
            session_id=session_id,
            file_category=file_category,
        )

    async def delete_file(self, file_id: str) -> dict:
        """Delete a file asynchronously.

        Args:
            file_id: The file ID to delete.

        Returns:
            Response confirming deletion.
        """
        return await self._run_in_executor(
            self._sync_client.delete_file,
            file_id=file_id,
        )

    @property
    def config(self) -> DataAgentConfig:
        """Get the client configuration."""
        return self._config
