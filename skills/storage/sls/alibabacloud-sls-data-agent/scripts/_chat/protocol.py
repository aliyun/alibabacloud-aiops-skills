"""SLS event decoding and shared result reduction.

The envelope and root/text rules come from the pinned Chat reference. Reconnect
requires the observed full-turn user origin and a closed replay, in addition to
the shared business outcome rules. A single user_ack yes submission is verified
against deployed SLS; other interaction response types still need live samples.
"""
from __future__ import annotations

import copy
import io
import json
from dataclasses import dataclass

from .inputs import InputError


MAX_RESULT_BYTES = 16 * 1024 * 1024
HIL_FIELDS = {"user_ack": "userAck", "user_input": "userInput",
              "ask_user_question": "askUserQuestion"}


def error(kind, code, message, phase):
    return {"kind": kind, "code": code, "message": message, "phase": phase}


def _string(value):
    return isinstance(value, str) and bool(value)


def _source(payload):
    """Only explicitly represented source objects; never reconstruct identities."""
    if not isinstance(payload, dict):
        raise ValueError("interaction payload is not an object")
    sources = []
    if "source" in payload:
        sources.append(payload["source"])
    for key in ("userAck", "userInput", "askUserQuestion"):
        if key in payload:
            item = payload[key]
            if not isinstance(item, dict) or "source" not in item:
                raise ValueError("interaction source is missing")
            sources.append(item["source"])
    if len(sources) != 1 or not isinstance(sources[0], dict):
        raise ValueError("interaction source is ambiguous or missing")
    source = sources[0]
    if not all(_string(source.get(key)) for key in ("type", "id", "callId")):
        raise ValueError("interaction source identity is incomplete")
    return source


def _hil_source(payload):
    """Only the three source-defined suspension types can await a user reply."""
    kind = payload.get("type") if isinstance(payload, dict) else None
    field = HIL_FIELDS.get(kind) if _string(kind) else None
    if field is None or not isinstance(payload.get(field), dict):
        raise ValueError("interaction is not a supported HIL request")
    return _source(payload)


def _query_display(payload):
    # QueryExtractor duplicates a query from the final answer. Other display
    # events can carry independent preview data, files, or images; do not drop
    # those outputs or treat their open payloads as replyable HIL requests.
    return (set(payload) == {"type", "queries"} and isinstance(payload["queries"], list) and
            all(isinstance(query, dict) and set(query) == {"datasource", "query"} and
                all(isinstance(query[field], str) for field in ("datasource", "query"))
                for query in payload["queries"]))


def interaction_key(item):
    if not isinstance(item, dict) or not _string(item.get("callId")):
        raise ValueError("interaction callId is missing")
    if "parentCallId" not in item or not isinstance(item["parentCallId"], str):
        raise ValueError("interaction parentCallId is missing")
    source = _source(item.get("payload"))
    if "source" in item and item["source"] != source:
        raise ValueError("interaction source disagrees with its payload")
    return (item["callId"], item["parentCallId"], source["type"], source["id"], source["callId"])


def validate_context(context):
    if not isinstance(context, dict) or not _string(context.get("threadId")):
        raise InputError("INVALID_CONTEXT", "Context must identify the actual thread.")
    items = context.get("interactions")
    if not isinstance(items, list) or not items:
        raise InputError("INVALID_CONTEXT", "Context must contain the complete nonempty pending interaction set.")
    seen = set()
    try:
        for item in items:
            _hil_source(item.get("payload") if isinstance(item, dict) else None)
            key = interaction_key(item)
            if key in seen:
                raise ValueError("duplicate interaction identity")
            seen.add(key)
    except ValueError:
        raise InputError("INVALID_CONTEXT", "Context has an incomplete or conflicting interaction association.") from None
    return copy.deepcopy(items)


def validate_result(result, interactions):
    if not isinstance(result, dict) or set(result) != {"index", "result"}:
        raise InputError("INVALID_RESULT", "Interaction result must be one JSON object containing only index and result.")
    if type(result["index"]) is not int or result["index"] < 0:
        raise InputError("INVALID_RESULT", "Interaction index must be a nonnegative integer.")
    if not isinstance(interactions, list) or not interactions:
        raise InputError("INVALID_CONTEXT", "A nonempty complete interaction set is required.")
    if result["index"] >= len(interactions):
        raise InputError("INVALID_RESULT", "Interaction index must select the current context interaction array.")


