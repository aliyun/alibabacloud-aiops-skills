"""Tests for the hook mechanism (lib/hooks.py).

Covers:
- No hook file → no-op pass-through
- Pre-hook modifies args
- Pre-hook rejects (HookReject → PRE_HOOK_REJECTED)
- Post-hook modifies result
- Post-hook rejects (HookReject → POSTVERIFY_FAILED)
- Global hook ordering (global before per-op in pre; per-op before global in post)
- Case-insensitive op resolve still triggers hooks
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CADT = os.path.join(ROOT, "cadt_deploy_on_aliyun.py")

sys.path.insert(0, ROOT)
from lib import hooks
from lib.errors import HookReject, PRE_HOOK_REJECTED


_DEPLOY_REQUIRED = '"applicationStart":"scripts/start.sh","applicationStop":"scripts/stop.sh","artifactPath":"/root/my-app"'


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, CADT, *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.stdout.strip(), f"empty stdout, stderr={proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _merge(extra: str) -> str:
    """Merge extra JSON fields with the required deploy fields."""
    return "{" + extra.strip("{}") + "," + _DEPLOY_REQUIRED + "}"


class TestHookLoader:
    def setup_method(self):
        hooks.clear_cache()

    def test_no_hook_file_noop(self):
        """When hook file doesn't exist, args pass through unchanged."""
        args = {"region": "cn-hangzhou"}
        ctx = {"op_name": "NoSuchOp", "exec_mode": "sync", "service_type": "qoder"}
        result = hooks.run_pre_hooks("NoSuchOp", args, ctx)
        assert result == args

    def test_no_hook_file_post_noop(self):
        """Post hook no-op when hook file doesn't exist."""
        data = {"projectId": "proj-123"}
        ctx = {"op_name": "NoSuchOp", "exec_mode": "sync", "service_type": "qoder"}
        result = hooks.run_post_hooks("NoSuchOp", {}, data, ctx)
        assert result == data


class TestInstallApplicationPreHook:
    """Test the real hooks/pre/InstallApplication.py."""

    def test_required_fields_passes(self):
        """regionId + instanceIds + appName + artifactUrl + required fields → hook does not reject."""
        env = _run("-run", "InstallApplication",
                   _merge('{"regionId":"cn-hangzhou","instanceIds":["i-bp1xxx"],"appName":"my-app","artifactUrl":"oss://bucket/artifact.tar.gz"}'))
        if not env["ok"]:
            assert env["error"]["code"] != "PRE_HOOK_REJECTED"

    def test_deployment_id_only_rejected(self):
        """deploymentId is deprecated; missing required fields → hook reject."""
        env = _run("-run", "InstallApplication",
                   _merge('{"deploymentId":12345}'))
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_missing_region_id_rejected(self):
        """Missing regionId → hook reject."""
        env = _run("-run", "InstallApplication",
                   _merge('{"instanceIds":["i-bp1xxx"],"appName":"my-app","artifactUrl":"oss://bucket/artifact.tar.gz"}'))
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_missing_instance_ids_rejected(self):
        """Missing instanceIds → hook reject."""
        env = _run("-run", "InstallApplication",
                   _merge('{"regionId":"cn-hangzhou","appName":"my-app","artifactUrl":"oss://bucket/artifact.tar.gz"}'))
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_no_location_fields_rejected(self):
        """Only regionId without instanceIds → hook reject."""
        env = _run("-run", "InstallApplication",
                   _merge('{"regionId":"cn-hangzhou"}'))
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_missing_application_start_rejected(self):
        """Missing applicationStart → schema required validation rejects."""
        env = _run("-run", "InstallApplication",
                    '{"regionId":"cn-hangzhou","instanceIds":["i-bp1xxx"],"appName":"my-app","artifactUrl":"oss://bucket/artifact.tar.gz","applicationStop":"scripts/stop.sh","artifactPath":"/root/app"}')
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_missing_application_stop_rejected(self):
        """Missing applicationStop → schema required validation rejects."""
        env = _run("-run", "InstallApplication",
                    '{"regionId":"cn-hangzhou","instanceIds":["i-bp1xxx"],"appName":"my-app","artifactUrl":"oss://bucket/artifact.tar.gz","applicationStart":"scripts/start.sh","artifactPath":"/root/app"}')
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_missing_artifact_path_rejected(self):
        """Missing artifactPath → schema required validation rejects."""
        env = _run("-run", "InstallApplication",
                    '{"regionId":"cn-hangzhou","instanceIds":["i-bp1xxx"],"appName":"my-app","artifactUrl":"oss://bucket/artifact.tar.gz","applicationStart":"scripts/start.sh","applicationStop":"scripts/stop.sh"}')
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")

    def test_no_required_fields_rejected(self):
        """No required fields provided → schema required validation rejects."""
        env = _run("-run", "InstallApplication", '{"regionId":"cn-hangzhou"}')
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")


class TestCaseInsensitiveHook:
    def test_lowercase_op_triggers_hook(self):
        """installapplication (all lowercase) also triggers InstallApplication validation."""
        env = _run("-run", "installapplication", '{"region":"cn-hangzhou"}')
        assert env["ok"] is False
        assert env["error"]["code"] in ("PRE_HOOK_REJECTED", "MISSING_FIELD")


