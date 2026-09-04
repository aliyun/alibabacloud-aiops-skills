# Bounded StartChat projection and managed follow-state source shard.
# Loaded by ros_agent.py into its shared module namespace; do not execute directly.
# ruff: noqa: F821 -- names are provided by earlier source shards.

def _event_payload(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    for key in ("statusUpdate", "artifactUpdate"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return result


def _result(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload.get("result")
    return result if isinstance(result, dict) else payload


def _normalize_state(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized.startswith("task_state_"):
        normalized = normalized[len("task_state_") :]
    return normalized.replace("_", "-")


def _state_from_result(result: Dict[str, Any]) -> Tuple[str, str]:
    event = _event_payload(result)
    candidates = [event]
    if isinstance(event, dict) and isinstance(event.get("task"), dict):
        candidates.append(event["task"])
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        status = candidate.get("status") or candidate.get("Status")
        if isinstance(status, dict):
            state = status.get("state") or status.get("State")
            if isinstance(state, str):
                return _normalize_state(state), state
        state = candidate.get("state") or candidate.get("State")
        if isinstance(state, str) and state.upper().startswith("TASK_STATE_"):
            return _normalize_state(state), state
    return "", ""


def _find_first(value: Any, *keys: str) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        for item in value.values():
            found = _find_first(item, *keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_first(item, *keys)
            if found not in (None, ""):
                return found
    return None


def _metadata_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    event = _event_payload(result)
    candidates = []
    if isinstance(event, dict):
        candidates.append(event.get("metadata"))
        status = event.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("metadata"))
        task = event.get("task")
        if isinstance(task, dict):
            candidates.append(task.get("metadata"))
    for value in candidates:
        if isinstance(value, dict) and isinstance(value.get("iac_code"), dict):
            return value["iac_code"]
    return {}


def _message_text_from_result(result: Dict[str, Any]) -> str:
    event = _event_payload(result)
    candidates = []
    if isinstance(event, dict):
        status = event.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("message"))
        candidates.append(event.get("message"))
        task = event.get("task")
        if isinstance(task, dict) and isinstance(task.get("status"), dict):
            candidates.append(task["status"].get("message"))
    for message in candidates:
        if not isinstance(message, dict) or not isinstance(message.get("parts"), list):
            continue
        pieces = [
            part.get("text")
            for part in message["parts"]
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if pieces:
            return "".join(pieces)
    return ""


def _permission_ack_from_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metadata_ack = _metadata_from_result(result).get("permissionAck")
    event = _event_payload(result)
    candidates = [metadata_ack, event]
    if isinstance(event, dict):
        candidates.append(event.get("message"))
        status = event.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("message"))
    for candidate in candidates:
        data_values = [candidate]
        if isinstance(candidate, dict) and isinstance(candidate.get("parts"), list):
            data_values.extend(part.get("data") for part in candidate["parts"] if isinstance(part, dict))
        for data in data_values:
            if not isinstance(data, dict) or data.get("kind") != "permission_ack":
                continue
            projected = {
                key: data[key]
                for key in ("schemaVersion", "kind", "inputId", "toolUseId", "decision", "accepted")
                if key in data
            }
            if projected.get("schemaVersion") != 1 or projected.get("accepted") is not True:
                continue
            if projected.get("decision") not in PERMISSION_DECISIONS:
                continue
            return projected
    return None


def _permission_is_acknowledged(permission: Any, acknowledgement: Any) -> bool:
    return (
        isinstance(permission, dict)
        and isinstance(acknowledgement, dict)
        and acknowledgement.get("accepted") is True
        and isinstance(permission.get("inputId"), str)
        and permission.get("inputId") == acknowledgement.get("inputId")
    )


def _permission_response_is_acknowledged(response: Any, acknowledgement: Any) -> bool:
    if not isinstance(response, dict) or not isinstance(acknowledgement, dict):
        return False
    if acknowledgement.get("accepted") is not True or acknowledgement.get("schemaVersion") != 1:
        return False
    return all(response.get(key) == acknowledgement.get(key) for key in ("inputId", "toolUseId", "decision"))


def _safe_deployment_summary(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    fields = (
        ("candidateName", 200),
        ("action", 80),
        ("region", 120),
        ("stackName", 200),
        ("template", 300),
        ("totalMonthlyCost", 300),
    )
    for key, maximum in fields:
        if key in value:
            result[key] = sanitize_text(value.get(key), maximum)
    resources = value.get("resources")
    if isinstance(resources, list):
        result["resources"] = [
            {
                key: sanitize_text(item.get(key), maximum)
                for key, maximum in (("name", 200), ("spec", 300), ("monthlyCost", 300))
                if key in item
            }
            for item in resources[:12]
            if isinstance(item, dict)
        ]
    return result or None


def _is_secret_field(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(
        fragment in normalized
        for fragment in (
            "accesskey",
            "apikey",
            "auth",
            "authorization",
            "cookie",
            "credential",
            "passphrase",
            "password",
            "passwd",
            "privatekey",
            "pwd",
            "secret",
            "session",
            "signature",
            "ststoken",
            "token",
        )
    )


def _safe_display_value(key: Any, value: Any, depth: int = 0) -> Any:
    if depth >= 16:
        return {"truncated": True}
    if _is_secret_field(key):
        return {"redacted": True}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return sanitize_text(value, 2000, True)
    if isinstance(value, dict):
        return {
            sanitize_text(str(item_key), 200): _safe_display_value(item_key, item_value, depth + 1)
            for item_key, item_value in list(value.items())[:64]
        }
    if isinstance(value, list):
        return [_safe_display_value(key, item, depth + 1) for item in value[:64]]
    return sanitize_text(str(value), 2000, True)


def _safe_permission_operation(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    for key in ("product", "action", "region"):
        if key in value:
            result[key] = sanitize_text(value.get(key), 200)
    target = value.get("target")
    if isinstance(target, dict):
        result["target"] = {
            key: sanitize_text(target.get(key), 300)
            for key in ("type", "name", "id")
            if key in target
        }
    api_calls = value.get("apiCalls")
    if isinstance(api_calls, list):
        result["apiCalls"] = [
            {
                key: sanitize_text(item.get(key), 200)
                for key in ("product", "action", "effect", "repeat")
                if key in item
            }
            for item in api_calls[:20]
            if isinstance(item, dict)
        ]
    return result or None


def _safe_display_parameters(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict) or value.get("format") != "json" or "value" not in value:
        return None
    return {"format": "json", "value": _safe_display_value("value", value["value"])}


def _safe_input(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    allowed = {"schemaVersion", "kind", "requestTaskId", "contextId", "inputId", "prompt", "options", "required"}
    if kind == "permission":
        allowed.update(
            {
                "toolUseId",
                "toolName",
                "title",
                "purpose",
                "effect",
                "target",
                "isReadOnly",
                "safeSummary",
                "deploymentSummary",
                "scope",
                "subPipelineId",
                "operation",
                "displayParameters",
                "language",
            }
        )
    elif kind == "ask_user_question":
        allowed.update({"allowFreeText", "freeTextPrompt"})
    elif kind != "candidate_selection":
        return None
    result = {key: value[key] for key in allowed if key in value}
    text_fields = (
        ("prompt", 1000),
        ("freeTextPrompt", 600),
        ("safeSummary", 1200),
        ("title", 300),
        ("purpose", 600),
        ("effect", 120),
        ("target", 600),
        ("toolName", 120),
        ("language", 12),
        ("scope", 120),
        ("subPipelineId", 200),
    )
    for key, maximum in text_fields:
        if key in result:
            result[key] = sanitize_text(result[key], maximum)
    if "isReadOnly" in result:
        result["isReadOnly"] = result["isReadOnly"] is True
    if "allowFreeText" in result:
        result["allowFreeText"] = result["allowFreeText"] is True
    if "deploymentSummary" in result:
        result["deploymentSummary"] = _safe_deployment_summary(result["deploymentSummary"])
    if "operation" in result:
        result["operation"] = _safe_permission_operation(result["operation"])
    if "displayParameters" in result:
        result["displayParameters"] = _safe_display_parameters(result["displayParameters"])
    options = value.get("options")
    if isinstance(options, list):
        safe_options = []
        for item in options[:20]:
            if not isinstance(item, dict):
                continue
            safe_item = {}
            option_fields = (
                ("id", 120),
                ("label", 240),
                ("summary", 800),
                ("architectureDiagram", 2400),
                ("totalMonthlyCost", 300),
            )
            for key, maximum in option_fields:
                if key in item:
                    safe_item[key] = sanitize_text(item.get(key), maximum, key == "architectureDiagram")
            costs = item.get("costItems")
            if isinstance(costs, list):
                safe_item["costItems"] = [
                    {
                        key: sanitize_text(cost.get(key), maximum)
                        for key, maximum in (("name", 200), ("spec", 300), ("monthlyCost", 300))
                        if key in cost
                    }
                    for cost in costs[:12]
                    if isinstance(cost, dict)
                ]
            if safe_item:
                safe_options.append(safe_item)
        result["options"] = safe_options
    return result


def _pipeline_events(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    batch = metadata.get("pipelineBatch")
    if isinstance(batch, dict) and isinstance(batch.get("events"), list):
        return [item for item in batch["events"] if isinstance(item, dict)]
    event = metadata.get("pipeline")
    return [event] if isinstance(event, dict) else []


def _input_from_metadata(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    direct = _safe_input(metadata.get("input"))
    if direct is not None:
        return direct

    def find(value: Any) -> Optional[Dict[str, Any]]:
        projected = _safe_input(value)
        if projected is not None:
            return projected
        if isinstance(value, dict):
            for item in value.values():
                projected = find(item)
                if projected is not None:
                    return projected
        elif isinstance(value, list):
            for item in value:
                projected = find(item)
                if projected is not None:
                    return projected
        return None

    return find(_pipeline_events(metadata))


def _pending_permissions_from_metadata(metadata: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    pending = metadata.get("pendingPermissions")
    if not isinstance(pending, list):
        return None
    result = []
    for value in pending:
        projected = _safe_input(value)
        if projected is not None and projected.get("kind") == "permission":
            result.append(projected)
    return result


def _safe_permission_wait(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    value = metadata.get("permissionWait")
    if not isinstance(value, dict):
        return None
    status = value.get("status")
    if not isinstance(status, str) or status not in {"waiting", "grace", "suspended"}:
        return None
    result = {"status": status}
    if "resumable" in value:
        result["resumable"] = value.get("resumable") is True
    return result


def _safe_permission_recovered(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    value = metadata.get("permissionRecovered")
    if not isinstance(value, dict):
        return None
    result = {}
    for key in ("inputId", "toolUseId"):
        item = value.get(key)
        if isinstance(item, str) and item:
            result[key] = sanitize_text(item, 240)
    return result or None


def _is_sideband_permission(metadata: Dict[str, Any], input_value: Dict[str, Any]) -> bool:
    if input_value.get("kind") != "permission":
        return False
    return any(
        event.get("eventType") == "permission_requested" and event.get("status") == "working"
        for event in _pipeline_events(metadata)
    )


def _permission_class(value: Dict[str, Any], *, mode: str, sideband: bool) -> Dict[str, Any]:
    if value.get("kind") != "permission":
        return value
    result = _permission_with_ref(value)
    result["permissionClass"] = "sub_pipeline" if sideband else ("pipeline" if mode == "pipeline" else "normal")
    return result


def _permission_ref(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    input_id = value.get("inputId")
    if not isinstance(input_id, str) or not input_id:
        return None
    digest = hashlib.sha256(input_id.encode("utf-8")).hexdigest()[:10]
    return "p-{}".format(digest)


def _permission_with_ref(value: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(value)
    if result.get("kind") == "permission":
        permission_ref = _permission_ref(result)
        if permission_ref is not None:
            result["permissionRef"] = permission_ref
    return result


def _safe_pipeline_result(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    for key, maximum in (("status", 80), ("stack_id", 240), ("error", 1000)):
        item = value.get(key)
        if isinstance(item, str) and item:
            result[key] = sanitize_text(item, maximum)
    resources = value.get("resources_created")
    if isinstance(resources, list):
        result["resources_created"] = [
            sanitize_text(item, 240) for item in resources[:24] if isinstance(item, str) and item
        ]
    outputs = value.get("outputs")
    if isinstance(outputs, dict):
        result["outputs"] = {
            sanitize_text(str(key), 120): sanitize_text(str(item), 300)
            for key, item in list(outputs.items())[:24]
            if isinstance(key, str) and isinstance(item, (str, int, float, bool))
        }
    return result or None


def _safe_intent_conclusion(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    for source, target, maximum in (
        ("user_message_summary", "requirementSummary", 360),
        ("cloud_platform", "cloudPlatform", 80),
        ("business_type", "businessType", 120),
    ):
        item = value.get(source)
        if isinstance(item, str) and item:
            result[target] = sanitize_text(item, maximum)
    non_functional = value.get("non_functional")
    if isinstance(non_functional, dict) and isinstance(non_functional.get("region_preference"), str):
        result["region"] = sanitize_text(non_functional["region_preference"], 120)
    resources = []
    for item in value.get("resource_intents", [])[:10] if isinstance(value.get("resource_intents"), list) else []:
        if not isinstance(item, dict):
            continue
        projected = {
            key: sanitize_text(item.get(key), maximum)
            for key, maximum in (("product", 100), ("action", 40), ("role", 100))
            if isinstance(item.get(key), str) and item.get(key)
        }
        if projected:
            resources.append(projected)
    if resources:
        result["resources"] = resources
    while len(_json_bytes(result)) > MAX_STEP_CONCLUSION_BYTES:
        if resources and len(resources) > 1:
            resources.pop()
        elif isinstance(result.get("requirementSummary"), str) and len(result["requirementSummary"]) > 120:
            result["requirementSummary"] = _truncate_utf8(result["requirementSummary"], 120)
        elif "businessType" in result:
            result.pop("businessType")
        elif "cloudPlatform" in result:
            result.pop("cloudPlatform")
        else:
            break
    return result or None


def _safe_architecture_conclusion(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get("candidates"), list):
        return None
    raw_candidates = value["candidates"]
    candidates = []
    for item in raw_candidates[:4]:
        if not isinstance(item, dict):
            continue
        projected = {}
        for source, target, maximum in (
            ("name", "name", 160),
            ("topology", "topology", 300),
            ("monthly_estimate", "monthlyEstimate", 160),
        ):
            candidate = item.get(source)
            if isinstance(candidate, str) and candidate:
                projected[target] = sanitize_text(candidate, maximum)
        if projected:
            candidates.append(projected)
    result = {"candidateCount": len(raw_candidates), "candidates": candidates}
    while len(_json_bytes(result)) > MAX_STEP_CONCLUSION_BYTES and candidates:
        if len(candidates) > 2:
            candidates.pop()
            continue
        changed = False
        for candidate in reversed(candidates):
            topology = candidate.get("topology")
            if isinstance(topology, str) and len(topology) > 100:
                candidate["topology"] = _truncate_utf8(topology, 100)
                changed = True
                break
        if not changed:
            candidates.pop()
    return result if candidates else None


def _safe_step_conclusion(step_id: Any, conclusion_field: Any, value: Any) -> Optional[Dict[str, Any]]:
    if step_id == "intent_parsing" or conclusion_field == "intent":
        return _safe_intent_conclusion(value)
    if step_id == "architecture_planning" or conclusion_field == "architecture":
        return _safe_architecture_conclusion(value)
    return None


def _safe_milestone(value: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event_type = value.get("eventType") or value.get("event_type")
    if event_type not in PIPELINE_EVENT_TYPES:
        return None
    result = {"eventType": event_type}
    for key in ("status", "sequence", "scope"):
        item = value.get(key)
        if isinstance(item, (str, int)):
            result[key] = item
    for key in ("step", "parentStep", "candidate", "candidateStep"):
        item = value.get(key)
        if isinstance(item, dict):
            result[key] = {
                field: item[field]
                for field in ("id", "name", "index", "total")
                if isinstance(item.get(field), (str, int))
            }
    data = value.get("data")
    if isinstance(data, dict):
        message = data.get("message") or data.get("summary") or data.get("description")
        if isinstance(message, str):
            result["message"] = sanitize_text(message, 500)
        if event_type == "step_completed":
            step = value.get("step")
            step_id = step.get("id") if isinstance(step, dict) else None
            conclusion = _safe_step_conclusion(step_id, data.get("conclusionField"), data.get("conclusion"))
            if conclusion is not None:
                result["conclusionSummary"] = conclusion
    return result


def _normal_handoff_ready(value: Dict[str, Any]) -> bool:
    if value.get("eventType") != "pipeline_handoff_ready" or value.get("visibility") not in {None, "committed"}:
        return False
    data = value.get("data")
    return isinstance(data, dict) and data.get("action") == "switch_to_normal" and data.get("targetMode") == "normal"


def _safe_artifact(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event = _event_payload(result)
    artifact = event.get("artifact") if isinstance(event, dict) else None
    if not isinstance(artifact, dict):
        return None
    parts = artifact.get("parts")
    first = parts[0] if isinstance(parts, list) and parts and isinstance(parts[0], dict) else {}
    uri = first.get("url")
    if not isinstance(uri, str):
        return None
    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
    projected = {
        "id": sanitize_text(str(artifact.get("artifactId") or ""), 128),
        "name": sanitize_text(artifact.get("name") or first.get("filename"), 240),
        "uri": sanitize_text(uri, 1200, True),
    }
    for key in ("mediaType", "sha256", "sourcePath"):
        if isinstance(metadata.get(key), str):
            projected[key] = sanitize_text(metadata[key], 1000, True)
    if isinstance(metadata.get("byteSize"), int):
        projected["byteSize"] = metadata["byteSize"]
    return projected


class StreamSummary:
    def __init__(self, initial_session_id: Optional[str] = None, mode: str = "normal") -> None:
        self.session_id = initial_session_id
        self.mode = mode
        self.task_id = None  # type: Optional[str]
        self.iac_code_session_id = None  # type: Optional[str]
        self.request_id = None  # type: Optional[str]
        self.state = ""
        self.wire_state = ""
        self.input_required = None  # type: Optional[Dict[str, Any]]
        self.input_required_from_pending = False
        self.pending_permissions = []  # type: List[Dict[str, Any]]
        self.permission_ack = None  # type: Optional[Dict[str, Any]]
        self.permission_wait = None  # type: Optional[Dict[str, Any]]
        self.permission_recovered = None  # type: Optional[Dict[str, Any]]
        self.sideband_input_ids = set()  # type: set
        self.resolved_sideband_input_ids = set()  # type: set
        self.text_parts = []  # type: List[str]
        self.text_bytes = 0
        self.text_truncated = False
        self.assistant_final = False
        self.milestones = []  # type: List[Dict[str, Any]]
        self.artifacts = []  # type: List[Dict[str, Any]]
        self.pipeline_result = None  # type: Optional[Dict[str, Any]]
        self.normal_handoff_ready = False
        self.event_count = 0
        self.heartbeat_count = 0
        self.malformed_event_count = 0
        self.error = None  # type: Optional[Dict[str, Any]]

    def _append_text(self, value: str) -> None:
        value = sanitize_text(value, MAX_FINAL_TEXT_BYTES, True)
        if not value:
            return
        remaining = MAX_FINAL_TEXT_BYTES - self.text_bytes
        if remaining <= 0:
            self.text_truncated = True
            return
        bounded = _truncate_utf8(value, remaining)
        self.text_parts.append(bounded)
        self.text_bytes += len(bounded.encode("utf-8"))
        if bounded != value:
            self.text_truncated = True

    def _replace_text(self, value: str) -> None:
        """Use the authoritative final snapshot instead of duplicating prior deltas."""
        raw_size = len(value.encode("utf-8"))
        value = sanitize_text(value, MAX_FINAL_TEXT_BYTES, True)
        self.text_parts = [value] if value else []
        self.text_bytes = len(value.encode("utf-8"))
        self.text_truncated = raw_size > MAX_FINAL_TEXT_BYTES

    def apply(self, payload: Dict[str, Any]) -> None:
        self.event_count += 1
        if str(payload.get("object", "")).lower() in {"heartbeat", "keepalive"}:
            self.heartbeat_count += 1
            return
        result = _result(payload)
        session_id = _find_first(payload, "contextId", "context_id", "SessionId")
        task_id = _find_first(payload, "taskId", "task_id")
        iac_session_id = _find_first(payload, "iacCodeSessionId", "iac_code_session_id")
        request_id = _find_first(payload, "requestId", "request_id", "RequestId")
        if isinstance(session_id, str):
            self.session_id = session_id
        if isinstance(task_id, str):
            self.task_id = task_id
        if isinstance(iac_session_id, str):
            self.iac_code_session_id = iac_session_id
        if isinstance(request_id, str):
            self.request_id = request_id
        state, wire_state = _state_from_result(result)
        # A few StartChat gateways emit a trailing WORKING status after the
        # authoritative terminal event. Keep the terminal state monotonic so
        # the managed job can expose Pipeline handoff instead of becoming an
        # ownerless working job when the CLI process exits.
        if state and (self.state not in TERMINAL_STATES or state in TERMINAL_STATES):
            self.state = state
            self.wire_state = wire_state
        metadata = _metadata_from_result(result)
        terminal_state_seen = self.state in TERMINAL_STATES
        if terminal_state_seen:
            # Terminal ownership also closes every waiting boundary. A stale
            # trailing status may still contribute artifacts, Pipeline
            # results, handoff metadata, text, or a real error below, but it
            # cannot reopen user input or permission-wait state.
            self.input_required = None
            self.input_required_from_pending = False
            self.pending_permissions = []
            self.permission_wait = None
        permission_wait = None if terminal_state_seen else _safe_permission_wait(metadata)
        if permission_wait is not None:
            self.permission_wait = permission_wait
        permission_recovered = None if terminal_state_seen else _safe_permission_recovered(metadata)
        if permission_recovered is not None:
            self.permission_recovered = permission_recovered
            self.permission_wait = None
            recovered_input_id = permission_recovered.get("inputId")
            if isinstance(self.input_required, dict) and self.input_required.get("inputId") == recovered_input_id:
                self.input_required = None
                self.input_required_from_pending = False
            self.pending_permissions = [
                value for value in self.pending_permissions if value.get("inputId") != recovered_input_id
            ]
        input_required = None if terminal_state_seen else _input_from_metadata(metadata)
        pending_permissions = None if terminal_state_seen else _pending_permissions_from_metadata(metadata)
        pending_input_ids = {value.get("inputId") for value in pending_permissions or [] if isinstance(value, dict)}
        if pending_permissions is not None:
            self.resolved_sideband_input_ids.update(self.sideband_input_ids - pending_input_ids)
        previous_sideband_input_id = (
            self.input_required.get("inputId")
            if isinstance(self.input_required, dict) and self.input_required.get("permissionClass") == "sub_pipeline"
            else None
        )
        sideband_input = input_required is not None and (
            _is_sideband_permission(metadata, input_required)
            or input_required.get("inputId") in pending_input_ids
            or input_required.get("inputId") in self.sideband_input_ids
            or input_required.get("inputId") == previous_sideband_input_id
        )
        if sideband_input and isinstance(input_required.get("inputId"), str):
            self.sideband_input_ids.add(input_required["inputId"])
        stale_resolved_sideband = (
            input_required is not None and input_required.get("inputId") in self.resolved_sideband_input_ids
        )
        if input_required is not None and not stale_resolved_sideband:
            self.input_required = _permission_class(input_required, mode=self.mode, sideband=sideband_input)
            self.input_required_from_pending = sideband_input
        if pending_permissions is None and sideband_input and isinstance(self.input_required, dict):
            pending_permissions = [self.input_required]
        if pending_permissions is not None:
            self.pending_permissions = [
                _permission_class(value, mode=self.mode, sideband=True) for value in pending_permissions
            ]
            direct_input_id = self.input_required.get("inputId") if isinstance(self.input_required, dict) else None
            matching_pending = next(
                (value for value in self.pending_permissions if value.get("inputId") == direct_input_id),
                None,
            )
            if matching_pending is not None:
                self.input_required = matching_pending
                self.input_required_from_pending = True
            elif self.pending_permissions and (self.input_required is None or self.input_required_from_pending):
                self.input_required = self.pending_permissions[0]
                self.input_required_from_pending = True
            elif not self.pending_permissions and self.input_required_from_pending:
                self.input_required = None
                self.input_required_from_pending = False
        text = _message_text_from_result(result)
        permission_ack = _permission_ack_from_result(result)
        if permission_ack is not None:
            self.permission_ack = permission_ack
        if _permission_is_acknowledged(self.input_required, self.permission_ack):
            acknowledged_input_id = self.permission_ack.get("inputId")
            self.input_required = None
            self.input_required_from_pending = False
            self.pending_permissions = [
                value for value in self.pending_permissions if value.get("inputId") != acknowledged_input_id
            ]
            if self.pending_permissions:
                self.input_required = self.pending_permissions[0]
                self.input_required_from_pending = True
        assistant_final = metadata.get("assistantFinal")
        is_assistant_final = isinstance(assistant_final, dict) and assistant_final.get("complete") is True
        if (is_assistant_final or self.state in TERMINAL_STATES) and self.input_required_from_pending:
            self.input_required = None
            self.input_required_from_pending = False
            self.pending_permissions = []
        if text:
            if is_assistant_final:
                self._replace_text(text)
            else:
                self._append_text(text)
        if is_assistant_final:
            self.assistant_final = True
        for item in _pipeline_events(metadata):
            if _normal_handoff_ready(item):
                self.normal_handoff_ready = True
            milestone = _safe_milestone(item)
            if milestone is not None and milestone not in self.milestones:
                self.milestones.append(milestone)
                self.milestones = self.milestones[-40:]
            data = item.get("data")
            if (
                item.get("eventType") == "step_completed"
                and isinstance(data, dict)
                and data.get("conclusionField") == "deployment"
            ):
                pipeline_result = _safe_pipeline_result(data.get("conclusion"))
                if pipeline_result is not None:
                    self.pipeline_result = pipeline_result
        artifact = _safe_artifact(result)
        if artifact is not None and artifact not in self.artifacts:
            self.artifacts.append(artifact)
            self.artifacts = self.artifacts[-24:]
        raw_error = payload.get("error")
        if not isinstance(raw_error, dict):
            raw_error = result.get("error") if isinstance(result.get("error"), dict) else None
        if isinstance(raw_error, dict):
            backup_not_ready = _session_backup_not_ready_error(raw_error)
            if backup_not_ready is not None:
                self.error = {
                    "code": backup_not_ready.code,
                    "message": backup_not_ready.message,
                    "retryable": True,
                }
            else:
                code = raw_error.get("code") or raw_error.get("Code") or "StartChatFailed"
                message = raw_error.get("message") or raw_error.get("Message") or "StartChat returned an error."
                self.error = {
                    "code": sanitize_text(str(code), 160),
                    "message": sanitize_text(str(message), 2000),
                }
        if str(payload.get("object", "")).lower() == "response" and str(payload.get("status", "")).lower() == "failed":
            self.state = "failed"

    def to_result(self, return_code: int, stderr_text: str) -> Dict[str, Any]:
        failed = return_code != 0 or self.state == "failed" or self.error is not None
        if failed:
            state = "failed"
        elif self.input_required is not None:
            state = "input-required"
        elif self.state in TERMINAL_STATES:
            state = "turn-completed" if self.mode == "normal" and self.state == "completed" else self.state
        elif self.assistant_final or (self.mode == "normal" and self.state == "input-required"):
            state = "turn-completed"
        elif self.permission_ack is not None:
            state = "permission-responded"
        else:
            state = self.state or "stream-ended"
        result = {
            "ok": not failed,
            "state": state,
            "presentationRequired": True,
            "eventCount": self.event_count,
            "heartbeatCount": self.heartbeat_count,
            "malformedEventCount": self.malformed_event_count,
        }  # type: Dict[str, Any]
        identities = (
            ("sessionId", self.session_id),
            ("taskId", self.task_id),
            ("iacCodeSessionId", self.iac_code_session_id),
            ("requestId", self.request_id),
            ("wireState", self.wire_state),
        )
        for key, value in identities:
            if value:
                result[key] = value
        text = "".join(self.text_parts)
        if state == "turn-completed":
            result["finalText"] = text
            result["finalTextComplete"] = not self.text_truncated
        elif text:
            result["latestText"] = _truncate_utf8(text, 16000)
        if self.input_required is not None:
            result["inputRequired"] = self.input_required
        if self.pending_permissions:
            result["pendingPermissions"] = self.pending_permissions
        if self.permission_ack is not None:
            result["permissionAck"] = self.permission_ack
        if self.permission_wait is not None:
            result["permissionWait"] = self.permission_wait
        if self.permission_recovered is not None:
            result["permissionRecovered"] = self.permission_recovered
        if self.milestones:
            result["milestones"] = self.milestones
        if self.artifacts:
            result["artifacts"] = self.artifacts
        if self.pipeline_result is not None:
            result["pipelineResult"] = self.pipeline_result
        if self.normal_handoff_ready:
            result["normalHandoffReady"] = True
            result["conversationMode"] = "normal"
        if self.error is not None:
            result["error"] = self.error
        elif return_code != 0:
            result["error"] = {
                "code": "aliyun_cli_failed",
                "message": sanitize_text(stderr_text, 3000)
                or "Alibaba Cloud CLI exited with status {}.".format(return_code),
            }
        elif self.event_count == 0:
            result["ok"] = False
            result["state"] = "failed"
            result["error"] = {"code": "empty_stream", "message": "StartChat ended without an SSE event."}
        return _bound_result(result)


def _bound_result(result: Dict[str, Any]) -> Dict[str, Any]:
    def size() -> int:
        return len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    while size() > MAX_RESULT_BYTES and result.get("milestones"):
        result["milestones"].pop(0)
    while size() > MAX_RESULT_BYTES and result.get("artifacts"):
        result["artifacts"].pop(0)
    if size() > MAX_RESULT_BYTES and isinstance(result.get("finalText"), str):
        result["finalText"] = _truncate_utf8(result["finalText"], MAX_RESULT_BYTES // 2)
        result["finalTextComplete"] = False
    return result


def _bound_projection(projection: Dict[str, Any]) -> Dict[str, Any]:
    bounded = dict(projection)
    input_value = bounded.get("inputRequired")
    maximum = MAX_INPUT_PROJECTION_BYTES if isinstance(input_value, dict) else MAX_PROJECTION_BYTES
    if len(_json_bytes(bounded)) <= maximum:
        return bounded
    if isinstance(input_value, dict):
        envelope = dict(input_value)
        bounded["inputRequired"] = envelope
        options = envelope.get("options")
        if isinstance(options, list):
            envelope["options"] = [dict(item) for item in options if isinstance(item, dict)]
        while len(_json_bytes(bounded)) > maximum:
            changed = False
            for key, minimum in (
                ("safeSummary", 160),
                ("purpose", 100),
                ("target", 80),
                ("prompt", 120),
                ("freeTextPrompt", 80),
            ):
                value = envelope.get(key)
                if isinstance(value, str) and len(value) > minimum:
                    envelope[key] = value[: max(minimum, len(value) // 2)]
                    changed = True
            for option in envelope.get("options", []):
                if not isinstance(option, dict):
                    continue
                for key, minimum in (("summary", 100), ("architectureDiagram", 240), ("totalMonthlyCost", 20)):
                    value = option.get(key)
                    if isinstance(value, str) and len(value) > minimum:
                        option[key] = value[: max(minimum, len(value) // 2)]
                        changed = True
                costs = option.get("costItems")
                if isinstance(costs, list) and len(costs) > 6:
                    del costs[6:]
                    changed = True
            if not changed:
                break
        if len(_json_bytes(bounded)) > maximum:
            raise BridgeError("stream_failed", "A StartChat input boundary exceeded the bounded bridge protocol.")
        bounded["trimmed"] = True
        return bounded
    milestones = bounded.get("milestones")
    while len(_json_bytes(bounded)) > maximum and isinstance(milestones, list) and len(milestones) > 1:
        milestones.pop(0)
    bounded.pop("latestText", None)
    if len(_json_bytes(bounded)) > maximum:
        bounded = {
            key: bounded[key]
            for key in ("type", "state", "sessionId", "taskId", "requestSeq", "error")
            if key in bounded
        }
        bounded["trimmed"] = True
    return bounded


def _project_stream_event(
    payload: Dict[str, Any],
    mode: str,
    request_seq: int,
    worker_role: str = "primary",
    worker_token: Optional[str] = None,
) -> Dict[str, Any]:
    result = _result(payload)
    state, wire_state = _state_from_result(result)
    metadata = _metadata_from_result(result)
    projection = {"type": "status", "requestSeq": request_seq, "time": int(time.time())}  # type: Dict[str, Any]
    if worker_role == "sideband":
        projection["workerRole"] = "sideband"
        if isinstance(worker_token, str) and worker_token:
            projection["workerToken"] = worker_token
    if state:
        projection["state"] = state
    if wire_state:
        projection["wireState"] = wire_state
    for key, value in (
        ("sessionId", _find_first(payload, "contextId", "context_id", "SessionId")),
        ("taskId", _find_first(payload, "taskId", "task_id")),
        ("iacCodeSessionId", _find_first(payload, "iacCodeSessionId", "iac_code_session_id")),
        ("requestId", _find_first(payload, "requestId", "request_id", "RequestId")),
    ):
        if isinstance(value, str) and value:
            projection[key] = sanitize_text(value, 240)

    input_required = _input_from_metadata(metadata)
    pending_permissions = _pending_permissions_from_metadata(metadata)
    if pending_permissions is not None:
        projection["pendingPermissions"] = [
            _permission_class(value, mode=mode, sideband=True) for value in pending_permissions
        ]
    if input_required is not None:
        sideband_ids = {
            value.get("inputId") for value in projection.get("pendingPermissions", []) if isinstance(value, dict)
        }
        sideband_input = input_required.get("inputId") in sideband_ids or _is_sideband_permission(
            metadata, input_required
        )
        projected_input = _permission_class(
            input_required,
            mode=mode,
            sideband=sideband_input,
        )
        projection["inputRequired"] = projected_input
        if sideband_input and "pendingPermissions" not in projection:
            projection["pendingPermissions"] = [projected_input]
        projection["type"] = "input-required"

    permission_wait = _safe_permission_wait(metadata)
    if permission_wait is not None:
        projection["permissionWait"] = permission_wait
        if projection["type"] == "status":
            projection["type"] = "permission-wait"

    permission_recovered = _safe_permission_recovered(metadata)
    if permission_recovered is not None:
        projection["permissionRecovered"] = permission_recovered
        if projection["type"] == "status":
            projection["type"] = "permission-recovered"

    milestones = []
    for item in _pipeline_events(metadata):
        if _normal_handoff_ready(item):
            projection["normalHandoffReady"] = True
        milestone = _safe_milestone(item)
        if milestone is not None and milestone not in milestones:
            milestones.append(milestone)
    if milestones:
        projection["milestones"] = milestones
        if projection["type"] == "status":
            projection["type"] = "milestone"

    permission_ack = _permission_ack_from_result(result)
    if permission_ack is not None:
        projection["permissionAck"] = permission_ack
        if projection["type"] == "status":
            projection["type"] = "permission-ack"

    artifact = _safe_artifact(result)
    if artifact is not None:
        projection["artifact"] = artifact
        if projection["type"] == "status":
            projection["type"] = "artifact"

    text = _message_text_from_result(result)
    assistant_final = metadata.get("assistantFinal")
    if text and isinstance(assistant_final, dict) and assistant_final.get("complete") is True:
        projection["type"] = "assistant-final"
        projection["finalText"] = sanitize_text(text, MAX_FINAL_TEXT_BYTES, True)
        projection["finalTextComplete"] = len(text.encode("utf-8")) <= MAX_FINAL_TEXT_BYTES
    elif text:
        # Store only a small snapshot in job state. Token deltas are not spooled
        # or returned to the outer Agent as individual events.
        projection["latestText"] = sanitize_text(text, 1000, True)

    raw_error = payload.get("error")
    if not isinstance(raw_error, dict):
        raw_error = result.get("error") if isinstance(result.get("error"), dict) else None
    if isinstance(raw_error, dict):
        projection["type"] = "failed"
        projection["state"] = "failed"
        backup_not_ready = _session_backup_not_ready_error(raw_error)
        if backup_not_ready is not None:
            projection["error"] = {
                "code": backup_not_ready.code,
                "message": backup_not_ready.message,
                "retryable": True,
            }
        else:
            projection["error"] = {
                "code": sanitize_text(
                    str(raw_error.get("code") or raw_error.get("Code") or "StartChatFailed"), 160
                ),
                "message": sanitize_text(
                    str(raw_error.get("message") or raw_error.get("Message") or "StartChat failed."), 2000
                ),
            }
    elif state in TERMINAL_STATES:
        projection["type"] = "terminal"

    return _bound_projection(projection)


def _without_wait_boundaries(projection: Dict[str, Any]) -> Dict[str, Any]:
    projection = dict(projection)
    for key in ("inputRequired", "pendingPermissions", "permissionWait", "permissionRecovered"):
        projection.pop(key, None)
    if projection.get("type") in {"input-required", "permission-wait", "permission-recovered"}:
        projection["type"] = "status"
    return projection


def _project_managed_stream_event(
    payload: Dict[str, Any],
    summary: StreamSummary,
    mode: str,
    request_seq: int,
    worker_role: str,
    worker_token: Optional[str],
) -> Dict[str, Any]:
    projection = _project_stream_event(payload, mode, request_seq, worker_role, worker_token)
    if summary.state in TERMINAL_STATES:
        projection = _without_wait_boundaries(projection)
    return projection


def _append_projection(job_id: str, projection: Dict[str, Any]) -> None:
    root, job_path, spool = _job_paths(job_id)
    _secure_directory(root)
    projection = _bound_projection(projection)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        request_seq = projection.get("requestSeq")
        if isinstance(request_seq, int) and request_seq != job.get("activeRequestSeq"):
            return
        worker_role = projection.get("workerRole")
        worker_token = projection.get("workerToken")
        if worker_role == "sideband" and worker_token != job.get("sidebandWorkerToken"):
            return
        projection_error = projection.get("error")
        if (
            worker_role != "sideband"
            and isinstance(job.get("permissionResponseInput"), dict)
            and isinstance(projection_error, dict)
            and projection_error.get("code") == SESSION_BACKUP_NOT_READY_CODE
            and projection_error.get("retryable") is True
        ):
            projection["type"] = "input-required"
            projection["state"] = "input-required"
            projection["inputRequired"] = job["permissionResponseInput"]
        primary_terminal = job.get("primaryStreamTerminalSeen") is True or job.get("state") in TERMINAL_STATES
        if primary_terminal:
            projection = _without_wait_boundaries(projection)
        if projection.get("type") == "terminal" and worker_role != "sideband":
            # Do not publish an incomplete final result before EOF, but close
            # the primary stream's user-input ownership immediately. The
            # internal marker also prevents a concurrent sideband worker from
            # reopening the parent Pipeline while the primary worker exits.
            projection = _without_wait_boundaries(projection)
            job["primaryStreamTerminalSeen"] = True
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
            job.pop("permissionWait", None)
        identity_changed = False
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            value = projection.get(key)
            if isinstance(value, str) and value and job.get(key) != value:
                job[key] = value
                identity_changed = True
        latest_text = projection.get("latestText")
        if isinstance(latest_text, str) and latest_text:
            job["latestText"] = latest_text
        projected_ack = projection.get("permissionAck")
        effective_ack = projected_ack if isinstance(projected_ack, dict) else job.get("permissionAck")
        in_flight_input_id = job.get("sidebandResponseInputId")
        acknowledged_input_ids = {value for value in job.get("acknowledgedPermissionIds", []) if isinstance(value, str)}
        if isinstance(effective_ack, dict) and isinstance(effective_ack.get("inputId"), str):
            acknowledged_input_ids.add(effective_ack["inputId"])
        seen_sideband_input_ids = {
            value for value in job.get("seenSidebandPermissionIds", []) if isinstance(value, str)
        }
        resolved_sideband_input_ids = {
            value for value in job.get("resolvedSidebandPermissionIds", []) if isinstance(value, str)
        }
        resolved_sideband_input_ids.update(acknowledged_input_ids)
        if isinstance(projection.get("pendingPermissions"), list):
            projected_pending_ids = {
                value.get("inputId")
                for value in projection["pendingPermissions"]
                if isinstance(value, dict) and isinstance(value.get("inputId"), str)
            }
            resolved_sideband_input_ids.update(seen_sideband_input_ids - projected_pending_ids)
            seen_sideband_input_ids.update(projected_pending_ids)
            job["seenSidebandPermissionIds"] = list(seen_sideband_input_ids)[-64:]
            job["resolvedSidebandPermissionIds"] = list(resolved_sideband_input_ids)[-64:]
            pending = [
                value
                for value in projection["pendingPermissions"]
                if not _permission_is_acknowledged(value, effective_ack)
                and value.get("inputId") != in_flight_input_id
                and value.get("inputId") not in acknowledged_input_ids
                and value.get("inputId") not in resolved_sideband_input_ids
            ]
            projection["pendingPermissions"] = pending
            if pending:
                job["pendingPermissions"] = pending
                current = job.get("inputRequired")
                pending_ids = {value.get("inputId") for value in pending if isinstance(value, dict)}
                if not isinstance(current, dict) or current.get("inputId") not in pending_ids:
                    job["inputRequired"] = pending[0]
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("permissionClass") == "sub_pipeline":
                    job.pop("inputRequired", None)
        input_required = projection.get("inputRequired")
        current_input = job.get("inputRequired")
        if (
            isinstance(input_required, dict)
            and isinstance(current_input, dict)
            and input_required.get("inputId") == current_input.get("inputId")
            and current_input.get("permissionClass") == "sub_pipeline"
        ):
            input_required = dict(input_required)
            input_required["permissionClass"] = "sub_pipeline"
            projection["inputRequired"] = input_required
        if isinstance(input_required, dict) and input_required.get("inputId") in resolved_sideband_input_ids:
            projection.pop("inputRequired", None)
            if projection.get("type") == "input-required":
                projection["type"] = "status"
        elif isinstance(input_required, dict) and input_required.get("inputId") == in_flight_input_id:
            projection.pop("inputRequired", None)
            if projection.get("type") == "input-required":
                projection["type"] = "status"
        elif _permission_is_acknowledged(input_required, effective_ack) or (
            isinstance(input_required, dict) and input_required.get("inputId") in acknowledged_input_ids
        ):
            projection.pop("inputRequired", None)
            if projection.get("type") == "input-required":
                projection["type"] = "permission-ack" if isinstance(projected_ack, dict) else "status"
        elif isinstance(input_required, dict):
            job["inputRequired"] = input_required
            job["state"] = "input-required"
        permission_wait = projection.get("permissionWait")
        if isinstance(permission_wait, dict):
            job["permissionWait"] = permission_wait
        permission_recovered = projection.get("permissionRecovered")
        if isinstance(permission_recovered, dict):
            job["permissionRecovered"] = permission_recovered
            job.pop("permissionWait", None)
            recovered_input_id = permission_recovered.get("inputId")
            current = job.get("inputRequired")
            if isinstance(current, dict) and current.get("inputId") == recovered_input_id:
                job.pop("inputRequired", None)
            remaining = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") != recovered_input_id
            ]
            if remaining:
                job["pendingPermissions"] = remaining
            else:
                job.pop("pendingPermissions", None)
            if job.get("state") == "input-required" and not isinstance(job.get("inputRequired"), dict):
                job["state"] = "working"
        permission_ack = projection.get("permissionAck")
        if isinstance(permission_ack, dict):
            job["permissionAck"] = permission_ack
            input_id = permission_ack.get("inputId")
            if isinstance(input_id, str):
                history = job.setdefault("acknowledgedPermissionIds", [])
                if input_id not in history:
                    history.append(input_id)
                    del history[:-64]
            remaining = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") != input_id
            ]
            if remaining:
                job["pendingPermissions"] = remaining
                job["inputRequired"] = remaining[0]
                job["state"] = "input-required"
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("inputId") == input_id:
                    job.pop("inputRequired", None)
                if worker_role == "sideband" and job.get("state") not in TERMINAL_STATES:
                    job["state"] = "working"
        artifact = projection.get("artifact")
        if isinstance(artifact, dict):
            artifacts = job.setdefault("artifacts", [])
            if artifact not in artifacts:
                artifacts.append(artifact)
                del artifacts[:-24]
        if projection.get("type") == "assistant-final" and isinstance(projection.get("finalText"), str):
            job["assistantFinal"] = projection["finalText"]
            job["assistantFinalComplete"] = projection.get("finalTextComplete") is True
        if projection.get("type") == "failed" and worker_role == "sideband":
            job["sidebandError"] = projection.get("error")
        elif projection.get("type") == "failed":
            job["state"] = "failed"
            job["error"] = projection.get("error")
        if projection.get("normalHandoffReady") is True and job.get("mode") == "pipeline":
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"

        wire_projection = dict(projection)
        wire_projection.pop("latestText", None)
        wire_projection.pop("workerRole", None)
        wire_projection.pop("workerToken", None)
        meaningful = wire_projection.get("type") != "status" or identity_changed
        if meaningful:
            data = _json_bytes(wire_projection) + b"\n"
            current_size = spool.stat().st_size if spool.exists() else 0
            if current_size + len(data) > MAX_SPOOL_BYTES:
                raise BridgeError("stream_failed", "The bounded ROS Agent event spool is full.")
            with spool.open("ab") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if os.name != "nt":
                os.chmod(str(spool), 0o600)
        _atomic_json(job_path, job)


def _finish_job(
    job_id: str,
    request_seq: int,
    result: Dict[str, Any],
    worker_pid: int,
    expected_worker_pid: Optional[int] = None,
) -> bool:
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if job.get("activeRequestSeq") != request_seq:
            return False
        if expected_worker_pid is not None:
            current_worker_pid = job.get("workerPid")
            worker_matches = (
                not isinstance(current_worker_pid, int)
                if expected_worker_pid == 0
                else current_worker_pid == expected_worker_pid
            )
            if (
                not worker_matches
                or job.get("state") in TERMINAL_STATES | {"turn-completed", "failed"}
                or isinstance(job.get("inputRequired"), dict)
            ):
                return False
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            value = result.get(key)
            if isinstance(value, str) and value:
                job[key] = value
        state = result.get("state") if isinstance(result.get("state"), str) else "stream-ended"
        error = result.get("error")
        retry_permission = (
            isinstance(job.get("permissionResponseInput"), dict)
            and isinstance(error, dict)
            and error.get("code") == SESSION_BACKUP_NOT_READY_CODE
            and error.get("retryable") is True
        )
        if retry_permission:
            state = "input-required"
            job["inputRequired"] = job["permissionResponseInput"]
        elif state == "input-required":
            input_required = result.get("inputRequired")
            acknowledged_input_ids = {
                value for value in job.get("acknowledgedPermissionIds", []) if isinstance(value, str)
            }
            pending_permissions = [
                value
                for value in result.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") not in acknowledged_input_ids
            ]
            stale_sideband_input = (
                isinstance(input_required, dict)
                and input_required.get("permissionClass") == "sub_pipeline"
                and input_required.get("inputId") in acknowledged_input_ids
            )
            if isinstance(input_required, dict) and not stale_sideband_input:
                job["inputRequired"] = input_required
            elif pending_permissions:
                job["inputRequired"] = pending_permissions[0]
            else:
                job.pop("inputRequired", None)
            if pending_permissions:
                job["pendingPermissions"] = pending_permissions
            else:
                job.pop("pendingPermissions", None)
            if stale_sideband_input and not pending_permissions:
                state = "failed"
                job["error"] = {
                    "code": "stream_detached",
                    "message": "The parent Pipeline StartChat stream ended without a terminal result.",
                    "retryable": True,
                }
        elif state == "turn-completed":
            job["finalText"] = result.get("finalText", "")
            job["finalTextComplete"] = result.get("finalTextComplete") is True
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
        elif state in TERMINAL_STATES:
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
        if not retry_permission:
            job.pop("permissionResponseInput", None)
        if isinstance(result.get("pipelineResult"), dict):
            job["pipelineResult"] = result["pipelineResult"]
        if result.get("normalHandoffReady") is True and job.get("mode") == "pipeline":
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"
        if isinstance(result.get("permissionAck"), dict):
            job["permissionAck"] = result["permissionAck"]
        if isinstance(result.get("permissionWait"), dict):
            job["permissionWait"] = result["permissionWait"]
        if isinstance(result.get("permissionRecovered"), dict):
            job["permissionRecovered"] = result["permissionRecovered"]
            job.pop("permissionWait", None)
        if isinstance(result.get("error"), dict):
            job["error"] = result["error"]
        elif state == "failed" and not isinstance(job.get("error"), dict):
            failure_text = result.get("latestText") or job.get("latestText")
            job["error"] = {
                "code": "remote_task_failed",
                "message": sanitize_text(failure_text, 2000)
                if isinstance(failure_text, str) and failure_text
                else "The remote StartChat task failed without a structured error.",
            }
        if isinstance(result.get("artifacts"), list):
            artifacts = job.setdefault("artifacts", [])
            for artifact in result["artifacts"]:
                if isinstance(artifact, dict) and artifact not in artifacts:
                    artifacts.append(artifact)
            del artifacts[:-24]
        job["state"] = state
        job.pop("primaryStreamTerminalSeen", None)
        if state == "completed" and job.get("mode") == "pipeline":
            # Selling Pipeline publishes a normal-chat handoff before its
            # terminal event. Preserve a conservative fallback for gateways
            # that coalesce that event out of the final SSE projection.
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"
        job["workerExitedAt"] = int(time.time())
        if job.get("workerPid") == worker_pid:
            job.pop("workerPid", None)
        boundary = {
            "type": "result-boundary",
            "requestSeq": request_seq,
            "state": state,
            "time": int(time.time()),
        }
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            if isinstance(job.get(key), str):
                boundary[key] = job[key]
        data = _json_bytes(boundary) + b"\n"
        current_size = spool.stat().st_size if spool.exists() else 0
        if current_size + len(data) <= MAX_SPOOL_BYTES:
            with spool.open("ab") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        _atomic_json(job_path, job)
    _touch_manager_activity()
    return True


def _finish_sideband_job(
    job_id: str,
    request_seq: int,
    worker_token: str,
    result: Dict[str, Any],
    worker_pid: int,
) -> None:
    root, job_path, _spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if job.get("activeRequestSeq") != request_seq or job.get("sidebandWorkerToken") != worker_token:
            return
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            value = result.get(key)
            if isinstance(value, str) and value:
                job[key] = value

        expected_permission = job.get("sidebandResponse")
        expected_response = job.get("lastPermissionResponse")
        acknowledgement = result.get("permissionAck")
        acknowledged = (
            isinstance(expected_response, dict)
            and isinstance(acknowledgement, dict)
            and _permission_response_is_acknowledged(expected_response, acknowledgement)
        )
        if acknowledged:
            job["permissionAck"] = acknowledgement
            acknowledged_input_id = acknowledgement.get("inputId")
            if isinstance(acknowledged_input_id, str):
                history = job.setdefault("acknowledgedPermissionIds", [])
                if acknowledged_input_id not in history:
                    history.append(acknowledged_input_id)
                    del history[:-64]
                resolved = job.setdefault("resolvedSidebandPermissionIds", [])
                if acknowledged_input_id not in resolved:
                    resolved.append(acknowledged_input_id)
                    del resolved[:-64]

        parent_terminal = job.get("state") in TERMINAL_STATES or job.get("primaryStreamTerminalSeen") is True
        if acknowledged and not parent_terminal:
            input_id = acknowledgement.get("inputId")
            remaining = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") != input_id
            ]
            if remaining:
                job["pendingPermissions"] = remaining
                job["inputRequired"] = remaining[0]
                job["state"] = "input-required"
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("inputId") == input_id:
                    job.pop("inputRequired", None)
                if job.get("state") not in TERMINAL_STATES:
                    job["state"] = "working"
            job.pop("sidebandError", None)
        elif not acknowledged and not parent_terminal:
            if isinstance(expected_permission, dict):
                pending = [value for value in job.get("pendingPermissions", []) if isinstance(value, dict)]
                expected_input_id = expected_permission.get("inputId")
                if not any(value.get("inputId") == expected_input_id for value in pending):
                    pending.insert(0, expected_permission)
                job["pendingPermissions"] = pending
                job["inputRequired"] = expected_permission
                job["state"] = "input-required"
            raw_error = result.get("error")
            job["sidebandError"] = (
                raw_error
                if isinstance(raw_error, dict)
                else {
                    "code": "permission_not_acknowledged",
                    "message": "The Pipeline permission response ended without an accepted acknowledgement.",
                    "retryable": True,
                }
            )
        elif acknowledged:
            job.pop("sidebandError", None)

        result_state = result.get("state") if isinstance(result.get("state"), str) else None
        if (
            acknowledged
            and isinstance(expected_permission, dict)
            and expected_permission.get("permissionClass") == "pipeline"
            and not parent_terminal
            and result_state in TERMINAL_STATES | {"turn-completed"}
        ):
            # A top-level Pipeline permission response can carry the Pipeline's
            # terminal result on the sideband StartChat stream. Persist that
            # result so follow does not wait forever after both workers exit.
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
            job["state"] = result_state
            if result_state == "turn-completed":
                job["finalText"] = result.get("finalText", "")
                job["finalTextComplete"] = result.get("finalTextComplete") is True
            if isinstance(result.get("pipelineResult"), dict):
                job["pipelineResult"] = result["pipelineResult"]
            if result.get("normalHandoffReady") is True or (
                result_state == "completed" and job.get("mode") == "pipeline"
            ):
                job["normalHandoffReady"] = True
                job["conversationMode"] = "normal"
            if isinstance(result.get("error"), dict):
                job["error"] = result["error"]
            if isinstance(result.get("artifacts"), list):
                artifacts = job.setdefault("artifacts", [])
                for artifact in result["artifacts"]:
                    if isinstance(artifact, dict) and artifact not in artifacts:
                        artifacts.append(artifact)
                del artifacts[:-24]

        job["sidebandWorkerExitedAt"] = int(time.time())
        if job.get("sidebandWorkerPid") == worker_pid:
            job.pop("sidebandWorkerPid", None)
        job.pop("sidebandWorkerToken", None)
        job.pop("sidebandResponseInputId", None)
        job.pop("sidebandResponse", None)
        _atomic_json(job_path, job)
    _touch_manager_activity()


def _fail_job(
    job_id: str,
    request_seq: int,
    error: BridgeError,
    worker_pid: int,
    expected_worker_pid: Optional[int] = None,
) -> bool:
    result = {
        "ok": False,
        "state": "failed",
        "error": {
            "code": error.code,
            "message": sanitize_text(error.message, 3000),
            "retryable": error.retryable,
        },
    }
    return _finish_job(job_id, request_seq, result, worker_pid, expected_worker_pid)


def _fail_sideband_job(
    job_id: str,
    request_seq: int,
    worker_token: str,
    error: BridgeError,
    worker_pid: int,
) -> None:
    result = {
        "ok": False,
        "state": "failed",
        "error": {
            "code": error.code,
            "message": sanitize_text(error.message, 3000),
            "retryable": error.retryable,
        },
    }
    _finish_sideband_job(job_id, request_seq, worker_token, result, worker_pid)


def _read_spool(spool: pathlib.Path) -> List[Dict[str, Any]]:
    if not spool.exists():
        return []
    values = []
    with spool.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                values.append(value)
    return values


def _follow_timeout_result(job_id: str, start_cursor: int) -> Optional[Dict[str, Any]]:
    """Persist and snapshot the bounded observation returned by a timed-out follow call.

    The marker is local bridge state, not a StartChat query or a remote progress
    event.  Recording it gives each visible heartbeat a distinct spool cursor,
    so an outer headless Agent can continue observing a long-running Pipeline
    without issuing an identical tool call indefinitely.  The result snapshot
    stays under the same job lock so it cannot combine this cursor with a newer
    terminal or input boundary while omitting intervening step events.
    """

    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        values = _read_spool(spool)
        if job.get("state") in TERMINAL_STATES | {"turn-completed", "failed"} or isinstance(
            job.get("inputRequired"), dict
        ):
            return None
        if any(
            isinstance(milestone, dict) and milestone.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
            for item in values[max(0, int(start_cursor)) :]
            for milestone in item.get("milestones", [])
        ):
            return None
        marker = {
            "type": "follow-heartbeat",
            "requestSeq": job.get("activeRequestSeq"),
            "time": int(time.time()),
        }
        data = _json_bytes(marker) + b"\n"
        current_size = spool.stat().st_size if spool.exists() else 0
        if current_size + len(data) > MAX_SPOOL_BYTES:
            raise BridgeError("stream_failed", "The bounded ROS Agent event spool is full.")
        with spool.open("ab") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(str(spool), 0o600)
        return _job_result(
            job_id,
            start_cursor,
            len(values) + 1,
            boundary_reached=False,
            timed_out=True,
        )


def _coordinate_label(milestone: Dict[str, Any]) -> str:
    event_type = str(milestone.get("eventType") or "")
    if event_type.startswith("candidate_step_"):
        candidate = milestone.get("candidate")
        step = milestone.get("candidateStep") or milestone.get("step")
        candidate_name = ""
        if isinstance(candidate, dict):
            candidate_name = sanitize_text(candidate.get("name") or candidate.get("id"), 100)
        step_label = ""
        if isinstance(step, dict):
            step_label = sanitize_text(step.get("name") or step.get("id"), 100)
            index = step.get("index")
            total = step.get("total")
            if isinstance(index, int) and isinstance(total, int):
                step_label = "{}/{} {}".format(index, total, step_label).strip()
        if candidate_name and step_label:
            return "{} · {}".format(candidate_name, step_label)
        if candidate_name or step_label:
            return candidate_name or step_label
    for key in ("candidateStep", "step", "parentStep", "candidate"):
        value = milestone.get(key)
        if not isinstance(value, dict):
            continue
        name = sanitize_text(value.get("name") or value.get("id"), 120)
        index = value.get("index")
        total = value.get("total")
        if isinstance(index, int) and isinstance(total, int):
            return "{}/{} {}".format(index, total, name).strip()
        if name:
            return name
    return ""


def _format_conclusion(summary: Any, language: str) -> str:
    if not isinstance(summary, dict):
        return ""
    parts = []
    requirement = sanitize_text(summary.get("requirementSummary"), 180)
    region = sanitize_text(summary.get("region"), 80)
    if requirement:
        parts.append(requirement)
    if region:
        parts.append(("\u5730\u57df " if language == "zh" else "region ") + region)
    resources = summary.get("resources")
    if isinstance(resources, list):
        names = []
        for item in resources[:6]:
            if not isinstance(item, dict):
                continue
            product = sanitize_text(item.get("product"), 60)
            action = sanitize_text(item.get("action"), 32)
            if language == "zh":
                action = {
                    "create": "\u65b0\u5efa",
                    "use_existing": "\u590d\u7528",
                    "reference": "\u5f15\u7528",
                    "forbid": "\u7981\u6b62",
                }.get(action, action)
            if product:
                names.append("{} ({})".format(product, action) if action else product)
        if names:
            parts.append(("\u8d44\u6e90 " if language == "zh" else "resources ") + "\u3001".join(names))
    candidates = summary.get("candidates")
    if isinstance(candidates, list):
        names = []
        for item in candidates[:4]:
            if not isinstance(item, dict):
                continue
            name = sanitize_text(item.get("name"), 80)
            estimate = sanitize_text(item.get("monthlyEstimate"), 80)
            if name:
                names.append("{} ({})".format(name, estimate) if estimate else name)
        if names:
            count = summary.get("candidateCount")
            prefix = (
                "{} \u4e2a\u5019\u9009\u65b9\u6848 ".format(count)
                if language == "zh"
                else "{} candidates ".format(count)
            )
            parts.append(prefix + "\u3001".join(names))
    return sanitize_text(("\uff1b" if language == "zh" else "; ").join(parts), 520)


def _format_user_update(milestone: Dict[str, Any], language: str) -> str:
    event_type = milestone.get("eventType")
    detail = _coordinate_label(milestone) or sanitize_text(milestone.get("message"), 240)
    labels = {
        "zh": {
            "step_started": "\u6b65\u9aa4\u5f00\u59cb",
            "step_completed": "\u6b65\u9aa4\u5b8c\u6210",
            "step_failed": "\u6b65\u9aa4\u5931\u8d25",
            "candidate_step_started": "\u5019\u9009\u6b65\u9aa4\u5f00\u59cb",
            "candidate_step_completed": "\u5019\u9009\u6b65\u9aa4\u5b8c\u6210",
            "candidate_step_failed": "\u5019\u9009\u6b65\u9aa4\u5931\u8d25",
        },
        "en": {
            "step_started": "Step started",
            "step_completed": "Step completed",
            "step_failed": "Step failed",
            "candidate_step_started": "Candidate step started",
            "candidate_step_completed": "Candidate step completed",
            "candidate_step_failed": "Candidate step failed",
        },
    }
    label = labels.get(language, labels["en"]).get(str(event_type), sanitize_text(str(event_type), 80))
    separator = "\uff1a" if language == "zh" else ": "
    conclusion = _format_conclusion(milestone.get("conclusionSummary"), language)
    if conclusion:
        detail = "{}{}{}".format(
            detail,
            "\uff1b\u7ed3\u8bba\uff1a" if language == "zh" else "; conclusion: ",
            conclusion,
        )
    return sanitize_text(label + (separator + detail if detail else ""), 720)


def _bound_follow_result(result: Dict[str, Any]) -> Dict[str, Any]:
    while len(_json_bytes(result)) > MAX_FOLLOW_BYTES:
        milestones = result.get("milestones")
        artifacts = result.get("artifacts")
        if isinstance(milestones, list) and len(milestones) > 1:
            milestones.pop(0)
        elif isinstance(artifacts, list) and len(artifacts) > 1:
            artifacts.pop(0)
        elif isinstance(result.get("latestText"), str):
            result["latestText"] = _truncate_utf8(result["latestText"], 300)
        elif isinstance(result.get("finalText"), str) and len(result["finalText"].encode("utf-8")) > 2000:
            result["finalText"] = _truncate_utf8(result["finalText"], 2000)
            result["finalTextComplete"] = False
        else:
            raise BridgeError("stream_failed", "The ROS Agent follow result exceeded its bounded protocol.")
    return result


def _job_result(
    job_id: str,
    start_cursor: int,
    end_cursor: Optional[int] = None,
    boundary_reached: bool = False,
    timed_out: bool = False,
) -> Dict[str, Any]:
    _root, job_path, spool = _job_paths(job_id)
    job = _load_state_json(job_path)
    values = _read_spool(spool)
    start = max(0, int(start_cursor))
    end = len(values) if end_cursor is None else min(len(values), max(start, int(end_cursor)))
    unseen = values[start:end]
    milestones = []
    folded = {}  # type: Dict[str, int]
    seen = set()
    for item in unseen:
        item_seq = item.get("requestSeq")
        if isinstance(item_seq, int) and item_seq != job.get("activeRequestSeq"):
            folded["stale_request_event"] = folded.get("stale_request_event", 0) + 1
            continue
        for milestone in item.get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            signature = _json_bytes(milestone)
            if signature in seen:
                folded["duplicate_milestone"] = folded.get("duplicate_milestone", 0) + 1
                continue
            seen.add(signature)
            milestones.append(milestone)
    job_state = str(job.get("state") or "unknown")
    has_result_gate = job_state in TERMINAL_STATES | {"turn-completed", "failed"} or isinstance(
        job.get("inputRequired"), dict
    )
    state = job_state if has_result_gate else ("working" if boundary_reached else job_state)
    result = {
        "ok": state != "failed" and not isinstance(job.get("sidebandError"), dict),
        "jobId": job_id,
        "state": state,
        "mode": job.get("mode"),
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": end,
        "turn": int(job.get("turn") or 1),
        "milestones": milestones[-MAX_FOLLOW_EVENTS:],
        "folded": folded,
    }  # type: Dict[str, Any]
    for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
        if isinstance(job.get(key), str):
            result[key] = job[key]
    if job.get("conversationMode") in SUPPORTED_AGENT_MODES:
        result["conversationMode"] = job["conversationMode"]
    if job.get("normalHandoffReady") is True:
        result["normalHandoffReady"] = True
    if isinstance(job.get("permissionWait"), dict):
        result["permissionWait"] = job["permissionWait"]
        result["presentationRequired"] = True
    if isinstance(job.get("permissionRecovered"), dict):
        result["permissionRecovered"] = job["permissionRecovered"]
        result["presentationRequired"] = True
    if boundary_reached:
        updates = [
            _format_user_update(value, result["preferredLanguage"])
            for value in result["milestones"]
            if value.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
        ]
        if updates:
            result["boundaryReached"] = True
            result["presentationRequired"] = True
            result["userUpdates"] = updates
    artifacts = list(job.get("artifacts") or [])[-MAX_FOLLOW_EVENTS:]
    if artifacts and not timed_out and (not boundary_reached or has_result_gate):
        result["artifacts"] = artifacts
    if isinstance(job.get("inputRequired"), dict):
        result["inputRequired"] = _permission_with_ref(job["inputRequired"])
        if isinstance(job.get("pendingPermissions"), list):
            result["pendingPermissions"] = [
                _permission_with_ref(value) for value in job["pendingPermissions"] if isinstance(value, dict)
            ]
        result["presentationRequired"] = True
    if state == "turn-completed":
        result["finalText"] = job.get("finalText", "")
        result["finalTextComplete"] = job.get("finalTextComplete") is True
        result["presentationRequired"] = True
    if state in TERMINAL_STATES and isinstance(job.get("pipelineResult"), dict):
        result["pipelineResult"] = job["pipelineResult"]
        result["presentationRequired"] = True
    if state == "failed" and isinstance(job.get("error"), dict):
        result["error"] = job["error"]
        result["presentationRequired"] = True
    elif isinstance(job.get("sidebandError"), dict):
        result["error"] = job["sidebandError"]
        result["presentationRequired"] = True
    if isinstance(job.get("permissionAck"), dict):
        result["permissionAck"] = job["permissionAck"]
        if state == "permission-responded":
            result["presentationRequired"] = True
    if timed_out:
        elapsed = max(0, int(time.time()) - int(job.get("turnStartedAt") or job.get("createdAt") or time.time()))
        result["followTimedOut"] = True
        result["heartbeat"] = (
            "ROS Agent \u4ecd\u5728\u5904\u7406\u4e2d\uff08{} \u79d2\uff09\u3002".format(elapsed)
            if result["preferredLanguage"] == "zh"
            else "ROS Agent is still working ({}s).".format(elapsed)
        )
        result["presentationRequired"] = True
        if isinstance(job.get("latestText"), str):
            result["latestText"] = job["latestText"]
    return _bound_follow_result(result)


def _follow_ready_result(job_id: str, start_cursor: int) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        values = _read_spool(spool)
        job = _load_state_json(job_path)
        has_step_boundary = any(
            isinstance(milestone, dict) and milestone.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
            for item in values[start_cursor:]
            for milestone in item.get("milestones", [])
        )
        state = job.get("state")
        if (
            has_step_boundary
            or state in TERMINAL_STATES | {"turn-completed", "failed"}
            or isinstance(job.get("inputRequired"), dict)
            or isinstance(job.get("sidebandError"), dict)
        ):
            return (
                _job_result(
                    job_id,
                    start_cursor,
                    len(values),
                    boundary_reached=has_step_boundary,
                ),
                job,
            )
        if state == "permission-responded" and job.get("pendingPermissions"):
            return _job_result(job_id, start_cursor, len(values)), job
        return None, job


def _follow_job_local(job_id: str, cursor: int, wait_seconds: float) -> Dict[str, Any]:
    root = _job_paths(job_id)[0]
    _secure_directory(root)
    wait_seconds = max(0.0, min(float(wait_seconds), MAX_FOLLOW_SECONDS))
    deadline = time.monotonic() + wait_seconds
    start_cursor = max(0, int(cursor))
    while True:
        ready_result, job = _follow_ready_result(job_id, start_cursor)
        if ready_result is not None:
            return ready_result
        state = job.get("state")
        sideband_worker_pid = job.get("sidebandWorkerPid")
        sideband_worker_token = job.get("sidebandWorkerToken")
        if (
            isinstance(sideband_worker_pid, int)
            and isinstance(sideband_worker_token, str)
            and not _pid_alive(sideband_worker_pid)
        ):
            error = BridgeError(
                "worker_exited", "The Pipeline permission response worker exited before acknowledgement.", True
            )
            _fail_sideband_job(
                job_id,
                int(job.get("activeRequestSeq") or 0),
                sideband_worker_token,
                error,
                sideband_worker_pid,
            )
            continue
        worker_pid = job.get("workerPid")
        if isinstance(worker_pid, int) and not _pid_alive(worker_pid):
            error = BridgeError("worker_exited", "The StartChat worker exited before reaching a boundary.", True)
            _fail_job(
                job_id,
                int(job.get("activeRequestSeq") or 0),
                error,
                worker_pid,
                expected_worker_pid=worker_pid,
            )
            continue
        if state == "permission-responded" and not isinstance(worker_pid, int):
            error = BridgeError(
                "stream_detached",
                "Permission was accepted, but the StartChat stream ended before the next Pipeline boundary.",
                True,
            )
            _fail_job(
                job_id,
                int(job.get("activeRequestSeq") or 0),
                error,
                0,
                expected_worker_pid=0,
            )
            continue
        if time.monotonic() >= deadline:
            timeout_result = _follow_timeout_result(job_id, start_cursor)
            if timeout_result is None:
                continue
            return timeout_result
        time.sleep(0.1)
