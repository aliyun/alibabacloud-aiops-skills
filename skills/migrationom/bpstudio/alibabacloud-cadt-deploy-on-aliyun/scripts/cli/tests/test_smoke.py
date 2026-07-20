"""Smoke tests — Phase 0 verifies the dispatcher skeleton works without
any aliyun CLI dependency. These run in pure CPython.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CADT = os.path.join(ROOT, "cadt_deploy_on_aliyun.py")
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VERSION_FILE = os.path.join(PROJECT_ROOT, "VERSION")


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, CADT, *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.stdout.strip(), f"empty stdout, stderr={proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_version():
    env = _run("-version")
    assert env["ok"] is True
    assert env["data"]["ops_count"] == 7


def test_list():
    env = _run("-l")
    assert env["ok"] is True
    assert env["data"]["total"] == 7
    names = [op["name"] for op in env["data"]["operations"]]
    assert "InstallApplication" in names
    assert "EcsRunCommand" in names


def test_list_filter():
    env = _run("-l", "--category=deploy")
    assert env["ok"] is True
    for op in env["data"]["operations"]:
        assert op["category"] == "deploy"


def test_describe():
    env = _run("-d", "InstallApplication")
    assert env["ok"] is True
    spec = env["data"]
    assert spec["name"] == "InstallApplication"
    assert "input_schema" in spec
    assert "output_schema" in spec


def test_describe_unknown_op():
    env = _run("-d", "DoesNotExist")
    assert env["ok"] is False
    assert env["error"]["code"] == "OP_NOT_FOUND"
    assert "fixHint" in env["error"]


def test_run_invalid_json():
    env = _run("-run", "InstallApplication", "not-json")
    assert env["ok"] is False
    assert env["error"]["code"] == "VALIDATION_FAILED"


def test_run_flag_style_input_detected():
    """--key value style should be rejected with a clear message, not a generic JSON error."""
    env = _run("-run", "InstallApplication", "--regionId", "cn-hangzhou")
    assert env["ok"] is False
    assert env["error"]["code"] == "VALIDATION_FAILED"
    assert "does not support --key value" in env["error"]["message"].lower() or \
           "does not support" in env["error"]["message"]
    assert "JSON" in env["error"]["fixHint"] or "json" in env["error"]["fixHint"].lower()


def test_run_unknown_op():
    env = _run("-run", "DoesNotExist", "{}")
    assert env["ok"] is False
    assert env["error"]["code"] == "OP_NOT_FOUND"


def test_unknown_subcommand():
    proc = subprocess.run(
        [sys.executable, CADT, "-banana"],
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout.strip())
    assert payload["ok"] is False
    assert payload["error"]["code"] == "CADT_INTERNAL"


def test_doctor_runs():
    env = _run("-doctor")
    assert "ok" in env
    assert "checks" in env["data"]
    assert any(c["name"] == "python>=3.9" for c in env["data"]["checks"])
    assert any(c["name"] == "ops_source" for c in env["data"]["checks"])



# ---------------------------------------------------------------------------
# CICD ops validation
# ---------------------------------------------------------------------------

EXPECTED_OPS = {
    "InstallApplication",
    "EcsGetDesc", "EcsGetDescList",
    "EcsRunCommandSync",
}

IMPORTED_OPS = {
    "EcsRunCommand", "EcsSendFile", "OssGeneratePresignedUrl",
}


def test_list_has_primary_ops():
    env = _run("-l", "--source=deploy")
    names = {op["name"] for op in env["data"]["operations"]}
    assert EXPECTED_OPS == names
    assert env["data"]["total"] == 4


def test_list_has_all_ops():
    env = _run("-l")
    names = {op["name"] for op in env["data"]["operations"]}
    assert EXPECTED_OPS | IMPORTED_OPS == names
    assert env["data"]["total"] == 7


def test_describe_install_application():
    env = _run("-d", "InstallApplication")
    spec = env["data"]
    assert spec["name"] == "InstallApplication"
    assert spec["exec_mode"] == "async"
    assert "regionId" in spec["input_schema"]["required"]
    assert "instanceIds" in spec["input_schema"]["required"]
    assert "appName" in spec["input_schema"]["required"]
    assert "artifactUrl" in spec["input_schema"]["properties"]
    assert "filePath" in spec["input_schema"]["properties"]


# ---------------------------------------------------------------------------
# instanceIds CSV coercion (x-coerce: "csv")
# Regression: agent passing instanceIds as JSON array ["i-bp1xxx"] caused
# backend TagResource 404 because coerce_string_fields JSON-encoded the list
# to '["i-bp1xxx"]' (with brackets) instead of comma-separated "i-bp1xxx".
# ---------------------------------------------------------------------------

def test_instance_ids_list_normalized_to_csv():
    """InstallApplication instanceIds as list → comma-separated string."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields
    from lib.manifest import load_op

    spec = load_op("InstallApplication")
    schema = spec["input_schema"]

    args = {"instanceIds": ["i-bp1xxx"]}
    coerce_string_fields(args, schema)
    assert args["instanceIds"] == "i-bp1xxx"

    args = {"instanceIds": ["i-bp1xxx", "i-bp2yyy"]}
    coerce_string_fields(args, schema)
    assert args["instanceIds"] == "i-bp1xxx,i-bp2yyy"