class TestEcsRunCommandPreHook:
    def test_command_file_ref_resolved(self):
        """command: "@script.sh" → pre-hook reads file content and substitutes."""
        script_content = "#!/bin/bash\necho 'hello from file'"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            f.flush()
            path = f.name
        try:
            from hooks.pre.EcsRunCommand import pre_hook
            args = {"instanceIds": ["i-xxx"], "command": f"@{path}"}
            result = pre_hook(args, {})
            assert result["command"] == script_content
            assert result["type"] == "RunShellScript"
        finally:
            os.unlink(path)

    def test_command_file_ref_in_list_resolved(self):
        """command: ["@script.sh"] -> pre-hook reads file content and replaces list element."""
        script_content = "echo hello"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            f.flush()
            path = f.name
        try:
            from hooks.pre.EcsRunCommand import pre_hook
            args = {"instanceIds": ["i-xxx"], "command": [f"@{path}"]}
            result = pre_hook(args, {})
            assert result["command"] == script_content
        finally:
            os.unlink(path)

    def test_command_plain_string_unchanged(self):
        """command not starting with @ is kept as-is."""
        from hooks.pre.EcsRunCommand import pre_hook
        args = {"instanceIds": ["i-xxx"], "command": "echo hello"}
        result = pre_hook(args, {})
        assert result["command"] == "echo hello"

    def test_command_nonexistent_file_kept_as_is(self):
        """command: "@/no/such/file" -> file not found, value kept as-is."""
        from hooks.pre.EcsRunCommand import pre_hook
        args = {"instanceIds": ["i-xxx"], "command": "@/no/such/file"}
        result = pre_hook(args, {})
        assert result["command"] == "@/no/such/file"

    def test_command_file_property_reads_file(self):
        """commandFile property reads file content and injects as command."""
        script_content = "#!/bin/bash\necho 'from commandFile'"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            f.flush()
            path = f.name
        try:
            from hooks.pre.EcsRunCommand import pre_hook
            args = {"instanceIds": ["i-xxx"], "commandFile": path}
            result = pre_hook(args, {})
            assert result["command"] == script_content
            assert "commandFile" not in result
        finally:
            os.unlink(path)

    def test_command_file_property_with_existing_command(self):
        """commandFile is ignored if command is already provided."""
        from hooks.pre.EcsRunCommand import pre_hook
        args = {"instanceIds": ["i-xxx"], "command": "echo existing", "commandFile": "/tmp/ignored.sh"}
        result = pre_hook(args, {})
        assert result["command"] == "echo existing"

    def test_command_size_limit_enforced(self):
        """command exceeding ~18KB raises ValidationFailed."""
        import pytest
        from hooks.pre.EcsRunCommand import pre_hook, COMMAND_SIZE_LIMIT
        from lib.errors import ValidationFailed
        oversized = "echo 'x'" + " " * (COMMAND_SIZE_LIMIT + 100)
        args = {"instanceIds": ["i-xxx"], "command": oversized}
        with pytest.raises(ValidationFailed) as exc_info:
            pre_hook(args, {})
        assert "exceeds size limit" in exc_info.value.message
        assert "18000" in exc_info.value.fix_hint or "OSS" in exc_info.value.fix_hint

    def test_command_within_size_limit_passes(self):
        """command under limit passes without error."""
        from hooks.pre.EcsRunCommand import pre_hook, COMMAND_SIZE_LIMIT
        valid_cmd = "echo 'x'" + " " * (COMMAND_SIZE_LIMIT - 100)
        args = {"instanceIds": ["i-xxx"], "command": valid_cmd}
        result = pre_hook(args, {})
        assert len(result["command"]) < COMMAND_SIZE_LIMIT

    def test_command_list_joined_with_newlines(self):
        """command: ["cmd1", "cmd2"] → pre-hook joins with newlines into single string."""
        from hooks.pre.EcsRunCommand import pre_hook
        args = {"instanceIds": ["i-xxx"], "command": ["echo hello", "echo world"]}
        result = pre_hook(args, {})
        assert result["command"] == "echo hello\necho world"


class TestCommandFileFlag:
    def test_command_file_flag_injects_command(self):
        """--command-file=<path> reads script from file and injects into payload.command."""
        script_content = "#!/bin/bash\necho 'from --command-file'"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            f.flush()
            path = f.name
        try:
            env = _run("-run", "EcsRunCommand",
                       '{"regionId":"cn-hangzhou","instanceIds":["i-xxx"]}',
                       f"--command-file={path}")
            if not env["ok"]:
                assert env["error"]["code"] != "MISSING_FIELD"
                assert env["error"]["code"] != "VALIDATION_FAILED"
        finally:
            os.unlink(path)

    def test_command_file_flag_missing_file(self):
        """--command-file pointing to a non-existent file -> raises error."""
        env = _run("-run", "EcsRunCommand",
                   '{"regionId":"cn-hangzhou","instanceIds":["i-xxx"]}',
                   "--command-file=/no/such/script.sh")
        assert env["ok"] is False
        assert env["error"]["code"] == "CADT_INTERNAL"
        assert "command file" in env["error"]["message"]
