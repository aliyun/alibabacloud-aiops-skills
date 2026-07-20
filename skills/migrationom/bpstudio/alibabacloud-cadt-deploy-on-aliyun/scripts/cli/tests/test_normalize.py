"""Tests for lib/normalize.py — EcsRunCommand response shape normalizer.

Verifies that all backend response variants collapse to a single stable shape:
    {success: bool, message: str, instances: {instanceId: {status, message, output}}}

Covers:
- Sync success path (Arguments already stripped by _unwrap_sync)
- Async poll success path (Arguments wrapper still present from _unwrap_data)
- Sync failure details (Arguments stripped)
- Async poll failure details (Arguments wrapper present)
- String-encoded attributes / instances (JSON-in-JSON from backend)
- Non-EcsRunCommand shapes pass through unchanged
- Partial failure (some instances succeed, some fail)
"""
from __future__ import annotations

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lib.normalize import normalize_ecs_run_result


INSTANCE_OK = {"status": "Success", "message": "Success", "output": "Hello World\n"}
INSTANCE_FAIL = {"status": "Failed", "message": "exit code 1", "output": ""}


class TestSyncSuccessPath:
    """After _unwrap_sync strips Data + Arguments, the business payload is flat."""

    def test_flat_shape_normalized(self):
        data = {"success": True, "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        result = normalize_ecs_run_result(data)
        assert result == {"success": True, "message": "", "instances": {"i-xxx": INSTANCE_OK}}

    def test_flat_shape_with_message(self):
        data = {"success": True, "message": "all ok", "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        result = normalize_ecs_run_result(data)
        assert result == {"success": True, "message": "all ok", "instances": {"i-xxx": INSTANCE_OK}}

    def test_multiple_instances(self):
        instances = {"i-aaa": INSTANCE_OK, "i-bbb": INSTANCE_OK}
        data = {"success": True, "attributes": {"instances": instances}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is True
        assert set(result["instances"].keys()) == {"i-aaa", "i-bbb"}


class TestAsyncPollSuccessPath:
    """After _unwrap_data strips Data only, Arguments wrapper remains."""

    def test_arguments_wrapper_stripped(self):
        inner = {"success": True, "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        data = {"Arguments": inner}
        result = normalize_ecs_run_result(data)
        assert result == {"success": True, "message": "", "instances": {"i-xxx": INSTANCE_OK}}

    def test_arguments_wrapper_with_message(self):
        inner = {"success": True, "message": "done", "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        data = {"Arguments": inner}
        result = normalize_ecs_run_result(data)
        assert result["message"] == "done"
        assert result["instances"] == {"i-xxx": INSTANCE_OK}


class TestFailurePath:
    """Failure details should normalize to the same shape."""

    def test_sync_failure_details(self):
        data = {"success": False, "message": "partial failure",
                "attributes": {"instances": {"i-xxx": INSTANCE_FAIL}}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is False
        assert result["message"] == "partial failure"
        assert result["instances"]["i-xxx"]["status"] == "Failed"

    def test_async_failure_details_with_arguments(self):
        inner = {"success": False, "message": "command failed",
                 "attributes": {"instances": {"i-xxx": INSTANCE_FAIL}}}
        data = {"Arguments": inner}
        result = normalize_ecs_run_result(data)
        assert result["success"] is False
        assert result["message"] == "command failed"
        assert result["instances"]["i-xxx"]["status"] == "Failed"

    def test_partial_failure(self):
        instances = {"i-aaa": INSTANCE_OK, "i-bbb": INSTANCE_FAIL}
        data = {"success": False, "message": "1 of 2 failed",
                "attributes": {"instances": instances}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is False
        assert result["instances"]["i-aaa"]["status"] == "Success"
        assert result["instances"]["i-bbb"]["status"] == "Failed"


class TestStringEncodedFields:
    """Backend sometimes returns attributes or instances as JSON strings."""

    def test_string_encoded_attributes(self):
        instances = {"i-xxx": INSTANCE_OK}
        attrs_str = json.dumps({"instances": instances})
        data = {"success": True, "attributes": attrs_str}
        result = normalize_ecs_run_result(data)
        assert result["success"] is True
        assert result["instances"] == instances

    def test_string_encoded_instances(self):
        instances = {"i-xxx": INSTANCE_OK}
        data = {"success": True, "attributes": {"instances": json.dumps(instances)}}
        result = normalize_ecs_run_result(data)
        assert result["instances"] == instances

    def test_arguments_with_string_encoded_attributes(self):
        instances = {"i-xxx": INSTANCE_OK}
        attrs_str = json.dumps({"instances": instances})
        data = {"Arguments": {"success": True, "attributes": attrs_str}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is True
        assert result["instances"] == instances


class TestNonEcsRunCommandPassthrough:
    """Non-EcsRunCommand shapes must pass through unchanged."""

    def test_plain_dict_passthrough(self):
        data = {"packageUrl": "oss://bucket/artifact.tar.gz"}
        assert normalize_ecs_run_result(data) == data

    def test_non_dict_passthrough(self):
        assert normalize_ecs_run_result("some string") == "some string"
        assert normalize_ecs_run_result(42) == 42
        assert normalize_ecs_run_result(None) is None

    def test_dict_with_attributes_but_no_instances(self):
        data = {"success": True, "attributes": {"somethingElse": "value"}}
        assert normalize_ecs_run_result(data) == data

    def test_empty_dict_passthrough(self):
        assert normalize_ecs_run_result({}) == {}

    def test_nested_dict_without_instances(self):
        data = {"Arguments": {"projectId": "proj-123", "status": "ok"}}
        assert normalize_ecs_run_result(data) == data


class TestSuccessFieldCoercion:
    """success field may arrive as string or non-bool from backend."""

    def test_success_as_string_true(self):
        data = {"success": "true", "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is True

    def test_success_as_string_false(self):
        data = {"success": "false", "attributes": {"instances": {"i-xxx": INSTANCE_FAIL}}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is False

    def test_success_missing(self):
        data = {"attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        result = normalize_ecs_run_result(data)
        assert result["success"] is False


class TestEnvelopeIntegration:
    """Verify the final envelope shape that agents parse via jq."""

    def test_success_envelope_shape(self):
        """After normalization, success envelope should be .data.instances."""
        business = normalize_ecs_run_result(
            {"success": True, "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        )
        envelope = {"ok": True, "data": business, "meta": {}}
        assert envelope["data"]["instances"]["i-xxx"]["output"] == "Hello World\n"
        assert envelope["data"]["success"] is True

    def test_failure_envelope_shape(self):
        """After normalization, failure envelope should be .data.instances (in error.data)."""
        details = normalize_ecs_run_result(
            {"Arguments": {"success": False, "message": "failed",
                           "attributes": {"instances": {"i-xxx": INSTANCE_FAIL}}}}
        )
        envelope = {"ok": False, "error": {"code": "BUSINESS_FAILURE", "message": "failed"},
                    "data": details, "meta": {}}
        assert envelope["data"]["instances"]["i-xxx"]["status"] == "Failed"
        assert envelope["data"]["success"] is False

    def test_sync_and_async_produce_same_shape(self):
        """The key invariant: sync and async paths must produce identical .data shape."""
        sync_input = {"success": True, "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}
        async_input = {"Arguments": {"success": True, "attributes": {"instances": {"i-xxx": INSTANCE_OK}}}}

        sync_result = normalize_ecs_run_result(sync_input)
        async_result = normalize_ecs_run_result(async_input)

        assert sync_result == async_result
