#!/usr/bin/env python3
"""Send SLS DataAgent messages through the Aliyun CLI and return one JSON result."""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import uuid

from _chat.cli import TOTAL_TIMEOUT, decode_json, run_cli
from _chat.inputs import (InputError, load_json_file, load_session, parse_args,
                          read_input, resolve_target, save_session)
from _chat.protocol import Reply, encode_result, error, validate_context


def _cli_error(result, phase):
    """Normalize process errors without changing the protocol reducer."""
    if result.problem:
        code, message = result.problem
        return error("outcome_unknown" if result.started else "local_rejected",
                     code, message, phase if result.started else "submit")
    if result.returncode != 0:
        # The installed plugin only offers a human SDKError formatter on stderr.
        # Do not guess a business outcome from its prose, exit code, or labels.
        return error("outcome_unknown", "CLI_EXIT", "The CLI exited without a confirmed service result.", phase)
    return None


def _finish_result(reply, failure=None):
    """Assemble one result; aborted executions retain only known location/pending.

    Stream errors enter Reply before this call so its existing error priorities
    and confirmed artifacts apply. Local rejection/exception overrides do not.
    """
    if failure is None:
        result = reply.finish()
    else:
        result = {"status": "unknown" if failure["kind"] == "outcome_unknown" else "failed",
                  "error": failure}
    if reply is not None:
        for key, value in reply.identifiers.items():
            if value and key not in result:
                result[key] = value
        if reply.pending and "interactions" not in result:
            result["interactions"] = list(reply.pending.values())
    return result


def _interrupted(signum, frame):
    # selectors may retry InterruptedError as EINTR; KeyboardInterrupt escapes it.
    raise KeyboardInterrupt("local signal")


def _write_stderr(message):
    descriptor, was_blocking = None, False
    try:
        data = (message + "\n").encode("utf-8")
        descriptor = sys.stderr.fileno()
        was_blocking = os.get_blocking(descriptor)
        if was_blocking:
            os.set_blocking(descriptor, False)
        # Optional diagnostics must not wait for a stderr pipe consumer.
        os.write(descriptor, data)
    except (OSError, ValueError, AttributeError):
        # Diagnostics and optional progress must not decide the business outcome.
        pass
    finally:
        if was_blocking:
            try:
                os.set_blocking(descriptor, True)
            except OSError:
                pass


def _create_thread(target, reply, session_file, message_id, deadline, progress):
    """Create and record the thread; None means success, otherwise return its error."""
    if progress:
        progress("Creating a thread")
    created = run_cli("create-thread", target, ["--body", "{}"], deadline=deadline, progress=progress,
                      on_start=lambda: save_session(session_file, target, "creating_thread", message_id))
    failure = _cli_error(created, "submit")
    if failure is not None:
        return failure
    try:
        body = decode_json(created.body)
        thread_id = body.get("threadId") if isinstance(body, dict) else None
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ValueError("missing threadId")
        target["threadId"] = thread_id
        reply.identifiers["threadId"] = thread_id
        if progress:
            display_id = thread_id[:128] + ("…" if len(thread_id) > 128 else "")
            progress(f"Thread created (threadId={display_id!r})")
        save_session(session_file, target, "thread_created", message_id)
    except (ValueError, UnicodeError):
        return error("outcome_unknown", "INVALID_THREAD_RESPONSE",
                     "Thread creation did not return a valid thread identifier.", "submit")
    return None


def _chat_arguments(command, thread_id, message_id, request_input, variables=None):
    """Encode the validated text or interaction reply for its CLI action."""
    action = {"send": "create", "respond": "interact", "reconnect": "reconnect"}[command]
    arguments = ["--thread-id", thread_id, "--action", action]
    if command == "send":
        message = {"messageId": message_id, "role": "user",
                   "contents": [{"type": "text", "value": request_input}]}
        arguments += ["--messages", json.dumps([message], ensure_ascii=False, allow_nan=False)]
        if variables is not None:
            arguments += ["--variables", json.dumps(variables, ensure_ascii=False, allow_nan=False)]
    elif command == "respond":
        # The service creates the inbound message ID; never resubmit the old message.
        variables = {"userInteractive": json.dumps(request_input, ensure_ascii=False, allow_nan=False)}
        arguments += ["--variables", json.dumps(variables, ensure_ascii=False, allow_nan=False)]
    return arguments


