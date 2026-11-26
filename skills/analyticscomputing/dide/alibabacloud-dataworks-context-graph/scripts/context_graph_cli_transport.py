"""Delegate allowlisted RPC calls to aliyun without exporting profile credentials."""

import json
import os
import re
import shutil
import subprocess

from context_graph_auth import CREDENTIAL_NAMES, credential_shape
from context_graph_contract import SkillError, endpoint_allowlist, parse_json, resolve_endpoint, validate_request
from context_graph_observability import user_agent


MINIMUM_CLI = (3, 3, 3)
MINIMUM_PLUGIN = (0, 9, 20)
PLUGIN_NAME = "aliyun-cli-dataworks-public"
COMMANDS = {
    "RetrieveKnowledgePoints": "retrieve-knowledge-points",
    "GetKnowledgePoint": "get-knowledge-point",
    "ListKnowledgePoints": "list-knowledge-points",
    "ListKnowledgeBases": "list-knowledge-bases",
    "GetKnowledgeBase": "get-knowledge-base",
}
OPTIONS = {
    "Query": "query", "KnowledgeBaseIds": "knowledge-base-ids", "FocusObjects": "focus-objects",
    "MaxResults": "max-results", "KnowledgeBaseId": "knowledge-base-id", "Type": "type",
    "Id": "id", "NextToken": "next-token",
}
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
CREDENTIAL_ALIASES = frozenset(
    prefix + suffix
    for prefix in ("ALIBABA_CLOUD_", "ALIBABACLOUD_", "ALICLOUD_", "")
    for suffix in ("ACCESS_KEY_ID", "ACCESS_KEY_SECRET", "SECURITY_TOKEN")
)
IGNORE_PROFILE = ("ALIBABA_CLOUD_IGNORE_PROFILE", "ALIBABACLOUD_IGNORE_PROFILE")


def validate_backend(backend, profile=None):
    if backend not in ("sdk", "aliyun"):
        raise SkillError("InvalidParameter", "Backend must be sdk or aliyun.")
    if profile is not None:
        if (backend != "aliyun" or not isinstance(profile, str) or not profile
                or len(profile) > 128 or profile.startswith("-")
                or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in profile)):
            raise SkillError("InvalidParameter", "Use a nonempty profile name only with the aliyun backend.")


def _run(arguments, environment, timeout):
    try:
        result = subprocess.run(arguments, env=environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8",
                                timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise SkillError("AliyunCliTimeout", "Aliyun CLI exceeded its local execution timeout.", retryable=True) from None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise SkillError("AliyunCliUnavailable", "Aliyun CLI could not execute or returned invalid text.") from None
    if sum(len(text.encode("utf-8")) for text in (result.stdout, result.stderr)) > MAX_OUTPUT_BYTES:
        raise SkillError("AliyunCliOutputTooLarge", "Aliyun CLI output exceeds the local size limit.")
    return result


def inspect_cli(environment):
    """Inspect version only, without resolving a profile or making a cloud call."""
    path = shutil.which("aliyun", path=environment.get("PATH", os.environ.get("PATH", os.defpath)))
    if path is None:
        raise SkillError("AliyunCliMissing", "Install aliyun CLI 3.3.3 or later in the 3.x series and expose it on PATH.")
    allowed = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "APPDATA",
               "LOCALAPPDATA", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL",
               "ALIBABA_CLOUD_CLI_PLUGINS_DIR"}
    probe_environment = {key: value for key, value in environment.items() if key in allowed}
    result = _run([path, "version"], probe_environment, 10)
    match = re.fullmatch(r"\s*(\d+)\.(\d+)\.(\d+)\s*", result.stdout)
    if result.returncode != 0 or match is None:
        raise SkillError("AliyunCliVersionUnsupported", "Cannot verify the installed aliyun CLI version.")
    version = tuple(map(int, match.groups()))
    if version[0] != 3 or version < MINIMUM_CLI:
        raise SkillError("AliyunCliVersionUnsupported", "Use aliyun CLI 3.3.3 or later in the 3.x series.")
    plugins = _run([path, "plugin", "list"], probe_environment, 10)
    installed = re.search(r"(?m)^aliyun-cli-dataworks-public\s+(\d+)\.(\d+)\.(\d+)(?=\s|$)", plugins.stdout)
    if plugins.returncode != 0 or installed is None:
        raise SkillError("AliyunCliPluginMissing", "Install the official dataworks-public plugin 0.9.20 or later; no legacy command fallback is allowed.")
    if tuple(map(int, installed.groups())) < MINIMUM_PLUGIN:
        raise SkillError("AliyunCliPluginUnsupported", "Update the official dataworks-public plugin to 0.9.20 or later.")
    return {"Path": path, "Version": ".".join(match.groups()), "Minimum": "3.3.3",
            "Plugin": {"Name": PLUGIN_NAME, "Version": ".".join(installed.groups()), "Minimum": "0.9.20"}}


