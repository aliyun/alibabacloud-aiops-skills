"""The Aliyun process boundary. No retries, history queries, or server cancellation."""
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass

from _skill_user_agent import AttributionError, user_agent
from .inputs import InputError, parse_json


MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_DIAGNOSTIC_BYTES = 64 * 1024
TOTAL_TIMEOUT = 240.0
IDLE_TIMEOUT = 60.0


@dataclass
class CLIResult:
    started: bool = False
    returncode: int | None = None
    body: bytes = b""
    stderr: str = ""
    problem: tuple[str, str] | None = None


def command(operation, target, arguments):
    argv = ["aliyun", "sls", operation]
    for key in ("name", "region", "profile", "endpoint"):
        if key in target:
            argv.extend(("--" + key, target[key]))
    return argv + list(arguments) + ["--log-level", "ERROR", "--retry-count", "0",
                                    "--user-agent", user_agent(), "--no-cli-ai-mode"]


def _stop_local(process):
    """Reap the whole local process group; this does not stop the remote turn."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            continue


def decode_json(line):
    try:
        return parse_json(line.decode("utf-8"))
    except InputError as exc:
        raise ValueError("invalid CLI JSON") from exc

def run_cli(operation, target, arguments, on_record=None, *, deadline=None,
            idle_timeout=IDLE_TIMEOUT, progress=None, on_start=None):
    """Drain both pipes incrementally, retaining one record and bounded diagnostics.

    A caller can share an absolute deadline across thread creation and chat.
    on_record consumes CLI JSON envelopes, never raw network SSE frames.
    """
    result = CLIResult()
    deadline = time.monotonic() + TOTAL_TIMEOUT if deadline is None else deadline
    if time.monotonic() >= deadline:
        result.problem = ("DEADLINE_EXCEEDED", "The execution deadline was reached.")
        return result
    try:
        environment = os.environ.copy()
        environment.pop("ALIBABA_CLOUD_USER_AGENT", None)
        environment["ALIBABA_CLOUD_THROTTLING_RETRY_ENABLED"] = "false"
        process = subprocess.Popen(command(operation, target, arguments), env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
    except AttributionError as exc:
        result.problem = ("INVALID_SKILL_ATTRIBUTION", str(exc))
        return result
    except OSError:
        result.problem = ("CLI_START_FAILED", "Unable to start the Aliyun CLI.")
        return result
    result.started = True
    pending, diagnostic = bytearray(), bytearray()
    started_at = last_output = last_notice = time.monotonic()
    received_output = False

    def consume_record(line):
        nonlocal received_output
        on_record(decode_json(line))
        if progress and not received_output:
            progress("Receiving output")
            received_output = True

    try:
        if on_start:
            on_start()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                now = time.monotonic()
                if now >= deadline:
                    result.problem = ("DEADLINE_EXCEEDED", "The execution deadline was reached; remote outcome is unconfirmed.")
                    break
                if now - last_output >= idle_timeout:
                    result.problem = ("READ_TIMEOUT", "CLI output timed out; remote outcome is unconfirmed.")
                    break
                if progress and now - last_notice >= 15:
                    progress(f"Still waiting for the current stage (elapsed: {int(now - started_at)} seconds)")
                    last_notice = now
                    continue  # Recheck budgets after optional reporting.
                ready = selector.select(min(0.2, deadline - now, idle_timeout - (now - last_output)))
                for key, _ in ready:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == "stderr":
                        diagnostic.extend(chunk)
                        del diagnostic[:-MAX_DIAGNOSTIC_BYTES]
                        continue
                    last_output = time.monotonic()
                    pending.extend(chunk)
                    if on_record is not None:
                        while b"\n" in pending:
                            line, _, remainder = pending.partition(b"\n")
                            pending = bytearray(remainder)
                            if len(line) > MAX_RECORD_BYTES:
                                raise ValueError("CLI record too large")
                            if line.strip():
                                consume_record(line)
                    if len(pending) > MAX_RECORD_BYTES:
                        raise ValueError("CLI record too large")
            if result.problem is None:
                if on_record is not None and pending.strip():
                    consume_record(pending)
                elif on_record is None:
                    result.body = bytes(pending)
                try:
                    remaining = min(deadline - time.monotonic(), idle_timeout - (time.monotonic() - last_output))
                    result.returncode = process.wait(timeout=max(0.001, remaining))
                except subprocess.TimeoutExpired:
                    code = "DEADLINE_EXCEEDED" if time.monotonic() >= deadline else "READ_TIMEOUT"
                    result.problem = (code, "The CLI did not exit before the execution budget was reached.")
    except (ValueError, UnicodeError):
        result.problem = ("INVALID_CLI_OUTPUT", "CLI output is not a valid, bounded JSON event stream.")
    except (KeyboardInterrupt, InterruptedError):
        result.problem = ("INTERRUPTED", "Local reading was interrupted; the remote turn may still be running.")
    except OSError:
        result.problem = ("CLI_IO_ERROR", "Unable to read the CLI output; remote outcome is unconfirmed.")
    finally:
        if result.problem is not None or process.poll() is None:
            _stop_local(process)
        result.returncode = process.returncode
        process.stdout.close()
        process.stderr.close()
        result.stderr = diagnostic.decode("utf-8", "replace")
    return result
