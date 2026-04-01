"""Attach to existing session subcommand (attach).

Author: Tinker
Created: 2026-03-04
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from cli.streaming import _stream_response, StreamState, _print_event
from cli.cmd_db import _db_attach
from cli.log_handler import StructuredLogHandler
# from cli.notify import push_notification
from cli.worker_utils import is_worker_process, setup_async_worker, handle_worker_completion
from cli.streaming_utils import run_worker_with_handler, execute_single_query
from cli.worker_lock import check_worker_lock, write_worker_pid, acquire_worker_lock, release_worker_lock
from data_agent import (
    DataAgentConfig,
    DataAgentClient,
    SessionManager,
    MessageHandler,
    FileManager,
    SSEClient,
)


def cmd_attach(args: argparse.Namespace) -> None:
    """Connect to an existing session for continuing analysis or confirming plan."""
    session_id = args.session_id
    is_worker = os.environ.get("DATA_AGENT_ASYNC_WORKER") == "1"
    async_run = getattr(args, "async_run", True)

    # Initialize components
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)
    session_manager = SessionManager(client)
    message_handler = MessageHandler(client)
    sse_client = SSEClient(config)
    file_manager = FileManager(client)

    # Async mode is determined by the --async-run/--no-async-run flag, regardless of query presence
    if async_run and not is_worker:
        # PARENT PROCESS: spawn background worker
        print(f"Connecting to session: {session_id}")
        try:
            session = client.describe_session(session_id=session_id)
        except Exception as e:
            print(f"Error: Failed to connect to session: {e}", file=sys.stderr)
            sys.exit(1)

        # Manually create a temporary session object to pass to the common utility
        class TempSession:
            def __init__(self, sess_obj):
                self.session_id = sess_obj.session_id
                self.agent_id = sess_obj.agent_id

        temp_session = TempSession(session)

        # Use common async worker setup
        setup_async_worker(args, temp_session)

    elif is_worker:
        # WORKER PROCESS: run the attach operation in background - using common utility
        def attach_query_executor(message_handler, session, args):
            output_mode = getattr(args, "output", "summary")
            session_dir = Path(f"sessions/{session.session_id}")

            query = args.query

            if query:
                print(f"\n> User Query: {query}\n", flush=True)
                got_content, need_confirm, output_text = _stream_response(
                    message_handler, session, query,
                    output_mode=output_mode, output_dir=session_dir,
                    process_log_handler=None,  # In worker process, no process log handler needed for this path
                    is_attach=True  # Indicate this is an attach operation
                )

                # Check if the query was for confirmation and if there are more steps to process
                is_confirmation_query = query.strip() in ["确认执行", "confirm", "execute", "同意后续所有SQL执行"]

                # If the query was a confirmation, there might be more steps to execute
                if is_confirmation_query:
                    # After confirmation, the process has handled the confirmation
                    # The subsequent steps will be tracked by the server and can be viewed
                    # by attaching to the session again
                    print(f"\n[Worker] Confirmation processed. Subsequent steps will continue in the background.", flush=True)

                # Determine final status
                final_status = "waiting_input" if need_confirm else "completed"

                with open(session_dir / "status.txt", "w", encoding="utf-8") as f:
                    f.write(final_status)
                with open(session_dir / "result.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "status": final_status,
                        "session_id": session.session_id,
                    }, f, ensure_ascii=False, indent=2)

                return got_content, need_confirm
            else:
                # For attach without query, just monitor or replay
                from_start = getattr(args, "from_start", False)
                checkpoint = getattr(args, "checkpoint", None)

                # In worker process, we need to initialize components locally
                _config = DataAgentConfig.from_env()
                _client = DataAgentClient(_config)
                _sse_client = SSEClient(_config)
                _file_manager = FileManager(_client)

                _db_attach(_sse_client, _file_manager, session, from_start=from_start, checkpoint=checkpoint, output_mode=output_mode)

                return True, False  # got_content=True, need_confirm=False

        # Since the attach worker has complex setup logic that differs significantly from the other commands,
        # we'll just call the run_worker_with_handler without a data_source
        run_worker_with_handler(args, query_execution_func=attach_query_executor)

    else:
        # SYNCHRONOUS MODE (--no-async-run)
        print(f"Connecting to session: {session_id}")
        print(f"  Region: {config.region}")
        try:
            # First, try to get the session info to discover the actual agent_id
            # For some sessions, the API may not return the agent_id if an empty agent_id is provided
            # We need to try with empty agent_id first, and if it fails, we'll try the create_or_reuse approach
            session = None
            try:
                session = client.describe_session(agent_id="", session_id=session_id)

                # Special case: If we get CREATING status with no agent ID, this means the session doesn't actually exist
                # for the current user, but the API returns a default response. We should exit immediately.
                if not session.agent_id and session.status.value == "CREATING":
                    print(f"Error: Session {session_id} does not exist or does not belong to the current user.", file=sys.stderr)
                    sys.exit(1)

                # Only print session info if it passes the above check
                print(f"Initial session check - agent: '{session.agent_id}', status: {session.status.value}")

            except Exception as e:
                # This could be an authentication error or the session doesn't exist
                print(f"Error connecting to session: {e}", file=sys.stderr)
                print(f"This could be due to invalid credentials or the session doesn't exist.", file=sys.stderr)

                # If it's an authentication error, we should exit immediately
                from data_agent.exceptions import AuthenticationError
                if isinstance(e, AuthenticationError):
                    print(f"Authentication failed. Please check your credentials in .env file.", file=sys.stderr)
                    sys.exit(1)

                # For other errors, continue with fallback approaches
                print(f"Trying alternative methods to connect to session...", file=sys.stderr)

            # If session retrieval failed or agent_id is still empty, try using session manager
            if not session or not session.agent_id:
                print("Agent ID not found in session info, this may indicate the session doesn't exist or isn't ready yet.")

                # Check if the session exists but is still in CREATING state
                if session and session.status.value == "CREATING":
                    print("Session exists but is still being created. Waiting for it to be ready...")
                    # Since session is in CREATING state but no agent_id was returned,
                    # we need to wait until the agent_id becomes available
                    import time
                    max_retries = 10  # Reduce wait time (10*30 = 5 minutes max)
                    retry_count = 0

                    while retry_count < max_retries:
                        time.sleep(30)  # Wait 30 seconds between checks
                        try:
                            session = client.describe_session(agent_id="", session_id=session_id)
                            print(f"Checking session again - agent: '{session.agent_id}', status: {session.status.value}")

                            # If we now have an agent_id, break out of the loop
                            if session.agent_id:
                                print(f"Got agent ID: {session.agent_id}. Session is ready.")
                                break

                            # If status is no longer CREATING but we still don't have an agent_id,
                            # the session may have failed to create properly or doesn't belong to the user
                            if session.status.value != "CREATING":
                                print(f"Session status changed to {session.status.value} but still no agent ID.")
                                print(f"This may indicate the session does not belong to the current user.", file=sys.stderr)
                                break

                        except Exception as api_error:
                            print(f"Check session retry failed: {api_error}", file=sys.stderr)
                            from data_agent.exceptions import AuthenticationError
                            if isinstance(api_error, AuthenticationError):
                                print(f"Authentication failed. Please check your credentials in .env file.", file=sys.stderr)
                                sys.exit(1)

                        retry_count += 1

                    if not session.agent_id:
                        print(f"Session is still not ready after waiting. Status: {session.status.value if session else 'unknown'}", file=sys.stderr)
                        print(f"If status is not CREATING, this may mean the session does not belong to your account.", file=sys.stderr)

                if not session or not session.agent_id:
                    # At this point, if we still don't have an agent_id, the session either:
                    # 1. Does not exist
                    # 2. Does not belong to the current user
                    # 3. Is still being created but taking too long
                    # 4. Has been cancelled or failed to create properly
                    print(f"Error: Could not retrieve agent ID for session {session_id}.", file=sys.stderr)
                    print(f"This may mean the session does not exist, does not belong to your account,", file=sys.stderr)
                    print(f"is still being created (waited too long), or was cancelled/failed to create.", file=sys.stderr)
                    sys.exit(1)

            rid = f", request_id: {session.request_id}" if session.request_id else ""
            print(f"Session connected: {session.session_id} (agent: {session.agent_id}, status: {session.status.value}{rid})")

            # If status is CREATING and a query is provided, we need to wait for it to be ready
            # But for IDLE state, we can proceed without waiting since it's a valid state
            if session.status.value == "CREATING" and getattr(args, "query", None):
                print("Waiting for session to be ready...")
                session = session_manager.create_or_reuse(
                    session_id=session_id, agent_id=session.agent_id, wait_for_running=True,
                )
                rid = f", request_id: {session.request_id}" if session.request_id else ""
                print(f"Session ready: {session.session_id} (status: {session.status.value}{rid})")

        except Exception as e:
            print(f"Error: Failed to connect to session: {e}", file=sys.stderr)
            sys.exit(1)

        output_mode = getattr(args, "output", "summary")
        session_dir = Path(f"sessions/{session.session_id}")

        # Create process log handler for attach command
        with StructuredLogHandler(session_dir, log_prefix="process") as log_handler:
            # Log initial connection info
            log_text = f"Connected to session: {session.session_id} (agent: {session.agent_id}, status: {session.status.value})"
            log_handler.write_both(log_text + "\n")

            if args.query:
                query = args.query
                print(f"\n> User Query: {query}\n")

                # Log the query
                query_log = f"Processing query: {query}\n"
                log_handler.write_both(query_log)

                try:
                    got_content, need_confirm, _ = _stream_response(
                        message_handler, session, query,
                        output_mode=output_mode, output_dir=session_dir,
                        process_log_handler=log_handler,  # Pass the process log handler
                    is_attach=True  # Indicate this is an attach operation
                    )

                    # Check if the query was for confirmation and if there are more steps to process
                    is_confirmation_query = query.strip() in ["确认执行", "confirm", "execute", "同意后续所有SQL执行"]

                    # Log the response completion
                    response_log = f"Query processed, got_content: {got_content}, need_confirm: {need_confirm}, is_confirmation: {is_confirmation_query}\n"
                    log_handler.write_both(response_log)

                    if not got_content:
                        print("(No response received, please retry)")
                    elif need_confirm:
                        print("\n⚠️  Agent has created an execution plan. User confirmation required.")
                        print(f"   To continue: python3 scripts/data_agent_cli.py attach --session-id {session.session_id} -q 'your input'")
                    elif is_confirmation_query:
                        # After confirmation, continue monitoring for additional steps
                        print(f"\n[Sync mode] Post-confirmation: Monitoring for additional steps...")

                        # Refresh session to get the latest status
                        updated_session = client.describe_session(agent_id=session.agent_id, session_id=session.session_id)

                        # If session is still running after confirmation, continue monitoring
                        if updated_session.status.value in ["RUNNING", "WAIT_INPUT"]:
                            print(f"Session status after confirmation: {updated_session.status.value}")

                            # Continue to attach and monitor the session
                            print(f"\nContinuing to monitor session progress...")

                            # Use already imported _db_attach and initialized clients
                            _db_attach(sse_client, file_manager, updated_session, from_start=False, checkpoint=None, output_mode=output_mode)
                    else:
                        try:
                            updated_session = client.describe_session(agent_id=session.agent_id, session_id=session.session_id)
                            if updated_session.status.value == "WAIT_INPUT":
                                print("\n⚠️  Agent has created an execution plan and is waiting for confirmation.")
                                print("   Use -q option to confirm the plan or provide feedback:")
                                print(f"     python3 scripts/data_agent_cli.py attach --session-id {session.session_id} -q 'confirm'")
                                print(f"     python3 scripts/data_agent_cli.py attach --session-id {session.session_id} -q 'modify the plan'")
                        except Exception:
                            pass
                except Exception as e:
                    error_msg = f"Request failed: {e}"
                    print(error_msg)
                    log_handler.write_both(error_msg + "\n")
            else:
                from_start = getattr(args, "from_start", False)
                checkpoint = getattr(args, "checkpoint", None)

                # Log the attachment without query
                attach_log = f"Attaching to session without query (from_start: {from_start}, checkpoint: {checkpoint})\n"
                log_handler.write_both(attach_log)

                # Additional verification: if session agent_id is still empty, try to retrieve it directly
                if not session.agent_id:
                    print(f"No agent ID in current session object, attempting to refresh session info...", file=sys.stderr)
                    try:
                        # Try to get fresh session data directly from the API
                        refreshed_session = client.describe_session(agent_id="", session_id=session_id)
                        if refreshed_session.agent_id:
                            session = refreshed_session
                            print(f"Successfully retrieved agent ID: {refreshed_session.agent_id}")
                        else:
                            print(f"Error: Could not retrieve agent ID for session {session_id}. Session may not exist.", file=sys.stderr)
                            sys.exit(1)
                    except Exception as e:
                        print(f"Error retrieving session info: {e}", file=sys.stderr)
                        sys.exit(1)

                # Final check before calling _db_attach
                if not session.agent_id:
                    print(f"Error: Cannot attach to session {session_id} without a valid agent ID.", file=sys.stderr)
                    print(f"The session might not exist or may be corrupted.", file=sys.stderr)
                    sys.exit(1)

                _db_attach(sse_client, file_manager, session, from_start=from_start, checkpoint=checkpoint, output_mode=output_mode)