def main(argv=None):
    target, reply, args = {}, None, None
    deadline = time.monotonic() + TOTAL_TIMEOUT
    message_id, may_submit = None, False
    result, failure = None, None
    previous_handler = signal.signal(signal.SIGTERM, _interrupted)
    try:
        args = parse_args(argv)
        session = load_session(args.session_file)
        context = load_json_file(args.context_file) if args.context_file else None
        target = resolve_target(args, session, context)
        pending, request_input = [], None
        if args.command == "respond":
            pending = validate_context(context)
        elif args.command == "send":
            if context and context.get("interactions"):
                raise InputError("PENDING_INTERACTIONS", "Known pending interactions require respond, not send.")
        elif context is not None:
            pending = validate_context(context)
        if args.command == "reconnect":
            message_id = (context or {}).get("messageId", session.get("messageId"))
        elif args.command == "send":
            request_input = read_input(args, sys.stdin, deadline=deadline)
            message_id = uuid.uuid4().hex
        reply = Reply(target.get("threadId"), message_id, pending, reconnect=args.command == "reconnect", target=target,
                      expected_root=session.get("callId") if args.command == "reconnect" else None)
        if args.command == "respond":
            # Establish the validated pending snapshot before result parsing so
            # even a local input rejection cannot silently discard known items.
            supplied = read_input(args, sys.stdin, deadline=deadline)
            request_input = encode_result(pending, supplied)
            reply.expect_response(pending[supplied["index"]], request_input)
        progress = _write_stderr if args.progress else None
        if "threadId" not in target:
            may_submit = True
            failure = _create_thread(target, reply, args.session_file, message_id, deadline, progress)
        if failure is None:
            arguments = _chat_arguments(args.command, target["threadId"], message_id, request_input, args.variables)
            if progress:
                progress({"send": "Sending a message", "respond": "Returning the interaction result",
                          "reconnect": "Reconnecting to receive output"}[args.command])
            may_submit = True
            recorded_root = None

            def consume(record):
                nonlocal recorded_root
                reply.feed(record)
                if reply.root_id and reply.root_id != recorded_root:
                    save_session(args.session_file, target, "receiving", message_id, reply.root_id)
                    recorded_root = reply.root_id

            execution = run_cli("create-chat", target, arguments, consume,
                                deadline=deadline, progress=progress,
                                on_start=lambda: save_session(args.session_file, target, "submitting", message_id,
                                                              reply.expected_root))
            failure = _cli_error(execution, "read_stream")
        if failure is not None and failure["kind"] == "outcome_unknown":
            # Preserve the first protocol error and root-conflict precedence.
            reply.unknown(failure["code"], failure["message"], failure["phase"])
            failure = None
        result = _finish_result(reply, failure)
        if failure is None:
            try:
                save_session(args.session_file, target, result["status"], message_id,
                             reply.root_id or reply.expected_root)
            except (InputError, OSError) as exc:
                # An optional location record cannot replace the established result.
                code = exc.code if isinstance(exc, InputError) else "SESSION_FILE_ERROR"
                _write_stderr("Final session record not saved (" + code + "); returned result retained.")
    except InputError as exc:
        kind = "outcome_unknown" if may_submit else "local_rejected"
        failure = error(kind, exc.code, exc.message, "execution" if may_submit else "validation")
        result = None
    except (KeyboardInterrupt, InterruptedError):
        failure = error("outcome_unknown" if may_submit else "local_rejected", "INTERRUPTED",
                        "Local execution was interrupted; this does not stop any remote turn.",
                        "read_stream" if may_submit else "validation")
        result = None
    except (OSError, ValueError, UnicodeError):
        failure = error("outcome_unknown" if may_submit else "local_rejected", "LOCAL_ERROR",
                        "A local input, encoding, or execution error prevented a confirmed result.",
                        "execution" if may_submit else "validation")
        result = None
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
    if result is None:
        result = _finish_result(reply, failure)
    try:
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    except (BrokenPipeError, OSError):
        return 1
    if result["status"] in ("completed", "interactive"):
        return 0
    return 2 if result["error"]["kind"] == "local_rejected" else 1


if __name__ == "__main__":
    sys.exit(main())
