# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from sysom_cli.configure.command import ConfigureCommand


class ConfigureNonInteractiveTests(unittest.TestCase):
    def test_eof_returns_non_interactive_envelope_with_settings_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            fake_cfg = home / ".aliyun" / "config.json"
            fake_cfg.parent.mkdir(parents=True, exist_ok=True)
            fake_cfg.write_text("{}", encoding="utf-8")

            def fake_input(_: str = "") -> str:
                raise EOFError()

            with patch.dict("os.environ", {"HOME": str(home)}):
                with patch("builtins.input", fake_input):
                    cmd = ConfigureCommand()
                    out = cmd.execute_local(Namespace())

            self.assertFalse(out["ok"])
            self.assertEqual(out["action"], "configure")
            self.assertEqual(out["error"]["code"], "non_interactive_shell")
            self.assertIn("/settings", out["agent"]["summary"])
            self.assertIn("PTY", out["agent"]["summary"])
            rem = "\n".join(out["data"]["remediation"])
            self.assertIn("/settings", rem)
            self.assertIn("/bash", rem)
            self.assertIn("authentication.md", rem)
            self.assertIn("/settings", out["data"]["guidance"]["credential_policy"])


if __name__ == "__main__":
    unittest.main()
