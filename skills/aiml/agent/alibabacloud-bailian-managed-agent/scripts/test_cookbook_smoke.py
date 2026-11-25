"""Local checks for live-test assertions; no credentials or network required."""
import unittest
from copy import deepcopy
from unittest.mock import patch

import cookbook_smoke as smoke


def status(state, reason=None, event_id="status"):
    data = {"session_status": state}
    if reason:
        data["stop_reason"] = {"type": reason}
    return {"id": event_id, "type": "session_status", "content": [{"type": "data", "data": data}]}


class SmokeAssertionsTest(unittest.TestCase):
    def delta_fixture(self):
        frames, history = [], []
        for eid, kind, chunks in (("reason", "reasoning", [(0, "a"), (1, "b"), (0, "a")]),
                                  ("answer", "message", [(0, "3"), (0, "23")])):
            frames.append({"object": "message", "status": "in_progress", "id": eid,
                           "type": kind, "role": "assistant"})
            blocks = {}
            for index, text in chunks:
                frames.append({"object": "content", "status": "in_progress", "type": "text",
                               "msg_id": eid, "index": index, "delta": True, "text": text})
                blocks[index] = blocks.get(index, "") + text
            for index, text in sorted(blocks.items()):
                frames.append({"object": "content", "status": "completed", "type": "text",
                               "msg_id": eid, "index": index, "delta": False, "text": text})
            final = {"object": "message", "status": "completed", "id": eid, "type": kind,
                     "role": "assistant", "content": [{"type": "text", "text": text}
                                                         for _, text in sorted(blocks.items())]}
            frames.append(final)
            history.append(deepcopy(final))
        return frames, history

    def test_content_deltas_separate_thinking_and_answer_without_appending_snapshots(self):
        frames, history = self.delta_fixture()
        evidence = smoke.delta_evidence(frames, history)
        smoke.assert_delta_evidence(evidence)
        self.assertEqual(evidence["reasoning"]["nonempty_delta_count"], 3)
        self.assertEqual(evidence["reasoning"]["text_chars"], 3)
        self.assertEqual(evidence["message"]["nonempty_delta_count"], 2)
        self.assertEqual(evidence["message"]["text_chars"], 3)

    def test_archived_event_delta_envelope_still_verifies(self):
        frames, history = self.delta_fixture()
        legacy = [smoke.normalize_delta_frame(f) for f in frames
                  if not (f.get("object") == "content" and f.get("delta") is False)]
        smoke.assert_delta_evidence(smoke.delta_evidence(legacy, history))

    def test_reasoning_start_and_final_alone_do_not_prove_text_delivery(self):
        frames, history = self.delta_fixture()
        frames = [f for f in frames if f.get("msg_id") != "reason"]
        for event in frames + history:
            if event.get("id") == "reason":
                event.pop("content", None)
        evidence = smoke.delta_evidence(frames, history)
        with self.assertRaises(AssertionError):
            smoke.assert_delta_evidence(evidence)

    def test_empty_reasoning_still_requires_a_history_event(self):
        frames, history = self.delta_fixture()
        for event in frames:
            if event.get("id") == "reason":
                event.pop("content", None)
        history = [e for e in history if e["id"] != "reason"]
        with self.assertRaises(AssertionError):
            smoke.assert_delta_evidence(smoke.delta_evidence(frames, history))

    def test_full_snapshot_cannot_hide_a_lost_delta(self):
        frames, history = self.delta_fixture()
        frames = [f for f in frames if not (f.get("delta") is True and f.get("text") == "23")]
        with self.assertRaises(AssertionError):
            smoke.assert_delta_evidence(smoke.delta_evidence(frames, history))

    def test_history_content_must_match_stream(self):
        frames, history = self.delta_fixture()
        history[0]["content"][0]["text"] = "different"
        with self.assertRaises(AssertionError):
            smoke.assert_delta_evidence(smoke.delta_evidence(frames, history))

    def test_sse_comments_optional_space_and_multiline_data(self):
        class Response:
            def iter_lines(self):
                return iter([': connected', '', 'data:{"type":"event_start"}', '',
                             ':keepalive', 'data: {"type":', 'data: "message"}', '',
                             'data: [DONE]', ''])
        result = list(smoke.iter_sse_events(Response(), float('inf')))
        self.assertEqual(result, [{'type': 'event_start'}, {'type': 'message'}])

    def test_old_completion_cannot_finish_new_running_turn(self):
        events = [status("idle", "end_turn", "old"), status("running", event_id="new")]
        self.assertIsNone(smoke.terminal_state(events))

    def test_only_normal_completion_passes(self):
        smoke.assert_end_turn([status("idle", "end_turn")])
        for events in ([], [status("running")], [status("idle", "requires_action")],
                       [status("idle", "retries_exhausted")], [status("terminated")]):
            with self.subTest(events=events), self.assertRaises(AssertionError):
                smoke.assert_end_turn(events)

    def test_assistant_claim_does_not_replace_tool_evidence(self):
        claim = {"type": "message", "role": "assistant", "content": [{"type": "text", "text": "MOUNT_REMOVED"}]}
        with self.assertRaises(AssertionError):
            smoke.assert_tool_success([claim], "MOUNT_REMOVED")
        failed = {"type": "tool_call_output", "is_error": True, "content": [{"type": "text", "text": "MOUNT_REMOVED"}]}
        with self.assertRaises(AssertionError):
            smoke.assert_tool_success([failed], "MOUNT_REMOVED")

    def test_paginated_resource_list_preserves_scope(self):
        pages = [{"data": [{"id": "file_1"}], "next_page": "cursor_2"},
                 {"data": [{"id": "file_2"}]}]
        with patch.object(smoke, "req", side_effect=pages) as request:
            result = smoke.list_items("/files", scope_type="session", scope_id="sesn_test")
        self.assertEqual([x["id"] for x in result], ["file_1", "file_2"])
        for call in request.call_args_list:
            query = smoke.httpx.URL("https://example.invalid" + call.args[1]).params
            self.assertEqual(query["scope_type"], "session")
            self.assertEqual(query["scope_id"], "sesn_test")
        self.assertEqual(query["page"], "cursor_2")


if __name__ == "__main__":
    unittest.main()
