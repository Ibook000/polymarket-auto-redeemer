import json
import os
import tempfile
import unittest

from config import load_config
from polymarket_client import PolymarketClient


class ConfigAndClientTests(unittest.TestCase):
    def test_load_config_with_proxy_mapping(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            json.dump(
                {
                    "global": {
                        "enabled": True,
                        "scan_interval": 15,
                        "retry_interval": 120,
                        "max_per_scan": 10,
                        "pending_log_interval": 10,
                        "relayer_url": "https://relayer-v2.polymarket.com",
                        "relayer_tx_type": "SAFE",
                        "http_proxy": "http://127.0.0.1:7890",
                        "https_proxy": "http://127.0.0.1:7890",
                    },
                    "accounts": [{"name": "a"}],
                },
                f,
            )
            path = f.name

        try:
            global_config, accounts = load_config(path)
            self.assertTrue(global_config["enabled"])
            self.assertEqual(global_config["proxies"]["http"], "http://127.0.0.1:7890")
            self.assertEqual(global_config["proxies"]["https"], "http://127.0.0.1:7890")
            self.assertEqual(len(accounts), 1)
        finally:
            os.remove(path)

    def test_normalize_condition_id(self):
        raw = "ab" * 32
        cid = PolymarketClient.normalize_condition_id(raw)
        self.assertEqual(cid, "0x" + raw)
        self.assertEqual(PolymarketClient.normalize_condition_id("0x" + raw), "0x" + raw)
        self.assertEqual(PolymarketClient.normalize_condition_id(""), "")
        self.assertEqual(PolymarketClient.normalize_condition_id("xyz"), "")


if __name__ == "__main__":
    unittest.main()
