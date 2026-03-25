import json
import os
from typing import Any, Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_API = "https://data-api.polymarket.com"
CTF_CONTRACT = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
USDC_E_CONTRACT = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
CONFIG_JSON_PATH = os.path.join(BASE_DIR, "config_redeem.json")


def load_config(config_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    global_cfg = config.get("global", {})
    global_config = {
        "enabled": global_cfg.get("enabled", True),
        "scan_interval": max(3, int(global_cfg.get("scan_interval", 15))),
        "retry_interval": max(10, int(global_cfg.get("retry_interval", 120))),
        "max_per_scan": max(1, int(global_cfg.get("max_per_scan", 10))),
        "pending_log_interval": max(10, int(global_cfg.get("pending_log_interval", 30))),
        "relayer_url": global_cfg.get("relayer_url", "https://relayer-v2.polymarket.com"),
        "relayer_tx_type": global_cfg.get("relayer_tx_type", "SAFE"),
        "http_proxy": global_cfg.get("http_proxy", ""),
        "https_proxy": global_cfg.get("https_proxy", ""),
    }

    proxies = {}
    if global_config.get("http_proxy"):
        proxies["http"] = global_config["http_proxy"]
    if global_config.get("https_proxy"):
        proxies["https"] = global_config["https_proxy"]
    global_config["proxies"] = proxies

    accounts = config.get("accounts", [])
    if not isinstance(accounts, list):
        accounts = []

    return global_config, accounts


def create_default_config_json(config_path: str = CONFIG_JSON_PATH) -> None:
    default_config = {
        "global": {
            "enabled": True,
            "scan_interval": 15,
            "retry_interval": 120,
            "max_per_scan": 10,
            "pending_log_interval": 10,
            "relayer_url": "https://relayer-v2.polymarket.com",
            "relayer_tx_type": "SAFE",
            "http_proxy": "",
            "https_proxy": "",
        },
        "accounts": [
            {
                "name": "account-1",
                "private_key": "0x",
                "funder_address": "0x",
                "builder_api_key": "",
                "builder_secret": "",
                "builder_passphrase": "",
                "enabled": True,
            }
        ],
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(default_config, f, ensure_ascii=False, indent=4)
