"""Session management for Data Agent.

Author: Tinker
Created: 2026-03-01
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

from data_agent.client import DataAgentClient, AsyncDataAgentClient
from data_agent.models import SessionInfo, SessionStatus
from data_agent.exceptions import SessionTimeoutError, SessionNotFoundError


class SessionManager:
    """Manages Data Agent session lifecycle.

    Handles session creation, status polling, and session reuse
    for multi-turn conversations.
    """

    def __init__(self, client: DataAgentClient):
        """Initialize session manager.

        Args:
            client: DataAgentClient instance for API calls.
        """
        self._client = client
        self._active_sessions: Dict[str, SessionInfo] = {}

    def create_or_reuse(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        database_id: Optional[str] = None,
        wait_for_running: bool = True,
        mode: Optional[str] = "ASK_DATA",
        enable_search: bool = False,
        file_id: Optional[str] = None,
    ) -> SessionInfo:
        """Create a new session or reuse an existing one.

        Args:
            session_id: Optional existing session ID to reuse.
            agent_id: Optional agent ID (used when reusing a session to avoid
                      an extra describe call with an empty agent_id).
            database_id: Optional database ID to bind to new session.
            wait_for_running: Whether to wait for session to be RUNNING.
            mode: Session mode to use when creating a new session.
                  One of "ASK_DATA" (default), "ANALYSIS", "INSIGHT".
            enable_search: Whether to enable search capability in the session.
            file_id: Optional file ID for file-based analysis session.

        Returns:
            SessionInfo for the active session.

        Raises:
            SessionTimeoutError: If session doesn't reach RUNNING state.
            SessionNotFoundError: If specified session_id is invalid.
        """
        # Try to reuse existing session
        if session_id:
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                if self.is_session_active(session_id):
                    session.update_last_used()
                    return session

            # Validate session with API
            try:
                session = self._client.describe_session(
                    session_id=session_id,
                    agent_id=agent_id or "",
                )

                # If the session is still in CREATING state, wait for it to become ready
                if session.status == SessionStatus.CREATING and wait_for_running:
                    session = self.wait_until_running(
                        session_id=session.session_id,
                        agent_id=session.agent_id,
                        max_wait=600,  # Increase max_wait to 10 minutes (600 seconds) since backend can be slow
                    )

                if session.is_running() or not wait_for_running:
                    self._active_sessions[session_id] = session
                    return session
                else:
                    raise SessionNotFoundError(
                        f"Session {session_id} exists but is not in RUNNING state (status: {session.status.value})"
                    )
            except SessionNotFoundError:
                raise
            except Exception as e:
                raise SessionNotFoundError(
                    f"Session {session_id} not found or inaccessible: {e}"
                ) from e

        # Create new session
        session = self._client.create_session(database_id=database_id, mode=mode, enable_search=enable_search, file_id=file_id)

        # Only wait if session is not already running
        if wait_for_running and not session.is_running():
            session = self.wait_until_running(
                session_id=session.session_id,
                agent_id=session.agent_id,
                max_wait=600,  # Increase max_wait to 10 minutes (600 seconds) since backend can be slow
            )

        self._active_sessions[session.session_id] = session
        return session

    def wait_until_running(
        self,
        session_id: str,
        agent_id: str = "",
        max_wait: int = 120,
    ) -> SessionInfo:
        """Wait for session to reach RUNNING state.

        Args:
            session_id: The session ID.
            agent_id: The agent ID (optional).
            max_wait: Maximum wait time in seconds.

        Returns:
            SessionInfo with RUNNING status.

        Raises:
            SessionTimeoutError: If session doesn't reach RUNNING state.
        """
        config = self._client.config
        poll_interval = config.poll_interval
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                raise SessionTimeoutError(
                    f"Session {session_id} did not reach RUNNING state within {max_wait} seconds",
                    session_id=session_id,
                    waited_seconds=int(elapsed),
                )

            session = self._client.describe_session(session_id=session_id, agent_id=agent_id)

            if session.is_running():
                return session
            elif session.status == SessionStatus.FAILED:
                raise SessionTimeoutError(
                    f"Session {session_id} failed to start",
                    session_id=session_id,
                    waited_seconds=int(elapsed),
                )
            elif session.status == SessionStatus.STOPPED:
                raise SessionTimeoutError(
                    f"Session {session_id} was stopped unexpectedly",
                    session_id=session_id,
                    waited_seconds=int(elapsed),
                )

            time.sleep(poll_interval)

    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is still active and usable.

        Args:
            session_id: The session ID to check.

        Returns:
            True if session is active and RUNNING.
        """
        if session_id not in self._active_sessions:
            return False

        session = self._active_sessions[session_id]

        # Consider session stale if not used for 30 minutes
        if datetime.now() - session.last_used_at > timedelta(minutes=30):
            return False

        try:
            current = self._client.describe_session(session_id=session_id, agent_id=session.agent_id)
            return current.is_running()
        except Exception:
            return False

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session info from cache.

        Args:
            session_id: The session ID.

        Returns:
            SessionInfo if found, None otherwise.
        """
        return self._active_sessions.get(session_id)

    def refresh_session(self, session_id: str) -> SessionInfo:
        """Refresh session status from API.

        Args:
            session_id: The session ID.

        Returns:
            Updated SessionInfo.

        Raises:
            SessionNotFoundError: If session is not in cache.
        """
        if session_id not in self._active_sessions:
            raise SessionNotFoundError(f"Session {session_id} not found in cache")

        session = self._active_sessions[session_id]
        updated = self._client.describe_session(session_id=session_id, agent_id=session.agent_id)
        self._active_sessions[session_id] = updated
        return updated

    def remove_session(self, session_id: str) -> None:
        """Remove session from cache.

        Args:
            session_id: The session ID to remove.
        """
        self._active_sessions.pop(session_id, None)

    def list_sessions(self) -> list[SessionInfo]:
        """List all cached sessions.

        Returns:
            List of SessionInfo objects.
        """
        return list(self._active_sessions.values())

    def clear_stale_sessions(self, max_age_minutes: int = 30) -> int:
        """Remove stale sessions from cache.

        Args:
            max_age_minutes: Maximum session age in minutes.

        Returns:
            Number of sessions removed.
        """
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        stale_ids = [
            sid for sid, session in self._active_sessions.items()
            if session.last_used_at < cutoff
        ]

        for sid in stale_ids:
            del self._active_sessions[sid]

        return len(stale_ids)


class AsyncSessionManager:
    """Asynchronous session manager for Data Agent.

    Provides async/await support for session management operations.
    """

    def __init__(self, client: AsyncDataAgentClient):
        """Initialize async session manager.

        Args:
            client: AsyncDataAgentClient instance for API calls.
        """
        self._client = client
        self._active_sessions: Dict[str, SessionInfo] = {}

    async def create_or_reuse(
        self,
        session_id: Optional[str] = None,
        database_id: Optional[str] = None,
        wait_for_running: bool = True,
    ) -> SessionInfo:
        """Create a new session or reuse an existing one asynchronously.

        Args:
            session_id: Optional existing session ID to reuse.
            database_id: Optional database ID to bind to new session.
            wait_for_running: Whether to wait for session to be RUNNING.

        Returns:
            SessionInfo for the active session.
        """
        # Try to reuse existing session
        if session_id:
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                if await self.is_session_active(session_id):
                    session.update_last_used()
                    return session

            try:
                session = await self._client.describe_session(
                    session_id=session_id,
                    agent_id="",
                )
                if session.is_running():
                    self._active_sessions[session_id] = session
                    return session
            except Exception:
                pass

        # Create new session
        session = await self._client.create_session(database_id=database_id)

        # Only wait if session is not already running
        if wait_for_running and not session.is_running():
            session = await self.wait_until_running(
                session_id=session.session_id,
                agent_id=session.agent_id,
            )

        self._active_sessions[session.session_id] = session
        return session

    async def wait_until_running(
        self,
        session_id: str,
        agent_id: str = "",
        max_wait: int = 120,
    ) -> SessionInfo:
        """Wait for session to reach RUNNING state asynchronously.

        Args:
            session_id: The session ID.
            agent_id: The agent ID (optional).
            max_wait: Maximum wait time in seconds.

        Returns:
            SessionInfo with RUNNING status.

        Raises:
            SessionTimeoutError: If session doesn't reach RUNNING state.
        """
        config = self._client.config
        poll_interval = config.poll_interval
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                raise SessionTimeoutError(
                    f"Session {session_id} did not reach RUNNING state within {max_wait} seconds",
                    session_id=session_id,
                    waited_seconds=int(elapsed),
                )

            session = await self._client.describe_session(session_id=session_id, agent_id=agent_id)

            if session.is_running():
                return session
            elif session.status in (SessionStatus.FAILED, SessionStatus.STOPPED):
                raise SessionTimeoutError(
                    f"Session {session_id} failed or stopped",
                    session_id=session_id,
                    waited_seconds=int(elapsed),
                )

            await asyncio.sleep(poll_interval)

    async def is_session_active(self, session_id: str) -> bool:
        """Check if a session is still active asynchronously.

        Args:
            session_id: The session ID to check.

        Returns:
            True if session is active and RUNNING.
        """
        if session_id not in self._active_sessions:
            return False

        session = self._active_sessions[session_id]

        if datetime.now() - session.last_used_at > timedelta(minutes=30):
            return False

        try:
            current = await self._client.describe_session(session_id=session_id, agent_id=session.agent_id)
            return current.is_running()
        except Exception:
            return False

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session info from cache.

        Args:
            session_id: The session ID.

        Returns:
            SessionInfo if found, None otherwise.
        """
        return self._active_sessions.get(session_id)

    async def refresh_session(self, session_id: str) -> SessionInfo:
        """Refresh session status from API asynchronously.

        Args:
            session_id: The session ID.

        Returns:
            Updated SessionInfo.

        Raises:
            SessionNotFoundError: If session is not in cache.
        """
        if session_id not in self._active_sessions:
            raise SessionNotFoundError(f"Session {session_id} not found in cache")

        session = self._active_sessions[session_id]
        updated = await self._client.describe_session(session_id=session_id, agent_id=session.agent_id)
        self._active_sessions[session_id] = updated
        return updated

    def remove_session(self, session_id: str) -> None:
        """Remove session from cache.

        Args:
            session_id: The session ID to remove.
        """
        self._active_sessions.pop(session_id, None)

    def list_sessions(self) -> list[SessionInfo]:
        """List all cached sessions.

        Returns:
            List of SessionInfo objects.
        """
        return list(self._active_sessions.values())
