"""Database analysis subcommand (db).

Author: Tinker
Created: 2026-03-04
"""

import argparse
import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Optional

# from cli.notify import push_notification
from cli.worker_lock import check_worker_lock, write_worker_pid, acquire_worker_lock, release_worker_lock
from cli.worker_utils import is_worker_process, setup_async_worker, handle_worker_completion
from cli.streaming_utils import run_worker_with_handler, execute_single_query, execute_query_batch
from cli.streaming import _stream_response, _finalize_stream, StreamState, _print_event
from data_agent import (
    DataAgentConfig,
    DataAgentClient,
    SessionManager,
    MessageHandler,
    FileManager,
    DataSource,
    SSEClient,
)


def _build_data_source(args: argparse.Namespace) -> DataSource:
    """Build DataSource from command-line arguments."""
    tables = [t.strip() for t in args.tables.split(",")] if args.tables else []
    table_ids = [t.strip() for t in args.table_ids.split(",")] if args.table_ids else []

    return DataSource(
        dms_instance_id=args.dms_instance_id,
        dms_database_id=args.dms_db_id,
        instance_name=args.instance_name,
        db_name=args.db_name,
        tables=tables,
        table_ids=table_ids,
        engine=args.engine,
        region_id=args.region,
    )


def _db_attach(
    sse_client: SSEClient,
    file_manager: FileManager,
    session,
    from_start: bool = False,
    checkpoint: Optional[int] = None,
    output_mode: str = "summary",
) -> None:
    """Attach to an existing session's SSE stream without sending a message.

    Streams all incoming events to stdout in real-time using the same
    formatting as _stream_response.  Useful for:
      - Watching an ongoing analysis
      - Replaying the last round to review a plan before confirming

    After the stream ends, calls ListFileUpload to download any
    agent-generated report files to sessions/<session_id>/reports/.
    """
    session_id = session.session_id
    session_dir = Path(f"sessions/{session_id}")

    if checkpoint is None:
        checkpoint = 0 if from_start else None

    label = "watching live stream"
    if from_start:
        label = "replaying from start"
    elif checkpoint is not None:
        label = f"resuming from checkpoint {checkpoint}"

    print(f"\nAttaching to session {session_id} ({label})...")
    print(f"Session status: {session.status.value}")

    # Special reminder for WAIT_INPUT status
    if session.status.value == "WAIT_INPUT":
        print("\n⚠️  Session is in WAIT_INPUT state.")
        print("   The agent has generated SQL and is waiting for your confirmation.")
        print()
        print("   To view the SQL and confirm:")
        print(f"     python3 skill/data_agent_cli.py attach --session-id {session_id} --from-start")
        print()
        print("   To confirm and execute ONLY this SQL (DO NOT create a new session):")
        print(f"     python3 skill/data_agent_cli.py attach --session-id {session_id} -q '确认执行当前SQL'")
        print()
        print("   To agree to execute all subsequent SQL automatically:")
        print(f"     python3 skill/data_agent_cli.py attach --session-id {session_id} -q '同意后续所有SQL执行'")
        print()
        print("   To modify the query:")
        print(f"     python3 skill/data_agent_cli.py attach --session-id {session_id} -q 'your new question'")

    print(f"Output directory: {session_dir.resolve()}")
    print("Press Ctrl+C to detach.")
    print("\n---\n")

    got_content = False
    last_checkpoint = checkpoint if checkpoint else 0
    last_progress_time = 0
    import time

    state = StreamState(output_mode=output_mode)
    state.output_dir = session_dir
    state.session_id = session_id
    state.is_attach = True
    state.session_status = getattr(session, 'status', None)
    if hasattr(state.session_status, 'value'):
        state.session_status = state.session_status.value

    try:
        # Initialize structured logging for attach mode
        from cli.streaming import init_structured_logging, close_structured_logging
        init_structured_logging(session_dir)

        for event in sse_client.stream_chat_content(
            agent_id=session.agent_id,
            session_id=session_id,
            checkpoint=checkpoint,
        ):
            if event.event_type == "SSE_FINISH":
                break

            # Track checkpoint progress (only in detail/raw mode)
            if output_mode != "summary" and event.checkpoint is not None and event.checkpoint > last_checkpoint:
                current_time = time.time()
                # Show checkpoint progress every 30 seconds or every 50 checkpoints
                if current_time - last_progress_time >= 30 or event.checkpoint - last_checkpoint >= 50:
                    print(f"  [checkpoint: {event.checkpoint}]", flush=True)
                    last_progress_time = current_time
                last_checkpoint = event.checkpoint

            c, _ = _print_event(event, output_mode, state=state)
            if c:
                got_content = True

    except KeyboardInterrupt:
        print("\n\nDetached.")
        return
    except Exception as e:
        # Extract request_id from HTTP error response if available
        request_id = ""
        resp = getattr(e, "response", None)
        if resp is not None:
            request_id = resp.headers.get("x-acs-request-id", "")
        rid_str = f" (Request-Id: {request_id})" if request_id else ""
        print(f"\nError: {e}{rid_str}", file=sys.stderr)
        return
    finally:
        # Close structured logging
        close_structured_logging()

    _finalize_stream(state)
    if state.got_content:
        got_content = True

    if got_content:
        print()  # trailing newline
    else:
        print("(No new events -- session may be waiting for your input)")

    # -- Download agent-generated files via ListFileUpload --
    # Server needs a few seconds to finalize report files after session completes
    print("\nFetching agent-generated files (waiting for server to finalize)...")
    time.sleep(5)
    report_dir = session_dir / "reports"
    total_reports = 0
    for category in ("WebReport", "TextReport", "DefaultArtifact"):
        try:
            files = file_manager.list_files(session_id, file_category=category)
        except Exception as e:
            print(f"  Warning: could not list {category}: {e}", file=sys.stderr)
            continue
        if not files:
            continue
        report_dir.mkdir(parents=True, exist_ok=True)
        for rf in files:
            if not rf.download_url:
                print(f"  Skipping {rf.filename} ({category}): no download URL")
                continue
            save_path = report_dir / (rf.filename or f"{rf.file_id}.bin")
            try:
                file_manager.download_from_url(rf.download_url, str(save_path))
                print(f"  [{category}] saved \u2192 {save_path.resolve()}")
                total_reports += 1
            except Exception as e:
                print(f"  Failed to download {rf.filename} ({category}): {e}", file=sys.stderr)

    if total_reports == 0:
        print("  No report files found for this session.")

    print("\n---\n")
    print(f'> \U0001f4a1 To continue conversation:')
    print(f'>    python3 skill/data_agent_cli.py attach --session-id {session_id} -q "your message"')


