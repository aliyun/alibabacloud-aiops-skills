# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest
from unittest.mock import patch

from sysom_cli.memory.lib.oom_quick import (
    analyze_oom_local,
    normalize_oomcheck_time_param,
    parse_oom_at_anchor,
)


def _two_block_journal_tail() -> list[str]:
    return [
        "Mar 10 10:00:00 host kernel: invoked oom-killer: gfp_mask=0x0",
        "Mar 10 10:00:00 host kernel: Killed process 111 (oldproc) total-vm:1000kB",
        "Mar 11 11:00:00 host kernel: invoked oom-killer: gfp_mask=0x0",
        "Mar 11 11:00:00 host kernel: Task in /sys.slice cgroup parent",
        "Mar 11 11:00:00 host kernel: Killed process 222 (newproc) total-vm:2000kB",
    ]


def _three_block_journal_tail() -> list[str]:
    b = _two_block_journal_tail()
    b.extend(
        [
            "Mar 12 12:00:00 host kernel: invoked oom-killer: gfp_mask=0x0",
            "Mar 12 12:00:00 host kernel: Killed process 333 (third) total-vm:3000kB",
        ]
    )
    return b


def _same_hour_duplicate_comm_blocks() -> list[str]:
    """同日同小时、同 comm、无 cgroup，折叠为一条摘要。"""
    return [
        "Mar 12 12:00:00 host kernel: invoked oom-killer: gfp_mask=0x0",
        "Mar 12 12:00:01 host kernel: Killed process 1 (sameapp) total-vm:1000kB",
        "Mar 12 12:30:00 host kernel: invoked oom-killer: gfp_mask=0x0",
        "Mar 12 12:30:02 host kernel: Killed process 2 (sameapp) total-vm:2000kB",
    ]


class NormalizeOomcheckTimeTests(unittest.TestCase):
    def test_iso_converts_to_unix_digits_only(self) -> None:
        out = normalize_oomcheck_time_param("2026-03-25T15:21:32")
        self.assertTrue(out.isdigit(), msg=out)
        self.assertNotIn(":", out)

    def test_space_datetime_converts(self) -> None:
        out = normalize_oomcheck_time_param("2026-03-25 15:21:32")
        self.assertTrue(out.isdigit(), msg=out)

    def test_range_segments_normalized(self) -> None:
        out = normalize_oomcheck_time_param(
            "2026-03-25T15:21:00~2026-03-25T15:22:00"
        )
        self.assertIn("~", out)
        a, b = out.split("~", 1)
        self.assertTrue(a.isdigit() and b.isdigit(), msg=out)

    def test_unix_passthrough(self) -> None:
        self.assertEqual(normalize_oomcheck_time_param("1700000000"), "1700000000")


class ParseOomAtTests(unittest.TestCase):
    def test_unix_seconds(self) -> None:
        dt = parse_oom_at_anchor("1700000000")
        self.assertIsNotNone(dt)
        assert dt is not None
        self.assertEqual(dt.year, 2023)

    def test_iso(self) -> None:
        dt = parse_oom_at_anchor("2024-06-15T14:30:00")
        self.assertIsNotNone(dt)
        assert dt is not None
        self.assertEqual((dt.year, dt.month, dt.day), (2024, 6, 15))


class AnalyzeOomLocalTests(unittest.TestCase):
    @patch("sysom_cli.memory.lib.oom_quick.get_kernel_log_lines")
    def test_default_one_full_log_is_last_event(self, mock_gl: object) -> None:
        mock_gl.return_value = _two_block_journal_tail()
        r = analyze_oom_local(max_lines=5000, max_full_oom_logs=1)
        self.assertEqual(r["hit_count"], 2)
        self.assertEqual(r["extraction_mode"], "sysak_blocks")
        self.assertEqual(len(r["oom_digest"]), 1)
        # digest is a dict with killed_comm
        self.assertEqual(r["oom_digest"][0]["killed_comm"], "newproc")
        self.assertEqual(len(r["oom_events_summary"]), 2)

    @patch("sysom_cli.memory.lib.oom_quick.get_kernel_log_lines")
    def test_oom_at_selects_nearest_wallclock_block(self, mock_gl: object) -> None:
        mock_gl.return_value = _two_block_journal_tail()
        r = analyze_oom_local(
            max_lines=5000,
            max_full_oom_logs=1,
            oom_at="Mar 10 10:00:05",
        )
        self.assertEqual(len(r["oom_digest"]), 1)
        self.assertEqual(r["oom_digest"][0]["killed_comm"], "oldproc")

    @patch("sysom_cli.memory.lib.oom_quick.get_kernel_log_lines")
    def test_max_full_logs_extends_backward(self, mock_gl: object) -> None:
        mock_gl.return_value = _three_block_journal_tail()
        r = analyze_oom_local(max_lines=5000, max_full_oom_logs=2)
        self.assertEqual(len(r["oom_digest"]), 2)
        comms = [d["killed_comm"] for d in r["oom_digest"]]
        self.assertIn("third", comms)
        self.assertIn("newproc", comms)

    @patch("sysom_cli.memory.lib.oom_quick.get_kernel_log_lines")
    def test_summaries_capped(self, mock_gl: object) -> None:
        mock_gl.return_value = _three_block_journal_tail()
        r = analyze_oom_local(max_lines=5000, max_event_summaries=2)
        self.assertEqual(len(r["oom_events_summary"]), 2)
        idxs = [s["event_index"] for s in r["oom_events_summary"]]
        self.assertEqual(idxs, [1, 2])

    @patch("sysom_cli.memory.lib.oom_quick.get_kernel_log_lines")
    def test_memcg_scope_hint(self, mock_gl: object) -> None:
        mock_gl.return_value = _two_block_journal_tail()
        r = analyze_oom_local(max_lines=5000)
        summ = r["oom_events_summary"]
        self.assertEqual(summ[-1].get("scope_hint"), "memcg")
        self.assertEqual(summ[-1].get("killed_comm"), "newproc")

    @patch("sysom_cli.memory.lib.oom_quick.get_kernel_log_lines")
    def test_same_hour_same_comm_collapses_with_count(self, mock_gl: object) -> None:
        mock_gl.return_value = _same_hour_duplicate_comm_blocks()
        r = analyze_oom_local(max_lines=5000, max_event_summaries=64)
        self.assertEqual(r["hit_count"], 2)
        self.assertEqual(len(r["oom_events_summary"]), 1)
        row = r["oom_events_summary"][0]
        self.assertEqual(row.get("similar_oom_count"), 2)
        self.assertEqual(row.get("killed_comm"), "sameapp")
        self.assertEqual(row.get("event_index"), 1)


if __name__ == "__main__":
    unittest.main()