def _result_fields(result, allowed):
    if (not isinstance(result, dict) or set(result) - allowed or
            not isinstance(result.get("decision"), str)):
        raise InputError("INVALID_RESULT", "Result must contain an explicit decision and only fields supported by this interaction type.")
    if "feedback" in result and not isinstance(result["feedback"], str):
        raise InputError("INVALID_RESULT", "Interaction feedback must be a string.")


def _ack_result(body, result):
    _result_fields(result, {"decision", "feedback"})
    options = body.get("options")
    if not isinstance(options, list) or not options:
        raise InputError("INVALID_CONTEXT", "User acknowledgement options are missing or malformed.")
    values = set()
    for option in options:
        if (not isinstance(option, dict) or not isinstance(option.get("value"), str) or
                option["value"] not in ("yes", "no") or
                option["value"] in values):
            raise InputError("INVALID_CONTEXT", "User acknowledgement options do not match the supported yes/no contract.")
        values.add(option["value"])
    if result["decision"] not in values:
        raise InputError("INVALID_RESULT", "Decision must select an observed yes/no acknowledgement option.")
    return copy.deepcopy(result)


def _input_result(result):
    _result_fields(result, {"decision", "formData", "feedback"})
    decision = result["decision"]
    if decision not in ("submit", "cancel"):
        raise InputError("INVALID_RESULT", "User input decision must be submit or cancel.")
    if decision == "submit" and not isinstance(result.get("formData"), dict):
        raise InputError("INVALID_RESULT", "Submitting user input requires a formData object.")
    if decision == "cancel" and "formData" in result:
        raise InputError("INVALID_RESULT", "Cancelling user input must not submit formData.")
    # UserInputPayload.formSpec is an open rendering object, not a declared JSON
    # Schema. This encoder validates the response envelope, not renderer rules.
    return copy.deepcopy(result)


def _question_result(body, result):
    _result_fields(result, {"decision", "answers", "feedback"})
    decision = result["decision"]
    if decision not in ("yes", "no"):
        raise InputError("INVALID_RESULT", "Question decision must be yes or no.")
    questions = body.get("questions")
    if not isinstance(questions, list) or not questions:
        raise InputError("INVALID_CONTEXT", "Question identities are missing or malformed.")
    question_ids = set()
    for question in questions:
        question_id = question.get("id") if isinstance(question, dict) else None
        if not isinstance(question_id, str) or not question_id.strip() or question_id in question_ids:
            raise InputError("INVALID_CONTEXT", "Question identities must be explicit and unique.")
        question_ids.add(question_id)
    mapped = {"decision": decision}
    if "feedback" in result:
        mapped["feedback"] = result["feedback"]
    if decision == "no":
        if "answers" in result:
            raise InputError("INVALID_RESULT", "Rejecting questions must not submit answers.")
        return copy.deepcopy(mapped)
    answers = result.get("answers")
    if not isinstance(answers, list) or not answers:
        raise InputError("INVALID_RESULT", "Accepting questions requires a nonempty answers array.")
    answered = set()
    for answer in answers:
        if (not isinstance(answer, dict) or set(answer) - {"questionId", "answer", "userInput"} or
                not isinstance(answer.get("questionId"), str) or
                answer["questionId"] not in question_ids or answer["questionId"] in answered or
                not {"answer", "userInput"}.intersection(answer) or
                ("answer" in answer and not isinstance(answer["answer"], dict)) or
                ("userInput" in answer and not isinstance(answer["userInput"], str))):
            raise InputError("INVALID_RESULT", "Each answer must select a unique observed question and provide an answer object or userInput string.")
        answered.add(answer["questionId"])
    mapped["modifiedData"] = {"answers": answers}
    return copy.deepcopy(mapped)