def _db_batch(
    message_handler: MessageHandler,
    session,
    data_source: DataSource,
    queries: list,
    output_mode: str = "summary",
    output_dir: Optional[Path] = None,
) -> tuple[bool, bool, str]:
    """Execute batch preset queries."""
    got_content, need_confirm = False, False
    full_text = ""
    for query in queries:
        print(f"\n{'=' * 60}")
        print(f"Query: {query}")
        print("=" * 60)
        c, nc, t = _stream_response(message_handler, session, query, data_source=data_source, output_mode=output_mode, output_dir=output_dir)
        if c: got_content = True
        if t: full_text += f"\n### Query: {query}\n" + t + "\n"
        if nc:
            need_confirm = True
            break
    return got_content, need_confirm, full_text


def _db_single(
    message_handler: MessageHandler,
    session,
    data_source: DataSource,
    query: str,
    output_mode: str = "summary",
    output_dir: Optional[Path] = None,
) -> tuple[bool, bool, str]:
    """Execute a single query with streaming output."""
    print(f"\nAnalyzing...\n")
    got_content, need_confirm, full_text = _stream_response(
        message_handler, session, query, data_source=data_source, output_mode=output_mode, output_dir=output_dir
    )
    if not got_content:
        print("(No response received, please retry)")
    elif need_confirm:
        print("\n\u26a0\ufe0f  \u9700\u8981\u7528\u6237\u786e\u8ba4\uff0c\u7a0b\u5e8f\u5c06\u9000\u51fa\u3002\u8bf7\u5b8c\u6210\u786e\u8ba4\u540e\u4f7f\u7528\u4f1a\u8bddID\u7ee7\u7eed\u5bf9\u8bdd\u3002")
    return got_content, need_confirm, full_text


