"""Notification utilities for pushing updates to Clawdbot / OpenClaw sessions.

Author: Tinker
Created: 2026-03-11
"""

import os
import json
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError


def get_active_session() -> str:
    """Get the active OpenClaw / Clawdbot session ID."""
    print("[Notify] Trying to determine active session...", flush=True)
    # 1. Environment variables
    session = os.environ.get("OPENCLAW_SESSION") or os.environ.get("CLAWDBOT_PUSH_SESSION")
    if session:
        print(f"[Notify] Found session from environment: {session}", flush=True)
        return session

    # 2. Try CLI
    cli_cmd = None
    for cmd in ["openclaw", "clawdbot"]:
        try:
            subprocess.run(["which", cmd], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cli_cmd = cmd
            print(f"[Notify] Found CLI: {cli_cmd}", flush=True)
            break
        except subprocess.CalledProcessError:
            continue

    if not cli_cmd:
        print("[Notify] No CLI found (openclaw or clawdbot).", flush=True)
        return ""

    try:
        print(f"[Notify] Running: {cli_cmd} sessions --active 5 --json", flush=True)
        result = subprocess.run(
            [cli_cmd, "sessions", "--active", "5", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            sessions = data.get("sessions", [])
            if sessions and sessions[0].get("key"):
                key = sessions[0]["key"]
                # Handle "webchat:xxx" format
                session_key = key.split(":")[-1] if ":" in key else key
                print(f"[Notify] Found session from CLI: {session_key}", flush=True)
                return session_key
            else:
                print("[Notify] CLI returned success but no active sessions found.", flush=True)
        else:
            print(f"[Notify] CLI command failed. Return code: {result.returncode}, Stderr: {result.stderr}", flush=True)
    except Exception as e:
        print(f"[Notify] Exception running CLI to get session: {e}", flush=True)

    return ""


def push_notification(session_id: str, message: str) -> bool:
    """Push a notification message to the specified session or active session.

    Args:
        session_id: The target session ID (optional).
        message: The message content to push.

    Returns:
        True if successful, False otherwise.
    """
    print(f"\n[Notify] Starting push notification... Target session_id: {session_id}", flush=True)
    custom_url = os.environ.get("ASYNC_TASK_PUSH_URL")

    # 1. Custom HTTP push
    if custom_url:
        print(f"[Notify] ASYNC_TASK_PUSH_URL is set: {custom_url}", flush=True)
        token = os.environ.get("ASYNC_TASK_AUTH_TOKEN", "")
        data = json.dumps({
            "sessionId": session_id,
            "content": message,
            "role": "assistant"
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(data))
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = Request(custom_url, data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=10) as response:
                success = response.status >= 200 and response.status < 300
                print(f"[Notify] HTTP push result: status={response.status}, success={success}", flush=True)
                return success
        except URLError as e:
            print(f"[Notify] HTTP push failed with URLError: {e}", flush=True)
            return False

    # 2. CLI push
    print("[Notify] Falling back to CLI push...", flush=True)
    target_session = session_id or get_active_session()
    if not target_session:
        print("[Notify] Aborting push: No target session available.", flush=True)
        return False

    cli_cmd = None
    for cmd in ["openclaw", "clawdbot"]:
        try:
            subprocess.run(["which", cmd], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cli_cmd = cmd
            print(f"[Notify] Found CLI for push: {cli_cmd}", flush=True)
            break
        except subprocess.CalledProcessError:
            continue

    if not cli_cmd:
        print("[Notify] Aborting push: No CLI found.", flush=True)
        return False

    cmd_args = [cli_cmd, "sessions", "send", "--session", target_session, message]
    print(f"[Notify] Executing: {' '.join(cmd_args)}", flush=True)
    try:
        result = subprocess.run(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            text=True
        )
        success = result.returncode == 0
        if success:
            print("[Notify] CLI push succeeded.", flush=True)
        else:
            print(f"[Notify] CLI push failed. Return code: {result.returncode}, Stderr: {result.stderr}", flush=True)
        return success
    except Exception as e:
        print(f"[Notify] Exception running CLI push: {e}", flush=True)
        return False