def encode_result(interactions, supplied):
    """Build one source-derived reply; only user_ack yes has live SLS evidence.

    UserInteractiveResponseContext and the Agent HIL validation define the wire
    fields. Call and source identities come exclusively from the selected saved
    event; the caller supplies only an explicit decision and business answers.
    Inputs must already be strictly parsed JSON from the public input boundary.
    """
    validate_result(supplied, interactions)
    item = interactions[supplied["index"]]
    try:
        source = _hil_source(item.get("payload") if isinstance(item, dict) else None)
        interaction_key(item)
    except ValueError:
        raise InputError("INVALID_CONTEXT", "Selected interaction has an unsupported type or incomplete association.") from None
    payload = item["payload"]
    kind = payload["type"]
    result = supplied["result"]
    if kind == "user_ack":
        mapped = _ack_result(payload["userAck"], result)
    elif kind == "user_input":
        mapped = _input_result(result)
    elif kind == "ask_user_question":
        mapped = _question_result(payload["askUserQuestion"], result)
    else:
        raise InputError("INVALID_CONTEXT", "Selected interaction type is unsupported.")
    return {"callId": item["callId"], "source": copy.deepcopy(source), **mapped}


@dataclass
class Message:
    call_id: object
    parent_id: object
    role: str
    text: list
    events: list
    tools: list
    has_calls: bool
    summary: str | None
    unknown_artifacts: bool


def _artifact_read_path(raw, thread_id):
    """Accept only the verified current-thread artifact namespace, without rewriting."""
    if not isinstance(raw, str) or not raw.startswith("/home/starops/threads/") or "artifacts" not in raw.split("/"):
        return None  # Ordinary Read calls are not artifact events.
    if (not _string(thread_id) or thread_id in (".", "..") or
            any(char in thread_id for char in "/\\")):
        raise ValueError("invalid artifact thread")
    prefix = "/home/starops/threads/" + thread_id + "/artifacts/"
    logical = raw.removeprefix("/home/starops/")
    if (not raw.startswith(prefix) or raw.endswith("/") or raw != raw.strip() or
            "\\" in raw or ".." in raw or "//" in raw or "." in raw.split("/") or
            any(ord(char) < 0x20 or ord(char) == 0x7f for char in raw) or
            len(logical.encode("utf-8")) > 1024):
        raise ValueError("invalid artifact path")
    return logical


def decode_artifacts(artifacts, role):
    """Classify only verified non-file artifacts; do not invent download paths.

    The console history sample and protocol mapper use Result for a duplicate
    final text, variables for session metadata, and AutoPassRule for a snapshot.
    None of those objects is a file reference or an instruction to approve.
    """
    summary, unknown = None, False
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("parts"), list):
            raise ValueError("invalid artifact")
        parts, name = artifact["parts"], artifact.get("name")
        data_parts = bool(parts) and all(isinstance(p, dict) and p.get("kind") == "data" and
                                       isinstance(p.get("data"), dict) for p in parts)
        if role == "user" and name == "variables" and data_parts and all(
                isinstance(p["data"].get("variables"), str) for p in parts):
            continue
        if role == "system" and name == "AutoPassRule" and data_parts and all(
                isinstance(p["data"].get("rules"), list) for p in parts):
            continue
        final = isinstance(artifact.get("metadata"), dict) and artifact["metadata"].get("is_final") is True
        if role == "system" and name == "Result" and final and parts and all(
                isinstance(p, dict) and p.get("kind") == "text" and isinstance(p.get("text"), str)
                for p in parts):
            candidate = "".join(p["text"] for p in parts)
            if summary is not None and summary != candidate:
                raise ValueError("conflicting final artifacts")
            summary = candidate
        else:
            unknown = True
    return summary, unknown


def decode_message(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("role"), str):
        raise ValueError("invalid message")
    contents, events, artifacts = (raw.get(key, []) for key in ("contents", "events", "artifacts"))
    if not all(isinstance(items, list) for items in (contents, events, artifacts)):
        raise ValueError("invalid message collections")
    text, content_errors = [], []
    for part in contents:
        if not isinstance(part, dict):
            raise ValueError("invalid content")
        if part.get("type") == "text":
            if not isinstance(part.get("value"), str):
                raise ValueError("invalid text")
            if any(key in part and type(part[key]) is not bool for key in ("append", "lastChunk")):
                raise ValueError("invalid text flags")
            text.append((part["value"], part.get("append", True), part.get("lastChunk", False)))
        elif part.get("type") == "error":
            content_errors.append({"type": "error", "payload": part.get("value")})
    if content_errors:
        events = events + content_errors
    normalized_events = []
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("invalid event")
        normalized_events.append((event["type"], event.get("payload")))
    for key in ("tools", "agents"):
        if key in raw and not isinstance(raw[key], list):
            raise ValueError("invalid call collection")
    summary, unknown_artifacts = decode_artifacts(artifacts, raw["role"])
    return Message(raw.get("callId"), raw.get("parentCallId"), raw["role"],
                   text, normalized_events, raw.get("tools", []), bool(raw.get("tools") or raw.get("agents")),
                   summary, unknown_artifacts)