def cmd_db(args: argparse.Namespace) -> None:
    """Handle db subcommand."""
    # Validate required database parameters
    missing = []
    for attr, name in [
        ("dms_instance_id", "--dms-instance-id"),
        ("dms_db_id", "--dms-db-id"),
        ("instance_name", "--instance-name"),
        ("db_name", "--db-name"),
        ("tables", "--tables"),
    ]:
        if not getattr(args, attr, None):
            missing.append(name)
    if missing:
        print(f"Error: Missing required parameters: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Initialize components
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)
    session_manager = SessionManager(client)
    message_handler = MessageHandler(client)

    # Create new session
    session_mode = args.session_mode.upper()
    data_source = _build_data_source(args)
    is_worker = is_worker_process()

    if getattr(args, "async_run", False) and not is_worker:
        # PARENT PROCESS LOGIC
        enable_search = getattr(args, 'enable_search', False)
        print(f"Creating session for async execution...")
        session = session_manager.create_or_reuse(mode=session_mode, database_id=str(args.dms_db_id), enable_search=enable_search)

        # Use common async worker setup
        setup_async_worker(args, session)

    elif is_worker:
        # WORKER PROCESS LOGIC - using common utility
        def db_query_executor(message_handler, session, args):
            output_mode = getattr(args, "output", "summary")
            data_source = _build_data_source(args)

            if args.query:
                _, need_confirm, _ = _db_single(message_handler, session, data_source, args.query, output_mode=output_mode, output_dir=Path(f"sessions/{session.session_id}"))
            else:
                if session_mode == "ANALYSIS":
                    default_queries = [
                        f"Analyze the overall data structure and table relationships of {data_source.db_name} database",
                        "Identify key metrics and distribution characteristics in the data",
                    ]
                else:
                    default_queries = [
                        f"What tables exist in {data_source.db_name} database?",
                        "Who has the highest sales?",
                    ]
                _, need_confirm, _ = _db_batch(message_handler, session, data_source, default_queries, output_mode=output_mode, output_dir=Path(f"sessions/{session.session_id}"))
            return True, need_confirm  # got_content=True, need_confirm

        run_worker_with_handler(args, data_source=_build_data_source(args), query_execution_func=db_query_executor)

    # NORMAL SYNCHRONOUS LOGIC
    mode_desc = {
        "ASK_DATA": "ASK_DATA mode (SQL query + natural language response)",
        "ANALYSIS": "ANALYSIS mode (deep analysis + report generation)",
        "INSIGHT": "INSIGHT mode",
    }.get(session_mode, session_mode)

    print(f"Creating session: {mode_desc}...")
    print(f"  Region: {config.region}")
    enable_search = getattr(args, 'enable_search', False)
    session = session_manager.create_or_reuse(mode=session_mode, database_id=str(args.dms_db_id), enable_search=enable_search)
    print(f"Session ready: {session.session_id}")
    print(f"\n💡 Tip: To continue this session later, use: python3 scripts/data_agent_cli.py attach --session-id {session.session_id}")

    # Execute query
    output_mode = getattr(args, "output", "summary")
    session_dir = Path(f"sessions/{session.session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Initialize structured logging for sync mode
    from cli.streaming import init_structured_logging, close_structured_logging
    init_structured_logging(session_dir)

    try:
        if args.query:
            _, _, output_text = _db_single(message_handler, session, data_source, args.query, output_mode=output_mode, output_dir=session_dir)
        else:
            # Default batch preset queries
            if session_mode == "ANALYSIS":
                default_queries = [
                    f"Analyze the overall data structure and table relationships of {data_source.db_name} database",
                    "Identify key metrics and distribution characteristics in the data",
                ]
            else:
                default_queries = [
                    f"What tables exist in {data_source.db_name} database?",
                    "Who has the highest sales?",
                ]
            print(f"\nNo query specified, running preset queries ({len(default_queries)} total)...")
            _, _, output_text = _db_batch(message_handler, session, data_source, default_queries, output_mode=output_mode, output_dir=session_dir)
    finally:
        close_structured_logging()

    # Write result status
    # if output_text:
    #     with open(session_dir / "output.md", "w", encoding="utf-8") as f:
    #         f.write(output_text)
    #     with open(session_dir / "result.json", "w", encoding="utf-8") as f:
    #         json.dump({"status": "completed", "output_file": "output.md"}, f)
    with open(session_dir / "result.json", "w", encoding="utf-8") as f:
        json.dump({"status": "completed"}, f)