def test_instance_ids_json_array_string_normalized_to_csv():
    """InstallApplication instanceIds as JSON-array string → comma-separated."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields
    from lib.manifest import load_op

    spec = load_op("InstallApplication")
    schema = spec["input_schema"]

    args = {"instanceIds": '["i-bp1xxx"]'}
    coerce_string_fields(args, schema)
    assert args["instanceIds"] == "i-bp1xxx"

    args = {"instanceIds": '["i-bp1xxx","i-bp2yyy"]'}
    coerce_string_fields(args, schema)
    assert args["instanceIds"] == "i-bp1xxx,i-bp2yyy"


def test_instance_ids_plain_string_unchanged():
    """InstallApplication instanceIds as plain CSV string → unchanged."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields
    from lib.manifest import load_op

    spec = load_op("InstallApplication")
    schema = spec["input_schema"]

    args = {"instanceIds": "i-bp1xxx"}
    coerce_string_fields(args, schema)
    assert args["instanceIds"] == "i-bp1xxx"

    args = {"instanceIds": "i-bp1xxx,i-bp2yyy"}
    coerce_string_fields(args, schema)
    assert args["instanceIds"] == "i-bp1xxx,i-bp2yyy"


def test_non_csv_string_field_dict_still_json_encoded():
    """Non-csv string fields still JSON-encode dict values (no regression)."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields

    schema = {
        "type": "object",
        "properties": {
            "config": {"type": "string"},
        },
    }
    args = {"config": {"key": "value"}}
    coerce_string_fields(args, schema)
    assert args["config"] == '{"key":"value"}'


def test_imported_ops_present():
    """Verify imported migrate-owned ops ARE in this skill for independence."""
    env = _run("-l", "--source=migrate")
    names = {op["name"] for op in env["data"]["operations"]}
    assert IMPORTED_OPS == names
    assert env["data"]["total"] == 3
    for op in env["data"]["operations"]:
        assert op.get("source") == "migrate"


# ---------------------------------------------------------------------------
# Deprecated alias normalization (x-deprecated-aliases)
# ---------------------------------------------------------------------------

def test_ecs_run_command_schema_has_instance_ids_only():
    """EcsRunCommand schema should only expose instanceIds (array), not instanceId."""
    env = _run("-d", "EcsRunCommand")
    spec = env["data"]
    props = spec["input_schema"]["properties"]
    assert "instanceIds" in props
    assert "instanceId" not in props
    assert props["instanceIds"]["type"] == "array"
    assert "instanceIds" in spec["input_schema"]["required"]


def test_ecs_run_command_deprecated_instance_id_normalized():
    """Passing deprecated instanceId (string) should be auto-normalized to instanceIds."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields
    from lib.manifest import load_op

    spec = load_op("EcsRunCommand")
    schema = spec["input_schema"]

    args = {"instanceId": "i-xxx", "command": "echo hi"}
    coerce_string_fields(args, schema)
    assert "instanceId" not in args
    assert args["instanceIds"] == ["i-xxx"]