def decode_record(record):
    if not isinstance(record, dict):
        raise ValueError("invalid CLI envelope")
    # The installed plugin omits event for an unnamed SSE data frame.
    kind, data = record.get("event", "message"), record.get("data")
    if not isinstance(kind, str):
        raise ValueError("invalid CLI event name")
    if kind in ("ping", "heartbeat", "stream_done") and data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("invalid event data")
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        raise ValueError("invalid message list")
    return kind, data, [decode_message(item) for item in messages]


class Reply:
    def __init__(self, thread_id, message_id=None, interactions=None, *, reconnect=False, target=None,
                 expected_root=None):
        self.identifiers = {"threadId": thread_id}
        self.observed_ids = {}
        self.ambiguous_ids = set()
        if message_id:
            self.identifiers["messageId"] = message_id
        self.pending = {}
        self.pending_sizes = {}
        self.pending_bytes = 0
        for item in interactions or []:
            _hil_source(item.get("payload") if isinstance(item, dict) else None)
            self._keep_pending(interaction_key(item), copy.deepcopy(item))
        self.root_id = None
        self.body_scope = None
        self.control_roots = {}
        self.summary = None
        self.terminals = set()
        self._text = io.StringIO()
        self.closed_text = False
        self.artifacts = []
        self.artifact_reads = {}
        self.artifact_paths = set()
        self.artifact_bytes = 0
        self.target = {key: target[key] for key in ("region", "name") if isinstance(target, dict) and key in target}
        self.service_error = None
        self.request_error = False
        self.problem = None
        self.stream_done = False
        self.reconnect = reconnect
        self.expected_root = expected_root
        self.expected_response = None
        self.response_conflict = False
        self.replay_origin = None
        self.result_bytes = 0

    @property
    def answer(self):
        return self._text.getvalue()

    def _keep_pending(self, key, item):
        size = len(json.dumps(item, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        total = self.pending_bytes - self.pending_sizes.get(key, 0) + size
        if total > MAX_RESULT_BYTES:
            raise ValueError("pending interactions exceed the result budget")
        self.pending[key] = item
        self.pending_sizes[key] = size
        self.pending_bytes = total

    def expect_response(self, item, encoded):
        """Remember the actual submitted reply without treating it as accepted."""
        try:
            key = interaction_key(item)
            response_key = interaction_key({"callId": encoded.get("callId"),
                                            "parentCallId": item["parentCallId"],
                                            "payload": encoded})
            if key not in self.pending or response_key != key:
                raise ValueError("submitted response does not match a pending item")
            self._confirmation_decision(encoded, self.pending[key])
        except (AttributeError, TypeError, ValueError):
            raise InputError("INVALID_CONTEXT", "Submitted interaction response does not match the selected pending item.") from None
        self.expected_response = (key, copy.deepcopy(encoded))

    def _confirmation_decision(self, payload, pending):
        decision = payload.get("decision")
        if not isinstance(decision, str) or decision not in ("yes", "no", "submit", "cancel"):
            raise ValueError("interaction response decision is missing or invalid")
        if pending is not None:
            kind = pending["payload"]["type"]
            allowed = ("submit", "cancel") if kind == "user_input" else ("yes", "no")
            if decision not in allowed:
                raise ValueError("interaction response decision disagrees with its pending type")
        for field in ("formData", "modifiedData"):
            if field in payload and not isinstance(payload[field], dict):
                raise ValueError("interaction response business data is not an object")
        if "feedback" in payload and not isinstance(payload["feedback"], str):
            raise ValueError("interaction response feedback is not a string")

    @staticmethod
    def _same_response_value(expected, actual):
        # Go may re-encode a JSON number such as 1.0 as 1. Booleans must still
        # remain distinct from numbers, including inside open form/answer data.
        if type(expected) is bool or type(actual) is bool:
            return type(expected) is type(actual) and expected == actual
        if isinstance(expected, dict) and isinstance(actual, dict):
            return (set(expected) == set(actual) and all(
                Reply._same_response_value(value, actual[key]) for key, value in expected.items()))
        if isinstance(expected, list) and isinstance(actual, list):
            return (len(expected) == len(actual) and all(
                Reply._same_response_value(left, right) for left, right in zip(expected, actual)))
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return expected == actual
        return type(expected) is type(actual) and expected == actual

    def _response_agrees(self, key, payload):
        if self.expected_response is None or key != self.expected_response[0]:
            return True
        if self.response_conflict:
            return False
        expected = self.expected_response[1]
        for field in ("decision", "formData", "modifiedData", "feedback"):
            if field not in expected:
                if field in payload and not self._omittable_response_field(field, payload[field]):
                    return False
            elif field not in payload:
                # Go's omitempty can omit empty top-level maps and feedback;
                # nested empty values remain business data and must agree.
                if not self._omittable_response_field(field, expected[field]):
                    return False
            elif not self._same_response_value(expected[field], payload[field]):
                return False
        return True

    @staticmethod
    def _omittable_response_field(field, value):
        return ((field in ("formData", "modifiedData") and isinstance(value, dict) and not value) or
                (field == "feedback" and value == ""))

    def _read_artifact(self, message, tool):
        # Live SLS exposes Read's structured file_path and a later success with
        # the same frame/tool identity. Write arguments can be blank; its prose
        # and the Agent answer must never supply a guessed artifact path.
        if not isinstance(tool, dict) or tool.get("name") != "Read":
            return
        arguments = tool.get("arguments")
        raw_path = arguments.get("file_path") if isinstance(arguments, dict) else None
        try:
            path = _artifact_read_path(raw_path, self.identifiers.get("threadId"))
        except ValueError:
            self.unknown("INVALID_ARTIFACT_PATH", "A Read artifact path is outside the verified current-thread namespace.")
            return
        key = (message.call_id, message.parent_id, tool.get("toolCallId"))
        valid_key = (_string(message.call_id) and isinstance(message.parent_id, str) and
                     _string(key[2]))
        previous = self.artifact_reads.get(key) if valid_key else None
        if path is None and previous is None:
            return
        if not valid_key or message.role != "assistant":
            self.unknown("UNATTRIBUTED_ARTIFACT_READ", "An artifact Read lacks a complete frame and tool association.")
            return
        status = tool.get("status")
        omitted_path = not isinstance(arguments, dict) or "file_path" not in arguments
        if status == "start" and path is not None:
            if previous is not None:
                if previous[0] != path:
                    self.artifact_reads[key] = (previous[0], "conflict", previous[2])
                    self.unknown("CONFLICTING_ARTIFACT_READ", "The same Read identity names conflicting artifact paths.")
                return
            size = len(json.dumps([key, path, status], ensure_ascii=False).encode("utf-8"))
            if self.artifact_bytes + size > MAX_RESULT_BYTES:
                raise ValueError("artifact associations exceed the result budget")
            self.artifact_reads[key] = (path, status, size)
            self.artifact_bytes += size
        elif (status in ("progress", "fail", "success") and previous is not None and
              previous[1] == "start" and (omitted_path or path == previous[0])):
            if status == "progress":
                return  # Progress neither confirms nor invalidates the Read.
            path = previous[0]
            # Neither completed nor failed Reads need historical tool identities.
            self.artifact_reads.pop(key)
            self.artifact_bytes -= previous[2]
            if status == "fail":
                return  # A confirmed tool failure is not an unknown Chat outcome.
            if not all(_string(self.target.get(field)) for field in ("region", "name")):
                self.unknown("INCOMPLETE_ARTIFACT_TARGET", "An artifact reference requires the selected region and DataAgent name.")
                return
            if path not in self.artifact_paths:
                artifact = {"region": self.target["region"], "dataAgentName": self.target["name"],
                            "artifactPath": path,
                            "accessHint": "Preview or download this artifact from the thread artifact panel in the SLS console."}
                size = len(json.dumps(artifact, ensure_ascii=False).encode("utf-8"))
                if self.artifact_bytes + size > MAX_RESULT_BYTES:
                    raise ValueError("artifact references exceed the result budget")
                self.artifact_paths.add(path)
                self.artifacts.append(artifact)
                self.artifact_bytes += size
        else:
            self.unknown("UNCONFIRMED_ARTIFACT_READ", "An artifact Read has missing or conflicting start/result evidence.")

    def unknown(self, code, message, phase="read_stream"):
        if self.problem is None:
            self.problem = error("outcome_unknown", code, message, phase)

    def failed(self, code, message, phase="execution"):
        if self.service_error is None:
            self.service_error = error("remote_failed", code, message, phase)

    def _service_failure(self, payload, code, message):
        if isinstance(payload, dict):
            detail = payload.get("error", payload)
            if isinstance(detail, dict):
                self._ids(detail)
                if _string(detail.get("code")):
                    code = detail["code"][:200]
                if _string(detail.get("message")):
                    message = detail["message"][:2000]
        self.failed(code, message)

    def _ids(self, data):
        for key in ("requestId", "traceId"):
            value = data.get(key)
            if _string(value) and key not in self.identifiers and key not in self.ambiguous_ids:
                self.identifiers[key] = value

    def _observe_scope(self, data):
        # Frame metadata belongs to this transport request, including user/child
        # frames. A common callId cannot make mixed requests one execution.
        for key in ("requestId", "traceId"):
            value = data.get(key)
            if not _string(value):
                continue
            previous = self.observed_ids.get(key)
            if previous is not None and previous != value:
                self.ambiguous_ids.add(key)
                self.identifiers.pop(key, None)
                self.unknown("CROSS_REQUEST_OUTPUT", "Output contains conflicting request/trace associations.")
            else:
                self.observed_ids[key] = value

    def feed(self, record):
        try:
            kind, data, messages = decode_record(record)
            self._observe_scope(data)
            self._ids(data)
            if kind == "error" or data.get("error"):
                self.request_error = True
                self._service_failure(data, "CHAT_ERROR", "The service returned an explicit Chat error.")
            for message in messages:
                if self.reconnect:
                    if self.stream_done:
                        self.unknown("REPLAY_AFTER_STREAM_DONE", "Replay contains messages after its stream closure.")
                    self._replay_message(message)
                scope = (data.get("requestId"), data.get("traceId"))
                self._message(message, scope if all(_string(v) for v in scope) else None)
            if kind == "stream_done":
                self.stream_done = True
        except ValueError:
            self.unknown("INVALID_CHAT_EVENT", "A required Chat event field is invalid or missing.")

    def _replay_message(self, message):
        # Public replay starts at the original user message; create hides that
        # message. A spin_text, successful tail, or empty cold-node stream cannot
        # establish that the whole turn was delivered. Only the observed text
        # origin is supported; tools-only user origins need their own evidence.
        if self.replay_origin is None:
            self.replay_origin = (
                message.role == "user" and message.call_id == self.identifiers.get("threadId") and
                message.parent_id == "" and len(message.text) == 1 and
                bool(message.text[0][0].strip()) and message.text[0][1:] == (False, True) and
                not message.events and not message.has_calls)
        elif message.role == "user":
            self.unknown("CONFLICTING_REPLAY_ORIGIN", "Replay contains more than one original user message.")

    def _bind_root(self, message, scope):
        if message.role == "assistant":
            if self.reconnect and self.expected_root and self.expected_root != message.call_id:
                self.unknown("REPLAY_ROOT_MISMATCH", "Replay does not belong to the known original Agent execution.")
                return False
            if self.root_id is not None and self.root_id != message.call_id:
                self.unknown("AMBIGUOUS_ROOT", "Output contains more than one Agent root execution.")
                return False
            if self.body_scope is not None and scope is not None and self.body_scope != scope:
                self.unknown("CROSS_REQUEST_OUTPUT", "Root output contains conflicting request/trace associations.")
                return False
            self.root_id = message.call_id
            if scope is not None:
                self.body_scope = scope
        else:
            if message.call_id not in self.control_roots and len(self.control_roots) >= 2:
                self.unknown("AMBIGUOUS_ROOT", "Output contains ambiguous system root identities.")
                return False
            previous = self.control_roots.get(message.call_id)
            if previous is not None and scope is not None and previous != scope:
                self.unknown("CROSS_REQUEST_OUTPUT", "System output contains conflicting request/trace associations.")
                return False
            self.control_roots[message.call_id] = scope or previous
        if self.root_id is not None:
            for call_id, control_scope in self.control_roots.items():
                if self.body_scope is not None and control_scope is not None and self.body_scope != control_scope:
                    self.unknown("CROSS_REQUEST_OUTPUT", "Agent text and system terminal belong to different request/trace scopes.")
                    return False
                if call_id == self.root_id:
                    continue  # Explicitly the same root, not a field fallback.
                if call_id != self.identifiers.get("threadId"):
                    self.unknown("AMBIGUOUS_ROOT", "A system root cannot be associated with the Agent or thread.")
                    return False
                if self.body_scope is None or control_scope is None or self.body_scope != control_scope:
                    self.unknown("UNATTRIBUTED_THREAD_TERMINAL", "Thread and Agent roots lack a matching request/trace association.")
                    return False
        return True

    def _message(self, message, scope):
        root_evidence = message.text or message.summary is not None or any(
            kind in ("task_finished", "error", "stream_done")
            for kind, _ in message.events)
        consequential = root_evidence or any(
            kind in ("interactive", "interactive_response") for kind, _ in message.events)
        if message.role in ("assistant", "system") and consequential and (
                not _string(message.call_id) or not isinstance(message.parent_id, str)):
            self.unknown("INCOMPLETE_CALL_IDENTITY", "A consequential message cannot be attributed to a complete call identity.")
            return
        root = (_string(message.call_id) and message.parent_id == "" and
                message.role in ("assistant", "system"))
        # Live SLS sends thread-scoped assistant spin_text before the Agent run
        # exists. HIL cards use a separate confirmation ID even when their
        # parent is empty; neither they nor progress can claim the body root.
        if root and root_evidence:
            if not self._bind_root(message, scope):
                return
        for tool in message.tools:
            self._read_artifact(message, tool)
        for kind, payload in message.events:
            if self.reconnect and self.stream_done:
                self.unknown("REPLAY_AFTER_STREAM_DONE", "Replay contains events after its stream closure.")
                return
            if kind in ("interactive", "interactive_response"):
                self._interaction(message, kind, payload)
            elif root and kind == "stream_done":
                self.stream_done = True
            elif root and kind == "task_finished":
                if not isinstance(payload, dict) or type(payload.get("success")) is not bool:
                    raise ValueError("invalid terminal")
                self.terminals.add(payload["success"])
                self._ids(payload)
                if not payload["success"]:
                    self._service_failure(payload, "ROOT_FAILED", "The root Chat execution reported failure.")
            elif root and kind == "error":
                self.terminals.add(False)
                self._service_failure(payload, "ROOT_ERROR", "The root Chat execution returned an error.")
        if message.unknown_artifacts:
            # Public docs expose an open artifact object. Do not invent a stable
            # reference/download mapping or silently discard unknown artifacts.
            self.unknown("UNCONFIRMED_ARTIFACT_PROTOCOL", "Artifact references require a verified SLS field and access mapping.")
        if message.summary is not None:
            if not root or message.role != "system":
                self.unknown("UNATTRIBUTED_FINAL_ARTIFACT", "A final artifact is not attached to an attributable system root.")
            elif self.summary is not None and self.summary != message.summary:
                self.unknown("CONFLICTING_FINAL_ARTIFACTS", "Final text artifacts disagree.")
            else:
                self.summary = message.summary
        self._append_text(message, root)

    def _interaction(self, message, kind, payload):
        if message.role == "user" and kind == "interactive":
            return
        if kind == "interactive":
            interactive_type = payload.get("type") if isinstance(payload, dict) else None
            if not _string(interactive_type):
                raise ValueError("interaction type is missing")
            if interactive_type not in HIL_FIELDS:
                if interactive_type != "sls_query" or not _query_display(payload):
                    self.unknown("UNCONFIRMED_INTERACTIVE_CONTENT",
                                 "Interactive display content requires a verified output mapping.")
                return
            _hil_source(payload)
        if not _string(message.call_id) or not isinstance(message.parent_id, str):
            raise ValueError("interaction envelope identity is incomplete")
        call_id = message.call_id
        if kind == "interactive_response":
            # A manual reply's envelope uses the owning Agent TaskID;
            # its payload carries the HIL ID. Automatic replies may use
            # the HIL ID in both places. Never infer either missing ID.
            if (message.role != "assistant" or not isinstance(payload, dict) or
                    not _string(payload.get("callId")) or "source" not in payload):
                raise ValueError("interaction response identity is incomplete")
            call_id = payload["callId"]
        item = {"callId": call_id, "parentCallId": message.parent_id,
                "payload": copy.deepcopy(payload)}
        key = interaction_key(item)
        item["source"] = copy.deepcopy(_source(payload))
        if kind == "interactive":
            self._keep_pending(key, item)
        else:
            self._confirmation_decision(payload, self.pending.get(key))
            if self.ambiguous_ids:
                return  # A conflicting request/trace frame cannot confirm a reply.
            if not self._response_agrees(key, payload):
                self.response_conflict = True
                self.unknown("CONFLICTING_INTERACTION_RESPONSE",
                             "The service interaction response conflicts with the submitted result.")
                return
            self.pending.pop(key, None)
            self.pending_bytes -= self.pending_sizes.pop(key, 0)

    def _append_text(self, message, root):
        if not root or message.role != "assistant" or message.has_calls:
            return
        for value, append, last in message.text:
            if value == "" and append and last:
                self.closed_text = True
                continue
            if self.closed_text or not append:
                self._text.seek(0)
                self._text.truncate(0)
                self.result_bytes = len(value.encode("utf-8"))
            else:
                self.result_bytes += len(value.encode("utf-8"))
                if self.result_bytes > MAX_RESULT_BYTES:
                    raise ValueError("answer exceeds resource budget")
            self._text.write(value)
            self.closed_text = last
            if self.result_bytes > MAX_RESULT_BYTES:
                raise ValueError("answer exceeds resource budget")

    def finish(self):
        problem = self.problem
        if self.artifact_reads and problem is None:
            problem = error("outcome_unknown", "UNCONFIRMED_ARTIFACT_READ",
                            "An artifact Read has no matching successful result.", "read_stream")
        if self.root_id is None and len(self.control_roots) > 1 and problem is None:
            problem = error("outcome_unknown", "AMBIGUOUS_ROOT", "Multiple system roots have no unique Agent association.", "execution")
        if self.summary is not None and self.summary != self.answer and problem is None:
            problem = error("outcome_unknown", "FINAL_TEXT_MISMATCH", "Final artifact and the last Agent text window disagree.", "execution")
        if len(self.terminals) > 1:
            problem = error("outcome_unknown", "CONFLICTING_ROOT_TERMINALS",
                            "Root terminal evidence conflicts; the remote outcome requires verification.", "execution")
        if self.reconnect and not self.request_error and problem is None and (
                not self.replay_origin or not self.stream_done or
                (self.root_id is None and (self.expected_root or not self.pending))):
            problem = error("outcome_unknown", "UNVERIFIED_REPLAY_COMPLETENESS",
                            "Replay lacks the complete original user origin, attributable outcome, or stream closure.", "read_stream")
        result = {key: value for key, value in self.identifiers.items() if _string(value)}
        if self.pending:
            result["interactions"] = list(self.pending.values())
        if self.artifacts:
            result["artifacts"] = self.artifacts
        if problem:
            result.update(status="unknown", error=problem)
        elif self.service_error:
            result.update(status="failed", error=self.service_error)
        elif self.pending and self.stream_done and result.get("threadId"):
            result["status"] = "interactive"
        elif self.terminals == {True} and not self.pending and result.get("threadId"):
            result["status"] = "completed"
            if self.answer:
                result["answer"] = self.answer
        else:
            result.update(status="unknown", error=error("outcome_unknown", "MISSING_BUSINESS_OUTCOME",
                          "The stream did not establish a complete business result.", "read_stream"))
        return result
