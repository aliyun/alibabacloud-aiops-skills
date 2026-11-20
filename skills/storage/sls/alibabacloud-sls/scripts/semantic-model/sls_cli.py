"""Read-only model transport through the configured Aliyun CLI."""

import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
from uuid import uuid4

from slsmodel.query import decode_model_rows

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "references" / "manifest.json"
SESSION_ID = uuid4().hex


class CLIError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}


def normalize_endpoint_host(value):
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        raise CLIError(
            "InvalidParameter", "Endpoint must not contain whitespace or control characters"
        )
    parsed = urlsplit(value if "://" in value else "https://" + value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or not re.fullmatch(r"[A-Za-z0-9.-]+(?::\d+)?", parsed.netloc)
    ):
        raise CLIError(
            "InvalidParameter",
            "Endpoint must be an HTTPS service host, without credentials or a path",
        )
    return parsed.netloc.lower()


def cli_environment():
    env = os.environ.copy()
    session = env.get("ALIBABA_CLOUD_SLS_SKILL_SESSION") or SESSION_ID
    env["ALIBABA_CLOUD_SLS_SKILL_SESSION"] = session
    if not env.get("ALIBABA_CLOUD_USER_AGENT"):
        version = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]
        env[
            "ALIBABA_CLOUD_USER_AGENT"
        ] = f"AlibabaCloud-Agent-Skills/alibabacloud-sls/{session} skill-version/{version}"
    return env


def command_error(process):
    payload = None
    for output in (process.stdout, process.stderr):
        try:
            candidate = json.loads(output)
        except (ValueError, TypeError):
            continue
        if isinstance(candidate, dict) and any(
            key in candidate for key in ("errorCode", "errorMessage", "error", "message", "code")
        ):
            payload = candidate
            break
    data = {"cliExitCode": process.returncode}
    if payload is None:
        return CLIError(
            "CLICommandFailed",
            process.stderr.strip()
            or process.stdout.strip()
            or "Aliyun CLI failed without diagnostic output",
            data,
        )
    nested = payload.get("error")
    details = nested if isinstance(nested, dict) else payload
    code = details.get("errorCode") or details.get("code") or "CLICommandFailed"
    message = details.get("errorMessage") or details.get("message")
    if not message and isinstance(nested, str):
        message = nested
    for source, target in (
        ("requestID", "requestId"),
        ("requestId", "requestId"),
        ("httpStatus", "httpStatus"),
    ):
        if source in payload:
            data[target] = payload[source]
        elif source in details:
            data[target] = details[source]
    if process.stderr.strip():
        data["stderr"] = process.stderr.strip()
    return CLIError(str(code), str(message or "Aliyun CLI model request failed"), data)


class SLSModelCLI:
    def __init__(self, endpoint=None, region=None, timeout=60, profile=None):
        if region is not None and not re.fullmatch(r"[a-z0-9-]+", region):
            raise CLIError("InvalidParameter", "Invalid SLS region")
        self.endpoint = normalize_endpoint_host(endpoint) if endpoint else None
        self.region = region
        self.timeout = timeout
        self.profile = profile

    def query_context_model(self, name, spl):
        if not isinstance(name, str) or not name:
            raise CLIError("InvalidParameter", "Context Model query requires a model name")
        return self._query(["context-model", "query", "--name=" + name], spl)

    def query_source_model(self, project, spl):
        return self._query(self._source_arguments(project, "query"), spl)

    def get_source_model_status(self, project):
        return self._run(self._source_arguments(project, "status"))

    @staticmethod
    def _source_arguments(project, operation):
        if not isinstance(project, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", project):
            raise CLIError("InvalidParameter", "Invalid SLS project name")
        return ["source-model", operation, "--project=" + project, "--disable-cross-region"]

    def _query(self, arguments, spl):
        if not isinstance(spl, str):
            raise CLIError("InvalidParameter", "Model query requires SPL text")
        # Stdin preserves long SPL and avoids shell quoting or command substitution.
        return decode_model_rows(self._run([*arguments, "--query-file=-"], spl))

    def _run(self, arguments, spl=""):
        for name in ("profile", "region", "endpoint"):
            value = getattr(self, name)
            if value is not None:
                arguments.append(f"--{name}={value}")
        try:
            process = subprocess.run(
                ["aliyun", "sls", *arguments, "--format=json", "--log-level=ERROR"],
                input=spl,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                timeout=self.timeout,
                env=cli_environment(),
            )
        except FileNotFoundError:
            raise CLIError(
                "MissingDependency",
                "Install Aliyun CLI and the SLS plugin; aliyun was not found on PATH",
            ) from None
        except subprocess.TimeoutExpired:
            raise CLIError(
                "CLITimeout",
                "Aliyun CLI model request exceeded --timeout; execution completion is unconfirmed",
            ) from None
        if process.returncode != 0:
            raise command_error(process)
        try:
            result = json.loads(process.stdout)
        except ValueError:
            raise CLIError(
                "InvalidResponse", "Aliyun CLI returned invalid JSON for the model request"
            ) from None
        if not isinstance(result, dict):
            raise CLIError("InvalidResponse", "Aliyun CLI model response must be a JSON object")
        if result.get("success") is False:
            raise command_error(process)
        return result