def test_ecs_run_command_deprecated_instance_id_array_normalized():
    """Passing deprecated instanceId (array) should be auto-normalized to instanceIds."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields
    from lib.manifest import load_op

    spec = load_op("EcsRunCommand")
    schema = spec["input_schema"]

    args = {"instanceId": ["i-xxx", "i-yyy"], "command": "echo hi"}
    coerce_string_fields(args, schema)
    assert "instanceId" not in args
    assert args["instanceIds"] == ["i-xxx", "i-yyy"]


def test_ecs_send_file_schema_has_instance_ids_only():
    """EcsSendFile schema should only expose instanceIds (array), not instanceId."""
    env = _run("-d", "EcsSendFile")
    spec = env["data"]
    props = spec["input_schema"]["properties"]
    assert "instanceIds" in props
    assert "instanceId" not in props
    assert props["instanceIds"]["type"] == "array"
    assert "instanceIds" in spec["input_schema"]["required"]


def test_ecs_send_file_deprecated_instance_id_normalized():
    """Passing deprecated instanceId (string) should be auto-normalized to instanceIds."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    from lib.attrs import coerce_string_fields
    from lib.manifest import load_op

    spec = load_op("EcsSendFile")
    schema = spec["input_schema"]

    args = {"instanceId": "i-xxx", "name": "test.sh", "content": "echo hi", "targetDir": "/tmp"}
    coerce_string_fields(args, schema)
    assert "instanceId" not in args
    assert args["instanceIds"] == ["i-xxx"]


# ---------------------------------------------------------------------------
# --user-agent / session-id injection
# ---------------------------------------------------------------------------
import importlib.util
_spec = importlib.util.spec_from_file_location("cadt_main", CADT)
_cadt_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cadt_main)
_inject_session_id = _cadt_main._inject_session_id


def test_inject_session_id_equals_form():
    os.environ.pop("SKILL_SESSION_ID", None)
    _inject_session_id(["--user-agent=AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/abc123"])
    assert os.environ.get("SKILL_SESSION_ID") == "abc123"
    os.environ.pop("SKILL_SESSION_ID", None)


def test_inject_session_id_space_form():
    os.environ.pop("SKILL_SESSION_ID", None)
    _inject_session_id(["--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/deadbeef"])
    assert os.environ.get("SKILL_SESSION_ID") == "deadbeef"
    os.environ.pop("SKILL_SESSION_ID", None)


def test_inject_session_id_env_takes_precedence():
    os.environ["SKILL_SESSION_ID"] = "from-env"
    _inject_session_id(["--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/from-flag"])
    assert os.environ.get("SKILL_SESSION_ID") == "from-env"
    os.environ.pop("SKILL_SESSION_ID", None)


def test_inject_session_id_no_flag():
    os.environ.pop("SKILL_SESSION_ID", None)
    _inject_session_id(["--timeout=300"])
    assert os.environ.get("SKILL_SESSION_ID") is None
    os.environ.pop("SKILL_SESSION_ID", None)


# ---------------------------------------------------------------------------
# _parse_flags
# ---------------------------------------------------------------------------
_parse_flags = _cadt_main._parse_flags


def test_parse_flags_equals_form():
    result = _parse_flags(["--timeout=120"], allowed={"timeout"})
    assert result == {"timeout": "120"}


def test_parse_flags_space_form():
    result = _parse_flags(["--timeout", "120"], allowed={"timeout"})
    assert result == {"timeout": "120"}


def test_parse_flags_mixed_forms():
    result = _parse_flags(["--timeout", "60", "--command-file=path/to/file"],
                          allowed={"timeout", "command-file"})
    assert result == {"timeout": "60", "command-file": "path/to/file"}


def test_parse_flags_boolean_flag():
    result = _parse_flags(["--timeout"], allowed={"timeout"})
    assert result == {"timeout": "true"}


def test_parse_flags_boolean_flag_followed_by_another_flag():
    result = _parse_flags(["--wait", "--timeout=30"], allowed={"wait", "timeout"})
    assert result == {"wait": "true", "timeout": "30"}


def test_parse_flags_ignores_disallowed():
    result = _parse_flags(["--timeout=120", "--unknown=foo"], allowed={"timeout"})
    assert result == {"timeout": "120"}


def test_parse_flags_ignores_non_flag_tokens():
    result = _parse_flags(["some-arg", "--timeout", "42", "another-arg"],
                          allowed={"timeout"})
    assert result == {"timeout": "42"}


def test_parse_flags_space_form_last_token():
    result = _parse_flags(["--timeout"], allowed={"timeout"})
    assert result == {"timeout": "true"}
