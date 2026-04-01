"""File analysis subcommand (file).

Author: Tinker
Created: 2026-03-04
"""

import argparse
import sys
import os
import json
import subprocess
from pathlib import Path

# from cli.notify import push_notification
from cli.worker_utils import is_worker_process, setup_async_worker, handle_worker_completion
from cli.streaming_utils import run_worker_with_handler, execute_single_query, execute_query_batch
from cli.worker_lock import check_worker_lock, write_worker_pid, acquire_worker_lock, release_worker_lock
from cli.dual_logger import run_with_dual_logging
from cli.streaming import _stream_response
from data_agent import (
    DataAgentConfig,
    DataAgentClient,
    SessionManager,
    MessageHandler,
    FileManager,
    DataSource,
)


def cmd_file(args: argparse.Namespace) -> None:
    """Handle file subcommand."""
    file_id = getattr(args, 'file_id', None)
    file_path = args.file_path

    # Validate arguments
    if not file_id and not file_path:
        print("Error: Either FILE path or --file-id must be provided", file=sys.stderr)
        sys.exit(1)
    if file_id and file_path:
        print("Error: Cannot specify both FILE path and --file-id", file=sys.stderr)
        sys.exit(1)

    # Initialize components
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)
    session_manager = SessionManager(client)
    message_handler = MessageHandler(client)
    file_manager = FileManager(client)

    is_worker = is_worker_process()
    session_mode = args.session_mode.upper()

    if getattr(args, "async_run", False) and not is_worker:
        # PARENT PROCESS LOGIC
        enable_search = getattr(args, 'enable_search', False)
        print(f"Creating session for async file analysis...")

        if file_id:
            # Using Data Center file ID
            print(f"Using Data Center file ID: {file_id}")

            # Create data source with file ID for query execution
            file_data_source = DataSource(
                data_source_type="FILE",
                file_id=file_id,
                region_id=config.region
            )

            # Create regular session without binding to specific data source initially
            session = session_manager.create_or_reuse(mode=session_mode, enable_search=enable_search, file_id=file_id)
        else:
            # Local file workflow: upload first
            if not Path(file_path).exists():
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                sys.exit(1)

            # Validate file type
            if not file_manager.is_supported_file(file_path):
                supported = ".csv, .xlsx, .xls"
                print(f"Error: Unsupported file type. Supported formats: {supported}", file=sys.stderr)
                sys.exit(1)

            # Upload file and get file info
            print(f"Uploading file: {file_path}")
            try:
                file_info = file_manager.upload_file(file_path)
                print(f"File uploaded successfully!")
                print(f"  File ID : {file_info.file_id}")
                print(f"  Filename: {file_info.filename}")
                print(f"  Size    : {file_info.size} bytes")

                # Create data source with uploaded file ID
                file_data_source = DataSource(
                    data_source_type="FILE",
                    file_id=file_info.file_id,
                )
            except Exception as e:
                print(f"Upload failed: {e}", file=sys.stderr)
                sys.exit(1)

            # Create session
            session = session_manager.create_or_reuse(mode=session_mode, enable_search=enable_search, file_id=file_info.file_id)

        # Store file_data_source as a dict for async worker to use (avoid serialization issues)
        args.file_data_source = file_data_source.to_api_dict()

        # Use common async worker setup
        setup_async_worker(args, session)

        print(f"\n✅ Async task started. Session ID: {session.session_id}")
        print(f"Check progress at: sessions/{session.session_id}/progress.log")

        sys.exit(0)

    elif is_worker:
        # WORKER PROCESS LOGIC - using common utility
        def file_query_executor(message_handler, session, args):
            if hasattr(args, 'file_data_source'):
                # If file_data_source is a dict (async mode), reconstruct DataSource
                if isinstance(args.file_data_source, dict):
                    # Create a new DataSource from the dict representation
                    # For file analysis, we need to use data_source_type="FILE" and the correct file_id
                    # The DataSource.to_api_dict() method expects data_source_type="FILE" to trigger FileId inclusion
                    file_data_source = DataSource(
                        data_source_type="FILE",  # Use "FILE" type for file analysis
                        file_id=args.file_data_source.get('FileId', ''),
                        region_id=args.file_data_source.get('RegionId', config.region)
                    )
                else:
                    # If file_data_source is already a DataSource object (sync mode)
                    file_data_source = args.file_data_source
            else:
                # Try to load from input.json if not available in args
                # In worker process, we can determine the session dir and load input.json
                import json
                from pathlib import Path
                session_dir = Path(f"sessions/{session.session_id}")
                input_file = session_dir / "input.json"

                if input_file.exists():
                    try:
                        with open(input_file, 'r', encoding='utf-8') as f:
                            saved_args = json.load(f)

                        if 'file_data_source' in saved_args:
                            file_data_source_dict = saved_args['file_data_source']
                            # Create DataSource for file analysis using data_source_type="FILE"
                            file_data_source = DataSource(
                                data_source_type="FILE",  # Use "FILE" type for file analysis
                                file_id=file_data_source_dict.get('FileId', ''),
                                region_id=file_data_source_dict.get('RegionId', config.region)
                            )
                    except Exception as e:
                        print(f"Warning: Could not load file_data_source from input.json: {e}", file=sys.stderr)

            if file_data_source is None:
                # Fallback: reconstruct based on available info
                if hasattr(args, 'file_id') and args.file_id:
                    file_data_source = DataSource(
                        data_source_type="FILE",
                        file_id=args.file_id,
                        region_id=getattr(args, 'region_id', 'cn-hangzhou')
                    )
                else:
                    print("Error: No file data source available in worker", file=sys.stderr)
                    return False, False

            output_mode = getattr(args, "output", "summary")
            session_dir = Path(f"sessions/{session.session_id}")

            if args.query:
                queries = [args.query]
            else:
                queries = [
                    "请分析上传文件的数据结构",
                    "数据的关键统计指标和分布情况是什么？",
                    "数据中是否存在异常值或离群点？",
                ]

            print(f"\n{'=' * 60}")
            print("File Analysis")
            print("=" * 60)

            output_text = ""
            for query in queries:
                print(f"\nQuery: {query}")
                print("-" * 50)
                got_content, need_confirm, t = _stream_response(
                    message_handler, session, query,
                    data_source=file_data_source, output_mode=output_mode,
                    output_dir=session_dir,
                )
                if t:
                    output_text += f"\n### Query: {query}\n" + t + "\n"

                if need_confirm:
                    return got_content, need_confirm  # got_content, need_confirm

            if args.list_generated_files:
                _print_generated_files(file_manager, session.session_id)

            return True, False  # got_content=True, need_confirm=False

        # Pass args as-is since we've attached file_data_source to it
        run_worker_with_handler(args, query_execution_func=file_query_executor)

    # NORMAL SYNCHRONOUS LOGIC
    if file_id:
        # Using Data Center file ID
        print(f"Using Data Center file ID: {file_id}")

        # Create data source with file ID
        file_data_source = DataSource(
            data_source_type="FILE",
            file_id=file_id,
            region_id=config.region
        )
    else:
        # Local file workflow: validate and upload
        if not Path(file_path).exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)

        # Validate file type
        if not file_manager.is_supported_file(file_path):
            supported = ".csv, .xlsx, .xls"
            print(f"Error: Unsupported file type. Supported formats: {supported}", file=sys.stderr)
            sys.exit(1)

        # Upload file
        print(f"Uploading file: {file_path}")
        try:
            file_info = file_manager.upload_file(file_path)
        except Exception as e:
            print(f"Upload failed: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"File uploaded successfully!")
        print(f"  File ID : {file_info.file_id}")
        print(f"  Filename: {file_info.filename}")
        print(f"  Size    : {file_info.size} bytes")

        # Create data source for uploaded file
        file_data_source = DataSource(
            data_source_type="FILE",
            file_id=file_info.file_id,
        )

    # Create session
    session_mode = args.session_mode.upper()
    mode_desc = {
        "ASK_DATA": "ASK_DATA mode",
        "ANALYSIS": "ANALYSIS mode (recommended for file analysis)",
        "INSIGHT": "INSIGHT mode",
    }.get(session_mode, session_mode)

    print(f"\nCreating session: {mode_desc}...")
    print(f"  Region: {config.region}")
    enable_search = getattr(args, 'enable_search', False)
    # For file analysis, pass file_id to create_or_reuse so the session is bound to the file
    session = session_manager.create_or_reuse(mode=session_mode, enable_search=enable_search, file_id=file_data_source.file_id if 'file_data_source' in locals() else None)
    print(f"Session ready: {session.session_id}")
    print(f"\n💡 Tip: To continue this session later, use: python3 data_agent_cli.py attach --session-id {session.session_id}")

    # Get output mode
    output_mode = getattr(args, "output", "summary")
    session_dir = Path(f"sessions/{session.session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Initialize structured logging for sync mode
    from cli.streaming import init_structured_logging, close_structured_logging
    init_structured_logging(session_dir)

    try:
        # Determine queries to execute
        if args.query:
            queries = [args.query]
        else:
            # Default preset analysis questions
            queries = [
                "请分析上传文件的数据结构",
                "数据的关键统计指标和分布情况是什么？",
                "数据中是否存在异常值或离群点？",
            ]

        # Execute queries with the file data source
        print(f"\n{'=' * 60}")
        print("File Analysis")
        print("=" * 60)

        output_text = ""
        for query in queries:
            print(f"\nQuery: {query}")
            print("-" * 50)
            try:
                got_content, need_confirm, t = _stream_response(
                    message_handler, session, query,
                    data_source=file_data_source, output_mode=output_mode,
                    output_dir=session_dir,
                )
                if t:
                    output_text += f"\n### Query: {query}\n" + t + "\n"

                if not got_content:
                    print("(No response received, please retry)")
                elif need_confirm:
                    print("\n⚠️  Agent has created an execution plan. User confirmation required.")
                    print(f"   To continue: python3 scripts/data_agent_cli.py attach --session-id {session.session_id} -q 'User Input' ")
                    if output_text:
                        with open(session_dir / "output.md", "w", encoding="utf-8") as f:
                            f.write(output_text)
                        with open(session_dir / "result.json", "w", encoding="utf-8") as f:
                            json.dump({"status": "waiting_input", "output_file": "output.md"}, f)
                    return
            except Exception as e:
                print(f"Request failed: {e}")

        # List generated files if requested
        if args.list_generated_files:
            _print_generated_files(file_manager, session.session_id)

    finally:
        # Close structured logging
        close_structured_logging()

    # Write result status
    with open(session_dir / "result.json", "w", encoding="utf-8") as f:
        json.dump({"status": "completed"}, f)


def _print_generated_files(file_manager: FileManager, session_id: str) -> None:
    """Print list of files generated by the Agent."""
    print(f"\n{'=' * 60}")
    print("Generated Files")
    print("=" * 60)
    try:
        generated = file_manager.list_files(session_id)
        if generated:
            for f in generated:
                print(f"  - {f.filename} ({f.file_type}, {f.size} bytes)")
                if f.download_url:
                    print(f"    Download: {f.download_url}")
        else:
            print("  No generated files.")
    except Exception as e:
        print(f"  Failed to get file list: {e}")