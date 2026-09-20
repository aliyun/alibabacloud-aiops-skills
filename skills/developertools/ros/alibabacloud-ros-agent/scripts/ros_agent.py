#!/usr/bin/env python3
# ruff: noqa: F401,F821 -- source shards execute in this shared namespace.
"""Bounded Alibaba Cloud ROS Agent bridge using signed StartChat RPCs."""

import argparse
import contextlib
import errno
import hashlib
import importlib
import json
import os
import pathlib
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

MAX_PROMPT_BYTES = 1024 * 1024
MAX_CONTEXT_BYTES = 64 * 1024
MAX_CONFIG_BYTES = 16 * 1024
MAX_CLI_CONFIG_BYTES = 2 * 1024 * 1024
MAX_PLUGIN_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_SSE_LINE_BYTES = 16 * 1024 * 1024
MAX_SSE_EVENT_BYTES = 16 * 1024 * 1024
MAX_SERVER_REPLAY_BYTES = 64 * 1024 * 1024
# A JSON wrapper can expand a server event through escaping. This is a parser
# bound, not a claim about the as-yet unpublished remote executor contract.
MAX_CLI_BATCH_BYTES = (6 * MAX_SERVER_REPLAY_BYTES) + (1024 * 1024)
MAX_FINAL_TEXT_BYTES = 10 * 1024
MAX_DIAGNOSTIC_BYTES = 64 * 1024
MAX_RESULT_BYTES = 32 * 1024
MAX_SPOOL_BYTES = 8 * 1024 * 1024
MAX_PROJECTION_BYTES = 4096
MAX_INPUT_PROJECTION_BYTES = 14 * 1024
MAX_FOLLOW_BYTES = 16 * 1024
MAX_FOLLOW_EVENTS = 16
MAX_STEP_CONCLUSION_BYTES = 1800
MAX_MANAGER_REQUEST_BYTES = 2 * 1024 * 1024
DEFAULT_FOLLOW_SECONDS = 60.0
MAX_FOLLOW_SECONDS = 120.0
DEFAULT_READ_TIMEOUT_SECONDS = 1800
MANAGER_START_TIMEOUT_SECONDS = 10.0
STOP_SESSION_WAIT_SECONDS = 10.0
STOP_REQUEST_TIMEOUT_SECONDS = 60.0
MAX_RECONNECT_BACKOFF_SECONDS = 5.0
MANAGER_IDLE_SECONDS = 60
MAX_MANAGER_IDLE_SECONDS = 24 * 60 * 60
MANAGER_SCHEMA_VERSION = 3
JOB_SCHEMA_VERSION = 1
STATE_DIR_ENV = "ALICLOUD_ROS_AGENT_STATE_DIR"
MAX_ATTACHMENTS = 5
DEFAULT_ENDPOINT = "ros.aliyuncs.com"
SUPPORTED_AGENT_MODES = {"normal", "pipeline"}
DEFAULT_TRANSPORT = "code"
SUPPORTED_TRANSPORTS = {"code", "aliyun_cli"}
DEFAULT_ALIYUN_CLI_EXECUTION_MODE = "local"
SUPPORTED_ALIYUN_CLI_EXECUTION_MODES = {"local", "remote"}
ROS_PLUGIN_COMMANDS = {"start-chat", "stop-chat"}
DEFAULT_REMOTE_CLI_FORWARD_ENV = ()  # type: Tuple[str, ...]
MAX_REMOTE_CLI_FORWARD_ENV_NAMES = 16
MAX_REMOTE_CLI_ENV_VALUE_BYTES = 16 * 1024
MAX_REMOTE_CLI_ENV_BYTES = 64 * 1024
SKILL_DISTRIBUTION = "agenthub"
SKILL_NAME = "alibabacloud-ros-agent"
SKILL_MANIFEST_PATH = pathlib.Path(__file__).resolve().parent.parent / "references" / "manifest.json"
USER_AGENT_TEMPLATE = (
    "AlibabaCloud-Agent-Skills/alibabacloud-ros-agent/{session-id} skill-version/{skill-version}"
)
REQUIREMENTS_FILE = "scripts/requirements.txt"
REMOTE_EXECUTOR_VERSION_ENV = "ALICLOUD_ROS_AGENT_EXECUTOR_VERSION"
REMOTE_EXECUTOR_CAPABILITIES_ENV = "ALICLOUD_ROS_AGENT_EXECUTOR_CAPABILITIES"
MIN_ROS_PLUGIN_VERSION = (0, 9, 1)
REMOTE_BOOTSTRAP_CAPABILITY = "startchat-reconnect-bootstrap-v1"
REMOTE_BOOTSTRAP_INVOCATION_ENV = "ALICLOUD_ROS_AGENT_INVOCATION_ID"
REMOTE_BOOTSTRAP_ACK_FILE_ENV = "ALICLOUD_ROS_AGENT_BOOTSTRAP_ACK_FILE"
REMOTE_BOOTSTRAP_PROTOCOL_ENV = "ALICLOUD_ROS_AGENT_BOOTSTRAP_PROTOCOL"


