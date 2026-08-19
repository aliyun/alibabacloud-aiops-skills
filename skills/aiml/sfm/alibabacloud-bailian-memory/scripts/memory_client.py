#!/usr/bin/env python3
"""
Unified DashScope Memory Library API client.

Provides the MemoryClient class that wraps the 16 Memory Library REST endpoints
used by this skill, with authentication, User-Agent injection, automatic retry
with exponential backoff, and unified error handling.

All writes go through POST /add-async: the request is accepted immediately and
extraction runs in the background, returning an event_id.

Management APIs are also wrapped: memory project create/list/get/update and
profile schema create/list/update, plus single profile value item operations.

API Key retrieval is fully automated via scripts/api_key.py — the agent
does not need to manually set, export, or pass API key values.

Environment variables:
    SKILL_SESSION_ID          - Optional. Session ID injected into the User-Agent header.
    BAILIAN_MEMORY_BASE_URL   - Optional. Overrides the API base URL (defaults to the production gateway).
"""

import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package is required. Install via: pip3 install -r scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)


SKILL_NAME = "alibabacloud-bailian-memory"
# Production gateway by default; override via BAILIAN_MEMORY_BASE_URL when another
# environment (e.g. the pre-release gateway) is required for testing.
# Note: the API key must belong to the same environment as the endpoint.
BASE_URL = os.environ.get("BAILIAN_MEMORY_BASE_URL",
                          "https://dashscope.aliyuncs.com/api/v2/apps/memory")

# HTTP status codes eligible for automatic retry
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1  # seconds


