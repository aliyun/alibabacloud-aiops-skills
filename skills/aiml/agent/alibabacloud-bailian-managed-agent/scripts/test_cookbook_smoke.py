"""Local checks for live-test assertions; no credentials or network required."""
import unittest
from unittest.mock import patch

import cookbook_smoke as smoke


def status(state, reason=None, event_id="status"):
    data = {"session_status": state}
    if reason:
        data["stop_reason"] = {"type": reason}
    return {"id": event_id, "type": "session_status", "content": [{"type": "data", "data": data}]}


class SmokeAssertionsTest(unittest.TestCase):
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