def _skill_version() -> str:
    try:
        with SKILL_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeError(
            "invalid_skill_manifest",
            "The AgentHub Skill manifest is unavailable or invalid.",
        ) from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise BridgeError(
            "invalid_skill_manifest",
            "The AgentHub Skill manifest does not contain a valid version.",
        )
    return version.strip()


def _skill_user_agent(session_id: str) -> str:
    if SKILL_DISTRIBUTION != "agenthub":
        return USER_AGENT_TEMPLATE
    if re.fullmatch(r"[0-9a-f]{32}", session_id) is None:
        raise BridgeError("invalid_skill_session", "The AgentHub Skill session identifier is invalid.")
    return USER_AGENT_TEMPLATE.replace("{session-id}", session_id).replace("{skill-version}", _skill_version())
PROFILE_ENV_NAMES = (
    "ALIBABACLOUD_PROFILE",
    "ALIBABA_CLOUD_PROFILE",
    "ALICLOUD_PROFILE",
)
REGION_ENV_NAMES = (
    "ALIBABA_CLOUD_REGION_ID",
    "ALIBABACLOUD_REGION_ID",
    "ALICLOUD_REGION_ID",
    "REGION_ID",
    "REGION",
)
SKILL_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config.json"
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
PERMISSION_DECISIONS = {"allow_once", "deny"}
PERMISSION_QUERY_PREFIX = "IAC_CODE_PERMISSION:"
SESSION_BACKUP_NOT_READY_CODE = "SESSION_BACKUP_NOT_READY"
TERMINAL_STATES = {"completed", "failed", "canceled", "rejected"}
PIPELINE_EVENT_TYPES = {
    "pipeline_started",
    "pipeline_resumed",
    "step_started",
    "step_completed",
    "step_failed",
    "candidate_started",
    "candidate_step_started",
    "candidate_step_completed",
    "candidate_step_failed",
    "candidate_completed",
    "candidate_selected",
    "input_required",
    "pipeline_completed",
    "pipeline_failed",
    "pipeline_canceled",
    "cleanup_started",
    "cleanup_progress",
    "cleanup_completed",
    "cleanup_failed",
}
STEP_BOUNDARY_EVENT_TYPES = {
    "step_started",
    "step_completed",
    "step_failed",
    "candidate_step_started",
    "candidate_step_completed",
    "candidate_step_failed",
}
SECRET_PATTERN = re.compile(
    r"(?i)((?:[\"']?)(?:access[-_ ]?key(?:[-_ ]?id|[-_ ]?secret)?|security[-_ ]?token|signature|"
    r"authorization)(?:[\"']?)\s*[:=]\s*(?:[\"']?)(?:bearer\s+)?)([^\"'\s,;&}]+)"
)
SENSITIVE_CLIENT_CONTEXT_KEY_PARTS = (
    "accesskey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "profile",
    "secret",
    "signature",
    "token",
)
SENSITIVE_ENV_NAME_PARTS = (
    "accesskey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "privatekey",
    "secret",
    "signature",
    "token",
)



_SOURCE_SHARDS = (
    "_ros_agent_core.py",
    "_ros_agent_projection.py",
    "_ros_agent_runtime.py",
)


def _load_source_shard(filename: str) -> None:
    path = pathlib.Path(__file__).resolve().with_name(filename)
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise RuntimeError("The ROS Agent bridge source shard is unavailable: {}".format(filename)) from exc
    if len(source) > 128 * 1024:
        raise RuntimeError("The ROS Agent bridge source shard exceeds the 128 KiB limit: {}".format(filename))
    exec(compile(source, str(path), "exec"), globals())


for _source_shard in _SOURCE_SHARDS:
    _load_source_shard(_source_shard)
del _source_shard


if __name__ == "__main__":
    sys.exit(main())