def authentication_environment(environment, profile=None):
    """Select one identity source; explicit keys bypass all CLI profiles."""
    validate_backend("aliyun", profile)
    result = dict(environment)
    shape = credential_shape(environment)
    explicit_keys = profile is None and shape != "not_configured"
    if explicit_keys and shape != "configured":
        raise SkillError("CredentialsInvalid", "Provide complete valid injected credentials; no CLI profile fallback is allowed.")
    for name in CREDENTIAL_ALIASES | set(IGNORE_PROFILE):
        result.pop(name, None)
    result["ALIBABA_CLOUD_THROTTLING_RETRY_ENABLED"] = "false"
    result["ALIBABA_CLOUD_RETRY_COUNT"] = "0"
    result["ALIBABA_CLOUD_CONNECT_TIMEOUT"] = "10000"
    result["ALIBABA_CLOUD_READ_TIMEOUT"] = "65000"
    if explicit_keys:
        result.update({name: environment.get(name, "") for name in CREDENTIAL_NAMES})
        result["ALIBABA_CLOUD_IGNORE_PROFILE"] = "TRUE"
        mode = "StsToken" if environment.get("ALIBABA_CLOUD_SECURITY_TOKEN") else "AK"
    else:
        mode = None
    return result, mode


def _error_result(stdout, stderr):
    """Retain safe service metadata, never raw CLI diagnostics or profile contents."""
    for stream in (stdout, stderr):
        try:
            payload = parse_json(stream)
        except (SkillError, ValueError, TypeError, RecursionError):
            continue
        if isinstance(payload, dict):
            code = payload.get("Code", payload.get("error_code", payload.get("code")))
            request_id = payload.get("RequestId", payload.get("request_id"))
            if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,159}", code):
                if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", request_id):
                    request_id = None
                return SkillError(code, "Aliyun CLI reported an OpenAPI error; check the code and permissions.",
                                  request_id=request_id,
                                  retryable=code.lower().startswith(("throttl", "serviceunavailable")))
    # Older CLI versions print labeled SDK errors instead of a JSON envelope.
    for stream in (stderr, stdout):
        code = re.search(r"(?m)^\s*ErrorCode:\s*([A-Za-z][A-Za-z0-9_.:-]{0,159})\s*$", stream)
        request_id = re.search(r"(?m)^\s*RequestId:\s*([A-Za-z0-9_.:-]{1,160})\s*$", stream)
        if code:
            return SkillError(code[1], "Aliyun CLI reported an OpenAPI error; check the code and permissions.",
                              request_id=request_id[1] if request_id else None,
                              retryable=code[1].lower().startswith(("throttl", "serviceunavailable")))
    return SkillError("AliyunCliCommandFailed", "Aliyun CLI failed; check the selected profile, credentials, permissions, and network. No backend or identity fallback was attempted.")


class AliyunCliTransport:
    def __init__(self, region, *, environ=None, profile=None, endpoint=None, session_id=None):
        validate_backend("aliyun", profile)
        self.region = region
        environment = os.environ if environ is None else environ
        self.endpoint = resolve_endpoint(region, environment.get("DATAWORKS_ENDPOINT") if endpoint is None else endpoint,
                                         allowed_hosts=endpoint_allowlist(environment))
        self.attribution = user_agent(session_id)
        self.environment, self.mode = authentication_environment(environment, profile)
        self.profile = profile
        info = inspect_cli(self.environment)
        self.executable = info["Path"]
        self.version = tuple(map(int, info["Version"].split(".")))

    def arguments(self, action, parameters):
        parameters = validate_request(action, parameters)
        arguments = [self.executable, "dataworks-public", COMMANDS[action],
                     "--api-version", "2024-05-18", "--endpoint", self.endpoint,
                     "--region", self.region,
                     "--read-timeout", "65000", "--connect-timeout", "10000", "--retry-count", "0",
                     "--no-cli-ai-mode", "--user-agent", self.attribution]
        if self.mode is not None:
            arguments.extend(("--mode", self.mode))
        if self.profile is not None:
            arguments.extend(("--profile", self.profile))
        for name, value in parameters.items():
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, (list, dict)) else str(value)
            arguments.extend(("--" + OPTIONS[name], rendered))
        return arguments

    def call(self, action, parameters):
        result = _run(self.arguments(action, parameters), self.environment, 90)
        if result.returncode != 0:
            raise _error_result(result.stdout, result.stderr)
        try:
            return parse_json(result.stdout)
        except (SkillError, ValueError, TypeError, RecursionError):
            raise SkillError("InvalidResponse", "Aliyun CLI returned invalid JSON; no content or raw diagnostics were printed.") from None
