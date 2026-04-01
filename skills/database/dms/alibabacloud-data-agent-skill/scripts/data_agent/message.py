"""Message handling for Data Agent.

Author: Tinker
Created: 2026-03-01
"""

from __future__ import annotations

import time
from typing import Optional, Iterator, AsyncIterator, List

from data_agent.client import DataAgentClient, AsyncDataAgentClient
from data_agent.sse_client import SSEClient, AsyncSSEClient, SSEEvent
from data_agent.models import SessionInfo, ContentBlock, ContentType, AnalysisResult, DataSource
from data_agent.exceptions import MessageSendError, ContentFetchError


class MessageHandler:
    """Handles message sending and response retrieval for Data Agent.

    Uses SSE streaming to receive responses from Data Agent.
    """

    def __init__(self, client: DataAgentClient):
        """Initialize message handler.

        Args:
            client: DataAgentClient instance for API calls.
        """
        self._client = client
        self._sse_client = SSEClient(client.config)

    def send_query(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> str:
        """Send a query and wait for complete response.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Returns:
            Complete response text from Data Agent.

        Raises:
            MessageSendError: If message sending fails.
            ContentFetchError: If content retrieval fails or times out.
        """
        timeout = timeout or self._client.config.timeout

        # Send the message
        try:
            self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        # Update session usage
        session.update_last_used()

        # Get response via SSE streaming
        try:
            response = self._sse_client.get_full_response(
                agent_id=session.agent_id,
                session_id=session.session_id,
                timeout=timeout,
            )
            return response
        except Exception as e:
            raise ContentFetchError(f"Failed to get response: {e}")

    def send_query_with_result(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> AnalysisResult:
        """Send a query and get detailed result with content blocks.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Returns:
            AnalysisResult with response text and content blocks.
        """
        timeout = timeout or self._client.config.timeout
        start_time = time.time()

        # Send the message
        try:
            self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        session.update_last_used()

        # Collect response via SSE
        content_blocks = []
        response_parts = []

        try:
            for event in self._sse_client.stream_chat_content(
                agent_id=session.agent_id,
                session_id=session.session_id,
                timeout=timeout,
            ):
                block = self._event_to_content_block(event)
                if block:
                    content_blocks.append(block)
                    if block.content_type == ContentType.TEXT:
                        response_parts.append(block.content)

                if event.event_type == "SSE_FINISH":
                    break

        except Exception as e:
            raise ContentFetchError(f"Failed to get response: {e}")

        duration_ms = int((time.time() - start_time) * 1000)
        response_text = "".join(response_parts)

        return AnalysisResult(
            query=query,
            response=response_text,
            content_blocks=content_blocks,
            session_id=session.session_id,
            duration_ms=duration_ms,
        )

    def stream_content(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> Iterator[ContentBlock]:
        """Send query and stream response content blocks.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Yields:
            ContentBlock objects as they become available.
        """
        timeout = timeout or self._client.config.timeout

        # Send the message
        try:
            self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        session.update_last_used()

        # Stream content blocks
        for event in self._sse_client.stream_chat_content(
            agent_id=session.agent_id,
            session_id=session.session_id,
            timeout=timeout,
        ):
            block = self._event_to_content_block(event)
            if block:
                yield block

            if event.event_type == "SSE_FINISH":
                break

    def stream_events(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> Iterator[SSEEvent]:
        """Send query and stream raw SSE events.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Yields:
            SSEEvent objects as they arrive.
        """
        timeout = timeout or self._client.config.timeout

        # Send the message
        try:
            self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        session.update_last_used()

        # Stream raw events
        yield from self._sse_client.stream_chat_content(
            agent_id=session.agent_id,
            session_id=session.session_id,
            timeout=timeout,
        )

    def _event_to_content_block(self, event: SSEEvent) -> Optional[ContentBlock]:
        """Convert SSE event to ContentBlock.

        Args:
            event: SSE event to convert.

        Returns:
            ContentBlock or None if not applicable.
        """
        # Only process delta events with content
        if event.event_type == "delta" and event.category == "llm":
            if event.content:
                return ContentBlock(
                    content_type=ContentType.TEXT,
                    content=event.content,
                    checkpoint=str(event.checkpoint) if event.checkpoint else None,
                    is_final=False,
                )

        # Process data events (complete content)
        if event.event_type == "data" and event.category == "think":
            if event.content:
                return ContentBlock(
                    content_type=ContentType.TEXT,
                    content=event.content,
                    checkpoint=str(event.checkpoint) if event.checkpoint else None,
                    is_final=True,
                )

        return None


class AsyncMessageHandler:
    """Asynchronous message handler for Data Agent.

    Uses async SSE streaming for responses.
    """

    def __init__(self, client: AsyncDataAgentClient):
        """Initialize async message handler.

        Args:
            client: AsyncDataAgentClient instance for API calls.
        """
        self._client = client
        self._sse_client = AsyncSSEClient(client.config)

    async def send_query(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> str:
        """Send a query and wait for complete response asynchronously.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Returns:
            Complete response text from Data Agent.
        """
        timeout = timeout or self._client.config.timeout

        # Send the message
        try:
            await self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        session.update_last_used()

        # Get response via SSE streaming
        try:
            response = await self._sse_client.get_full_response(
                agent_id=session.agent_id,
                session_id=session.session_id,
                timeout=timeout,
            )
            return response
        except Exception as e:
            raise ContentFetchError(f"Failed to get response: {e}")

    async def send_query_with_result(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> AnalysisResult:
        """Send a query and get detailed result asynchronously.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Returns:
            AnalysisResult with response text and content blocks.
        """
        timeout = timeout or self._client.config.timeout
        start_time = time.time()

        try:
            await self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        session.update_last_used()

        content_blocks = []
        response_parts = []

        try:
            async for event in self._sse_client.stream_chat_content(
                agent_id=session.agent_id,
                session_id=session.session_id,
                timeout=timeout,
            ):
                block = self._event_to_content_block(event)
                if block:
                    content_blocks.append(block)
                    if block.content_type == ContentType.TEXT:
                        response_parts.append(block.content)

                if event.event_type == "SSE_FINISH":
                    break

        except Exception as e:
            raise ContentFetchError(f"Failed to get response: {e}")

        duration_ms = int((time.time() - start_time) * 1000)
        response_text = "".join(response_parts)

        return AnalysisResult(
            query=query,
            response=response_text,
            content_blocks=content_blocks,
            session_id=session.session_id,
            duration_ms=duration_ms,
        )

    async def stream_content(
        self,
        session: SessionInfo,
        query: str,
        timeout: Optional[int] = None,
        data_source: Optional[DataSource] = None,
    ) -> AsyncIterator[ContentBlock]:
        """Send query and stream response content blocks asynchronously.

        Args:
            session: Active session to use.
            query: Natural language query.
            timeout: Optional timeout in seconds.
            data_source: Optional DataSource with database metadata.

        Yields:
            ContentBlock objects as they become available.
        """
        timeout = timeout or self._client.config.timeout

        try:
            await self._client.send_message(
                agent_id=session.agent_id,
                session_id=session.session_id,
                message=query,
                data_source=data_source,
            )
        except Exception as e:
            raise MessageSendError(f"Failed to send message: {e}")

        session.update_last_used()

        async for event in self._sse_client.stream_chat_content(
            agent_id=session.agent_id,
            session_id=session.session_id,
            timeout=timeout,
        ):
            block = self._event_to_content_block(event)
            if block:
                yield block

            if event.event_type == "SSE_FINISH":
                break

    def _event_to_content_block(self, event: SSEEvent) -> Optional[ContentBlock]:
        """Convert SSE event to ContentBlock."""
        if event.event_type == "delta" and event.category == "llm":
            if event.content:
                return ContentBlock(
                    content_type=ContentType.TEXT,
                    content=event.content,
                    checkpoint=str(event.checkpoint) if event.checkpoint else None,
                    is_final=False,
                )

        if event.event_type == "data" and event.category == "think":
            if event.content:
                return ContentBlock(
                    content_type=ContentType.TEXT,
                    content=event.content,
                    checkpoint=str(event.checkpoint) if event.checkpoint else None,
                    is_final=True,
                )

        return None
