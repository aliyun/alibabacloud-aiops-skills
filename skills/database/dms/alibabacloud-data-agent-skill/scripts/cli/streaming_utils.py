"""Common utilities for streaming and session management in Data Agent CLI."""

import os
import sys
import json
from pathlib import Path
from typing import Tuple, Optional, List

from cli.log_handler import StructuredLogHandler
from cli.worker_lock import acquire_worker_lock, release_worker_lock
from cli.worker_utils import handle_worker_completion, get_worker_session_details, initialize_components
from data_agent import SessionManager, MessageHandler, DataSource


def execute_query_batch(
    message_handler: MessageHandler,
    session,
    queries: List[str],
    output_mode: str = "summary",
    output_dir: Optional[Path] = None,
    data_source: Optional[DataSource] = None,
    process_log_handler: Optional[StructuredLogHandler] = None
) -> tuple[bool, bool, str]:
    """Execute a batch of queries with streaming output.

    Args:
        message_handler: Message handler instance
        session: Session object
        queries: List of queries to execute
        output_mode: Output mode (summary/detail/raw)
        output_dir: Output directory for files
        data_source: Optional data source for the queries
        process_log_handler: Optional process log handler

    Returns:
        Tuple of (got_content, need_confirm, full_text)
    """
    got_content, need_confirm = False, False
    full_text = ""

    for i, query in enumerate(queries):
        if len(queries) > 1:  # Only print separators for multiple queries
            print(f"\n{'=' * 60}")
            print(f"Query {i+1}/{len(queries)}: {query}")
            print("=" * 60)
        else:
            print(f"\nQuery: {query}")

        c, nc, t = _stream_response_with_data_source(
            message_handler, session, query,
            data_source=data_source,
            output_mode=output_mode,
            output_dir=output_dir,
            process_log_handler=process_log_handler
        )

        if c:
            got_content = True
        if t:
            full_text += f"\n### Query: {query}\n" + t + "\n"
        if nc:
            need_confirm = True
            break  # Stop processing if confirmation is needed

    return got_content, need_confirm, full_text


def _stream_response_with_data_source(
    message_handler: MessageHandler,
    session,
    query: str,
    data_source: Optional[DataSource] = None,
    output_mode: str = "summary",
    output_dir: Optional[Path] = None,
    process_log_handler: Optional[StructuredLogHandler] = None
) -> tuple[bool, bool, str]:
    """Wrapper for _stream_response that handles data_source parameter properly."""
    # Import the streaming function from the existing module
    from cli.streaming import _stream_response
    return _stream_response(
        message_handler, session, query,
        data_source=data_source, output_mode=output_mode, output_dir=output_dir,
        process_log_handler=process_log_handler
    )


def execute_single_query(
    message_handler: MessageHandler,
    session,
    query: str,
    output_mode: str = "summary",
    output_dir: Optional[Path] = None,
    data_source: Optional[DataSource] = None,
    process_log_handler: Optional[StructuredLogHandler] = None
) -> tuple[bool, bool, str]:
    """Execute a single query with streaming output.

    Args:
        message_handler: Message handler instance
        session: Session object
        query: Query to execute
        output_mode: Output mode (summary/detail/raw)
        output_dir: Output directory for files
        data_source: Optional data source for the query
        process_log_handler: Optional process log handler

    Returns:
        Tuple of (got_content, need_confirm, full_text)
    """
    print(f"\nAnalyzing...\n")
    got_content, need_confirm, full_text = _stream_response_with_data_source(
        message_handler, session, query,
        data_source=data_source, output_mode=output_mode, output_dir=output_dir,
        process_log_handler=process_log_handler
    )
    if not got_content:
        print("(No response received, please retry)")
    elif need_confirm:
        print("\n⚠️  需要用户确认，程序将退出。请完成确认后使用会话ID继续对话。")
    return got_content, need_confirm, full_text


def run_worker_with_handler(
    args,
    data_source: Optional[DataSource] = None,
    query_execution_func=None
) -> None:
    """Generic worker execution with common error handling and session management.

    Args:
        args: Command line arguments
        data_source: Optional data source for queries
        query_execution_func: Function to execute queries, receives (message_handler, session, args)
    """
    from cli.worker_lock import acquire_worker_lock, release_worker_lock

    # Get session details from environment
    session_id, agent_id = get_worker_session_details()
    session_dir = Path(f"sessions/{session_id}")

    # Redirect stdout to progress.log for worker process
    log_file_path = session_dir / "progress.log"
    log_file = open(log_file_path, "a", encoding="utf-8")  # Changed from "w" to "a" to append instead of overwrite
    sys.stdout = log_file
    sys.stderr = log_file

    print(f"[Worker] Session ID: {session_id}", flush=True)
    print(f"[Worker] Agent ID: {agent_id}", flush=True)
    acquire_worker_lock(session_dir)

    try:
        # Initialize components
        _, _, session_manager, message_handler = initialize_components()

        print("[Worker] Connecting to session...", flush=True)
        # Parent already verified the session is ready (AgentStatus=RUNNING),
        # so skip wait_for_running — DescribeDataAgentSession may report
        # SessionStatus=CREATING for a long time even when the session is
        # fully usable.
        session = session_manager.create_or_reuse(
            session_id=session_id, agent_id=agent_id, wait_for_running=False
        )
        print(f"[Worker] Session connected (status={session.status.value})", flush=True)

        output_mode = getattr(args, "output", "summary")
        output_text = ""

        # Execute queries using provided function or default behavior
        if query_execution_func:
            got_content, need_confirm = query_execution_func(
                message_handler, session, args
            )
        else:
            # Default behavior: handle query if provided, otherwise use presets
            # This is a simplified default - in practice, each command should provide its own execution function
            if hasattr(args, 'query') and args.query:
                got_content, need_confirm, output_text = execute_single_query(
                    message_handler, session, args.query,
                    output_mode=output_mode, output_dir=session_dir,
                    data_source=data_source
                )
            else:
                # Provide a simple default query execution - customize per command type
                default_queries = ["What can you help me with?"]
                got_content, need_confirm, output_text = execute_query_batch(
                    message_handler, session, default_queries,
                    output_mode=output_mode, output_dir=session_dir,
                    data_source=data_source
                )

        # Handle results
        handle_worker_completion(session_dir, need_confirm)

    except Exception as e:
        # Handle error
        handle_worker_completion(session_dir, error=e)
        print(f"Error: {e}", file=sys.stderr, flush=True)
    finally:
        release_worker_lock(session_dir)
        # Close structured logging files
        from cli.streaming import close_structured_logging
        close_structured_logging()
        # Close the redirected file
        log_file.close()

    sys.exit(0)