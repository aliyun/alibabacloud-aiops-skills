# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sysom_cli.lib.auth import check_aliyun_config, check_env_credentials


class AuthStsTokenTests(unittest.TestCase):
    def test_env_credentials_support_sts_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "ALIBABA_CLOUD_ACCESS_KEY_ID": "STS.ID",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "secret",
                "ALIBABA_CLOUD_SECURITY_TOKEN": "token-abc",
            },
            clear=True,
        ):
            out = check_env_credentials()

        self.assertTrue(out["available"])
        self.assertEqual(out["method"], "环境变量(STS Token)")
        self.assertEqual(out["credentials"]["ak_id"], "STS.ID")
        self.assertEqual(out["credentials"]["ak_secret"], "secret")
        self.assertEqual(out["credentials"]["security_token"], "token-abc")

    def test_config_support_sts_token_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg_path = home / ".aliyun" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(
                json.dumps(
                    {
                        "current": "default",
                        "profiles": [
                            {
                                "name": "default",
                                "mode": "StsToken",
                                "access_key_id": "STS.ID",
                                "access_key_secret": "secret",
                                "sts_token": "token-xyz",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"HOME": str(home)}):
                out = check_aliyun_config()

        self.assertTrue(out["available"])
        self.assertEqual(out["method"], "配置文件(StsToken)")
        self.assertEqual(out["credentials"]["ak_id"], "STS.ID")
        self.assertEqual(out["credentials"]["ak_secret"], "secret")
        self.assertEqual(out["credentials"]["security_token"], "token-xyz")


if __name__ == "__main__":
    unittest.main()