class MemoryApiError(Exception):
    """Raised when a DashScope Memory API call returns a non-success response."""

    def __init__(self, status_code, error_code, message, request_id=None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.request_id = request_id
        super().__init__(f"[{status_code}] {error_code}: {message} (request_id={request_id})")


class MemoryClient:
    """Client for the DashScope Memory Library REST API.

    Usage::

        client = MemoryClient()
        result = client.add_memory_messages(user_id="user_123", messages=[...])
    """

    def __init__(self):
        from api_key import get_api_key
        self._api_key = get_api_key()
        session_id = os.environ.get("SKILL_SESSION_ID", "")
        ua = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}"
        if session_id:
            ua = f"{ua}/{session_id}"
        self._user_agent = ua
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        })

    # ------------------------------------------------------------------
    # Internal request helper with retry
    # ------------------------------------------------------------------

    def _request(self, method, path, params=None, json_body=None):
        """Send an HTTP request with automatic retry on transient errors.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            path: API path appended to BASE_URL.
            params: Query parameters (dict).
            json_body: JSON request body (dict).

        Returns:
            Parsed JSON response as a dict.

        Raises:
            MemoryApiError: On non-retryable error responses.
        """
        url = f"{BASE_URL}{path}"
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                resp = self._session.request(
                    method, url, params=params, json=json_body, timeout=30
                )
            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_BASE * (2 ** attempt))
                    continue
                raise RuntimeError(f"Network error after {_MAX_RETRIES} retries: {exc}") from exc

            if resp.status_code == 200:
                return resp.json()

            # Parse error body
            try:
                body = resp.json()
            except ValueError:
                body = {}
            error_code = body.get("code", body.get("Code", "UnknownError"))
            message = body.get("message", body.get("Message", resp.text))
            request_id = body.get("request_id", body.get("RequestId", ""))

            if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE * (2 ** attempt))
                continue

            raise MemoryApiError(resp.status_code, error_code, message, request_id)

        # Should not reach here, but just in case
        raise RuntimeError(f"Request failed after {_MAX_RETRIES} retries: {last_error}")

    # ------------------------------------------------------------------
    # Memory Fragment Operations
    # ------------------------------------------------------------------

    def add_memory_messages(self, user_id, messages, timestamp=None,
                            memory_library_id=None, project_id=None,
                            project_ids=None, profile_schema=None, meta_data=None):
        """Asynchronously extract memories from conversation messages.

        Sends REST POST /add-async in messages mode. Accepted immediately and
        returns an event_id while LLM extraction runs in the background. Default
        usage is fire-and-forget; poll :meth:`get_event` only when the caller
        needs confirmation.
        To store a known text as-is, use :meth:`add_memory_content` instead.

        Args:
            user_id: Memory entity ID (max 64 chars).
            messages: List of conversation message dicts with 'role' and 'content'
                (required). Roles 'user'/'assistant'/'tool' are supported;
                'tool_calls' and 'tool_call_id' follow the standard OpenAI format.
            timestamp: Optional message Unix timestamp in seconds.
            memory_library_id: Optional memory library ID.
            project_id: Optional memory project ID. Mutually exclusive with ``project_ids``.
            project_ids: Optional list of memory project IDs for extracting into
                multiple projects at once.
            profile_schema: Optional profile schema ID; pass it to also extract
                user profile attributes from the conversation (separate event resource).
            meta_data: Optional custom key-value metadata.

        Returns:
            dict with 'request_id', 'event_id' and 'events' list (one record per
            resource, each with 'status' PENDING/SUCCEEDED/FAILED).
        """
        if not messages:
            raise ValueError("'messages' is required.")
        if project_ids and project_id:
            raise ValueError("'project_id' and 'project_ids' are mutually exclusive.")
        body = {"user_id": user_id, "messages": messages}
        if timestamp is not None:
            body["timestamp"] = timestamp
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        if project_id:
            body["project_id"] = project_id
        if project_ids:
            body["project_ids"] = project_ids
        if profile_schema:
            body["profile_schema"] = profile_schema
        if meta_data:
            body["meta_data"] = meta_data
        return self._request("POST", "/add-async", json_body=body)

    def add_memory_content(self, user_id, custom_content, timestamp=None,
                           memory_library_id=None, project_id=None,
                           meta_data=None):
        """Asynchronously save a custom content string as memory (no LLM extraction).

        Sends REST POST /add-async in custom_content mode. Custom content binds
        to exactly one project, so ``project_ids`` is not supported; profile
        extraction depends on conversation messages, so ``profile_schema`` is not
        supported either.

        Args:
            user_id: Memory entity ID (max 64 chars).
            custom_content: The memory content saved as-is (required, max 512 chars).
            timestamp: Optional message Unix timestamp in seconds.
            memory_library_id: Optional memory library ID.
            project_id: Optional memory project ID (single project only).
            meta_data: Optional custom key-value metadata.

        Returns:
            dict with 'request_id', 'event_id' and 'events' list; the event
            'resource_type' carries a 'custom_' prefix (custom_observation).
        """
        if not custom_content:
            raise ValueError("'custom_content' is required.")
        body = {"user_id": user_id, "custom_content": custom_content}
        if timestamp is not None:
            body["timestamp"] = timestamp
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        if project_id:
            body["project_id"] = project_id
        if meta_data:
            body["meta_data"] = meta_data
        return self._request("POST", "/add-async", json_body=body)

    def get_event(self, event_id):
        """Query the status of an asynchronous memory operation.

        Sends REST GET /events/{event_id}. Usually NOT needed — writes are
        fire-and-forget; query only when the user asks for confirmation or a
        later step depends on extraction completion.

        Args:
            event_id: The event ID returned by :meth:`add_memory_messages` or
                :meth:`add_memory_content`.

        Returns:
            dict with 'request_id' and 'events' list (one record per resource,
            each with 'event_type', 'resource_id', 'resource_type', 'status'
            PENDING/SUCCEEDED/FAILED, 'created_at', 'updated_at'; FAILED records
            additionally carry 'detail' formatted as 'errorCode: errorMessage';
            after SUCCEEDED each record carries a 'result' array describing the
            applied changes: 'content', 'event' ADD/UPDATE/DELETE,
            'memory_node_id' for observation memories, and 'old_content'
            for updates).
        """
        return self._request("GET", f"/events/{event_id}")

    def search_memory(self, user_id, messages, memory_library_id=None,
                      project_id=None, top_k=None):
        """Semantically search across memory fragments.

        Sends REST POST /memory_nodes/search. Tuning and billing parameters
        (min_score, plan_version, enable_rerank) are server-controlled and
        intentionally not exposed; the server applies its defaults
        (plan_version=pro, min_score=0.3).

        Args:
            user_id: Memory entity ID.
            messages: Conversation messages for the search query.
            memory_library_id: Optional memory library ID.
            project_id: Optional memory project ID (defaults to the default project).
            top_k: Max results (1-100, default 10).

        Returns:
            dict with 'request_id', 'plan_version' and 'memory_nodes' list (each
            node contains 'memory_node_id', 'content', 'memory_type', 'score',
            'status', 'timestamp', 'created_at', 'updated_at', 'project_id').
        """
        body = {"user_id": user_id, "messages": messages}
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        if project_id:
            body["project_id"] = project_id
        if top_k is not None:
            body["top_k"] = top_k
        return self._request("POST", "/memory_nodes/search", json_body=body)

    def list_memories(self, user_id, memory_library_id=None, project_id=None,
                      page_num=None, page_size=None):
        """List memory fragments with pagination.

        Sends REST GET /memory_nodes.

        Args:
            user_id: Memory entity ID.
            memory_library_id: Optional memory library ID.
            project_id: Optional memory project ID (defaults to the default project).
            page_num: Page number (starts at 1).
            page_size: Items per page.

        Returns:
            dict with 'request_id', 'memory_nodes' (each node contains
            'memory_node_id', 'content', 'memory_type', 'status', 'project_id',
            timestamps), 'total', 'page_size', 'page_num'.
        """
        params = {"user_id": user_id}
        if memory_library_id:
            params["memory_library_id"] = memory_library_id
        if project_id:
            params["project_id"] = project_id
        if page_num is not None:
            params["page_num"] = page_num
        if page_size is not None:
            params["page_size"] = page_size
        return self._request("GET", "/memory_nodes", params=params)

    def get_memory_node(self, memory_node_id):
        """Get the detail of a single memory fragment.

        Sends REST GET /memory_nodes/{id}.

        Args:
            memory_node_id: ID of the memory fragment.

        Returns:
            dict with 'request_id' and 'memory_node' (contains 'memory_node_id',
            'content', 'memory_type', 'status', 'project_id', 'meta_data',
            timestamps).
        """
        return self._request("GET", f"/memory_nodes/{memory_node_id}")

    def update_memory(self, memory_node_id, custom_content, user_id,
                      memory_library_id=None, timestamp=None, meta_data=None):
        """Update an existing memory fragment (overwrites its content).

        Sends REST PATCH /memory_nodes/{id}.
        The node's library and project ownership cannot be changed.

        Args:
            memory_node_id: ID of the memory to update.
            custom_content: New content (max 512 chars).
            user_id: Memory entity ID.
            memory_library_id: Optional memory library ID used for ownership check.
            timestamp: Optional Unix timestamp (seconds).
            meta_data: Optional metadata merged incrementally: keys not specified
                remain unchanged.

        Returns:
            dict with 'request_id'.
        """
        body = {"custom_content": custom_content, "user_id": user_id}
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        if timestamp is not None:
            body["timestamp"] = timestamp
        if meta_data:
            body["meta_data"] = meta_data
        return self._request("PATCH", f"/memory_nodes/{memory_node_id}", json_body=body)

    def delete_memory(self, memory_node_id, memory_library_id=None):
        """Delete a memory fragment. This operation is irreversible.

        Sends REST DELETE /memory_nodes/{id}. Destructive: display the target
        content and obtain user confirmation before calling.

        Args:
            memory_node_id: ID of the memory to delete.
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id'.
        """
        params = {}
        if memory_library_id:
            params["memory_library_id"] = memory_library_id
        return self._request("DELETE", f"/memory_nodes/{memory_node_id}", params=params or None)

    # ------------------------------------------------------------------
    # User Profile
    # ------------------------------------------------------------------

    def get_user_profile(self, profile_schema_id, user_id, memory_library_id=None,
                         need_detail=None):
        """Get extracted user profile based on a profile schema.

        Sends REST GET /profile_schemas/{id}/user_profile.

        Args:
            profile_schema_id: Profile schema ID.
            user_id: Memory entity ID.
            memory_library_id: Optional memory library ID.
            need_detail: Optional. When True, each attribute carries an expanded
                'value_items' list (each with 'item_id', 'value', 'status')
                instead of a joined 'value' string. The item_id is required for
                :meth:`update_user_profile_value` with op_type update/delete.

        Returns:
            dict with 'request_id' and 'profile' (contains 'schema_name',
            'schema_description' and 'attributes'; each attribute has 'id',
            'name' and either a joined 'value' string or 'value_items').
        """
        params = {"user_id": user_id}
        if memory_library_id:
            params["memory_library_id"] = memory_library_id
        if need_detail is not None:
            params["need_detail"] = "true" if need_detail else "false"
        return self._request("GET", f"/profile_schemas/{profile_schema_id}/user_profile", params=params)

    def update_user_profile_value(self, profile_schema_id, entity_id, attribute_id,
                                  op_type, item_id=None, value=None,
                                  memory_library_id=None):
        """Operate on a single user profile attribute value item.

        Sends REST PATCH /profile_schemas/{id}/profile_values.

        Operation semantics (op_type is case-insensitive; invalid values are
        rejected):
        - 'add': appends ``value`` as a new value item; ``item_id`` not needed.
        - 'update': modifies an existing value item; ``item_id`` required.
        - 'delete': removes an existing value item; ``item_id`` required.

        ``item_id`` values come from :meth:`get_user_profile` with
        ``need_detail=True``.

        Args:
            profile_schema_id: Profile schema ID.
            entity_id: Profile owner entity ID; for user profiles pass the user ID.
            attribute_id: Attribute ID; must exist in the target schema.
            op_type: One of 'add' / 'update' / 'delete'.
            item_id: Value item ID; required when op_type is update/delete.
            value: Attribute value content; used when op_type is add/update.
            memory_library_id: Optional memory library ID used for ownership check.

        Returns:
            dict with 'request_id'.
        """
        if not op_type:
            raise ValueError("'op_type' is required.")
        op = str(op_type).strip().lower()
        if op not in ("add", "update", "delete"):
            raise ValueError("'op_type' must be one of: add, update, delete.")
        if op in ("update", "delete") and item_id is None:
            raise ValueError(f"'item_id' is required when op_type is {op}.")
        body = {
            "entity_id": entity_id,
            "attribute_id": attribute_id,
            "op_type": op,
        }
        if item_id is not None:
            body["item_id"] = item_id
        if value is not None:
            body["value"] = value
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        return self._request("PATCH", f"/profile_schemas/{profile_schema_id}/profile_values", json_body=body)

    # ------------------------------------------------------------------
    # Memory Project Management
    # ------------------------------------------------------------------

    def create_memory_project(self, name, plan_version=None, instruction_type=None,
                              custom_instruction=None, expired_in_days=None,
                              auto_refresh=None, memory_library_id=None):
        """Create a memory project.

        Sends REST POST /memory_projects.

        Args:
            name: Project name (required, max 32 chars).
            plan_version: Billing plan 'pro' (default) or 'lite', case-insensitive.
            instruction_type: 'default' or 'custom'.
            custom_instruction: Custom extraction instruction content.
            expired_in_days: Memory expiration in days (1-180, or -1 for never).
            auto_refresh: Whether accessing a memory refreshes its expiration.
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id' and 'project_id'.
        """
        if not name:
            raise ValueError("'name' is required.")
        body = {"name": name}
        if plan_version:
            body["plan_version"] = plan_version
        if instruction_type:
            body["instruction_type"] = instruction_type
        if custom_instruction is not None:
            body["custom_instruction"] = custom_instruction
        if expired_in_days is not None:
            body["expired_in_days"] = expired_in_days
        if auto_refresh is not None:
            body["auto_refresh"] = auto_refresh
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        return self._request("POST", "/memory_projects", json_body=body)

    def list_memory_projects(self, page_num=None, page_size=None,
                             memory_library_id=None):
        """List memory projects with pagination.

        Sends REST GET /memory_projects.

        Args:
            page_num: Page number (starts at 1).
            page_size: Items per page.
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id', 'memory_projects' (each with 'project_id',
            'name', 'plan_version',
            instruction and expiration settings, timestamps), 'page_num',
            'page_size', 'total'.
        """
        params = {}
        if page_num is not None:
            params["page_num"] = page_num
        if page_size is not None:
            params["page_size"] = page_size
        if memory_library_id:
            params["memory_library_id"] = memory_library_id
        return self._request("GET", "/memory_projects", params=params or None)

    def get_memory_project(self, project_id, memory_library_id=None):
        """Get the detail of a memory project.

        Sends REST GET /memory_projects/{id}.

        Args:
            project_id: ID of the memory project.
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id', 'project_id', 'name',
            'plan_version', instruction and expiration
            settings, timestamps.
        """
        params = {}
        if memory_library_id:
            params["memory_library_id"] = memory_library_id
        return self._request("GET", f"/memory_projects/{project_id}", params=params or None)

    def update_memory_project(self, project_id, name=None, instruction_type=None,
                              custom_instruction=None, expired_in_days=None,
                              auto_refresh=None,
                              plan_version=None, memory_library_id=None):
        """Update a memory project. Fields not passed remain unchanged.

        Sends REST PATCH /memory_projects/{id}. At least one updatable field
        must be provided.

        Args:
            project_id: ID of the memory project to update.
            name: New project name (max 32 chars).
            instruction_type: 'default' or 'custom'.
            custom_instruction: Custom extraction instruction content.
            expired_in_days: Memory expiration in days (1-180, or -1 for never).
            auto_refresh: Whether accessing a memory refreshes its expiration.
            plan_version: Billing plan 'pro' or 'lite', case-insensitive.
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id'.
        """
        body = {}
        if name is not None:
            body["name"] = name
        if instruction_type is not None:
            body["instruction_type"] = instruction_type
        if custom_instruction is not None:
            body["custom_instruction"] = custom_instruction
        if expired_in_days is not None:
            body["expired_in_days"] = expired_in_days
        if auto_refresh is not None:
            body["auto_refresh"] = auto_refresh
        if plan_version is not None:
            body["plan_version"] = plan_version
        if not body:
            raise ValueError("At least one updatable field must be provided.")
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        return self._request("PATCH", f"/memory_projects/{project_id}", json_body=body)

    # ------------------------------------------------------------------
    # Profile Schema Management
    # ------------------------------------------------------------------

    def create_profile_schema(self, name, attributes, description=None,
                              plan_version=None, memory_library_id=None):
        """Create a user profile schema.

        Sends REST POST /profile_schemas.

        Args:
            name: Schema name (required, max 32 chars).
            attributes: Non-empty list of attribute dicts, each with required
                'name' and optional 'description', 'immutable' (default False)
                and 'default_value'. When immutable=True, default_value is
                required and the value is never changed by extraction.
            description: Optional schema description.
            plan_version: Billing plan 'pro' (default) or 'lite', case-insensitive.
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id' and 'profile_schema_id'.
        """
        if not name:
            raise ValueError("'name' is required.")
        if not attributes:
            raise ValueError("'attributes' must be a non-empty list.")
        for i, attr in enumerate(attributes):
            if not isinstance(attr, dict) or not attr.get("name"):
                raise ValueError(f"attributes[{i}] requires a non-empty 'name'.")
            if attr.get("immutable") and not attr.get("default_value"):
                raise ValueError(f"attributes[{i}].default_value is required when immutable=true.")
        body = {"name": name, "attributes": attributes}
        if description is not None:
            body["description"] = description
        if plan_version:
            body["plan_version"] = plan_version
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        return self._request("POST", "/profile_schemas", json_body=body)

    def list_profile_schemas(self, page_num=None, page_size=None, memory_library_id=None):
        """List user profile schemas with pagination.

        Sends REST GET /profile_schemas.

        Args:
            page_num: Page number (starts at 1, default 1).
            page_size: Items per page (default 10).
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id', 'profile_schemas' (each with
            'profile_schema_id', 'name', 'description', 'plan_version'), 'total'.
        """
        params = {}
        if page_num is not None:
            params["page_num"] = page_num
        if page_size is not None:
            params["page_size"] = page_size
        if memory_library_id:
            params["memory_library_id"] = memory_library_id
        return self._request("GET", "/profile_schemas", params=params or None)

    def update_profile_schema(self, profile_schema_id, name=None, description=None,
                              plan_version=None, attributes_operations=None,
                              memory_library_id=None):
        """Update a user profile schema. Fields not passed remain unchanged.

        Sends REST PATCH /profile_schemas/{id}. At least one updatable field
        must be provided.

        attributes_operations semantics (each element requires 'op'):
        - op='add': requires 'name'; 'description', 'immutable' and
          'default_value' optional (default_value required when immutable=True).
        - op='update': requires 'attribute_id' and at least one of
          'name'/'description'/'default_value'; 'immutable' cannot be updated.
        - op='delete': requires 'attribute_id'.

        Args:
            profile_schema_id: ID of the profile schema to update.
            name: New schema name (max 32 chars).
            description: New schema description.
            plan_version: Billing plan 'pro' or 'lite', case-insensitive.
            attributes_operations: List of attribute change operation dicts
                (passed through as-is).
            memory_library_id: Optional memory library ID.

        Returns:
            dict with 'request_id'.
        """
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if plan_version is not None:
            body["plan_version"] = plan_version
        if attributes_operations:
            body["attributes_operations"] = attributes_operations
        if not body:
            raise ValueError("At least one updatable field must be provided.")
        if memory_library_id:
            body["memory_library_id"] = memory_library_id
        return self._request("PATCH", f"/profile_schemas/{profile_schema_id}", json_body=body)

