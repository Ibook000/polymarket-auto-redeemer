import os
import threading
import time
from datetime import datetime

from config import CONFIG_JSON_PATH, create_default_config_json, load_config
from polymarket_client import PolymarketClient
from relayer_adapter import RelayerAdapter

try:
    from web3 import Web3  # noqa: F401

    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

try:
    import py_builder_relayer_client  # noqa: F401
    import py_builder_signing_sdk  # noqa: F401

    HAS_BUILDER = True
except ImportError:
    HAS_BUILDER = False


def log(msg, level="INFO"):
    if level in ["INFO", "OK", "ERR", "WARN", "TRADE"]:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "[INFO]",
            "OK": "[OK]",
            "ERR": "[ERR]",
            "WARN": "[WARN]",
            "TRADE": "[TRADE]",
        }.get(level, "[INFO]")
        print(f"{ts} {prefix} {msg}")

        if level in ["TRADE", "ERR", "OK"]:
            try:
                with open("redeem.log", "a", encoding="utf-8") as f:
                    f.write(f"{ts} {prefix} {msg}\n")
            except Exception:
                pass


class AccountRedeemer:
    def __init__(self, account_config, global_config):
        self.name = account_config.get("name", "Unnamed")
        self.private_key = (account_config.get("private_key") or "").strip()
        if self.private_key and not self.private_key.startswith("0x"):
            self.private_key = "0x" + self.private_key
        self.funder_address = (account_config.get("funder_address") or "").strip()
        self.enabled = account_config.get("enabled", True)
        self.builder_api_key = account_config.get("builder_api_key", "")
        self.builder_secret = account_config.get("builder_secret", "")
        self.builder_passphrase = account_config.get("builder_passphrase", "")

        self.global_config = global_config
        self.scan_addresses = []
        self.last_try_by_condition = {}
        self.last_pending_signature = ""
        self.last_pending_log_ts = 0.0
        self.running = False
        self.thread = None
        self.last_pending_count = 0
        self.last_claimable_count = 0
        self.last_result = {}
        self.last_error = ""

        self.pm_client = PolymarketClient(proxies=self.global_config.get("proxies", {}))
        self.relayer = None

        if not self.enabled:
            log(f"[{self.name}] Auto redeem disabled", "WARN")
            return

        if not HAS_WEB3:
            log(f"[{self.name}] Auto redeem disabled: missing web3 dependency", "ERR")
            self.enabled = False
            return

        if not self.private_key:
            log(f"[{self.name}] Auto redeem disabled: missing private_key", "ERR")
            self.enabled = False
            return

        if not self.funder_address:
            log(f"[{self.name}] Auto redeem disabled: missing funder_address", "ERR")
            self.enabled = False
            return

        if not (self.builder_api_key and self.builder_secret and self.builder_passphrase):
            log(f"[{self.name}] Auto redeem disabled: missing Builder API credentials", "ERR")
            self.enabled = False
            return

        self.scan_addresses = [self.funder_address]

        try:
            self.relayer = RelayerAdapter(
                private_key=self.private_key,
                builder_api_key=self.builder_api_key,
                builder_secret=self.builder_secret,
                builder_passphrase=self.builder_passphrase,
                relayer_url=self.global_config.get("relayer_url", "https://relayer-v2.polymarket.com"),
                relayer_tx_type=self.global_config.get("relayer_tx_type", "SAFE"),
            )
            self.relayer.create_client()
        except Exception as e:
            log(f"[{self.name}] Auto redeem disabled: relayer init failed {e}", "ERR")
            self.enabled = False
            return

        log(f"[{self.name}] AccountRedeemer initialized", "OK")

    def scan_once(self):
        if not self.enabled:
            return

        try:
            pending, claimable = self.pm_client.collect_redeemable(self.scan_addresses, self.funder_address)
        except Exception as e:
            log(f"[{self.name}] Failed to fetch positions: {e}", "ERR")
            return

        now = time.time()

        self.last_pending_count = len(pending)
        self.last_claimable_count = len(claimable)

        if pending:
            signature = "|".join([f"{x['owner']}:{x['condition_id']}" for x in pending])
            if signature != self.last_pending_signature or (
                now - self.last_pending_log_ts
            ) >= self.global_config.get("pending_log_interval", 30):
                self.last_pending_signature = signature
                self.last_pending_log_ts = now

                owners = sorted(list({x["owner"] for x in pending}))
                owner_text = ", ".join(owners[:3])
                if len(owners) > 3:
                    owner_text += f" and {len(owners)} addresses"

                log(
                    f"[{self.name}] | redeemable: {len(pending)} | auto-redeemable: {len(claimable)} | address: {owner_text}",
                    "WARN",
                )

        if not claimable:
            log(f"[{self.name}] No claimable positions", "INFO")
            return

        max_per_scan = self.global_config.get("max_per_scan", 10)
        log(f"[{self.name}] Start redeeming {len(claimable)} positions (max {max_per_scan} per scan)", "INFO")

        batch_size = min(max_per_scan, len(claimable))
        batch = []

        for cid in claimable:
            retry_interval = self.global_config.get("retry_interval", 120)
            t0 = self.last_try_by_condition.get(cid, 0)
            if now - t0 < retry_interval:
                continue
            self.last_try_by_condition[cid] = now
            batch.append(cid)

            if len(batch) >= batch_size:
                break

        if batch:
            ok, tx_hash, err = self.relayer.redeem_conditions(batch)

            if ok:
                log(f"[{self.name}] Successfully redeemed {len(batch)} positions | {tx_hash}", "OK")
                self.last_error = ""
                self.last_result = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ok": True,
                    "condition_ids": batch,
                    "tx": tx_hash,
                    "message": "ok",
                }
            else:
                log(f"[{self.name}] Failed to redeem {len(batch)} positions | {err}", "ERR")
                self.last_error = str(err)
                self.last_result = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ok": False,
                    "condition_ids": batch,
                    "tx": tx_hash,
                    "message": str(err),
                }

    def _loop(self):
        scan_interval = self.global_config.get("scan_interval", 15)
        while self.running:
            try:
                self.scan_once()
            except Exception as e:
                log(f"[{self.name}] Auto redeem loop exception: {e}", "ERR")

            for _ in range(scan_interval):
                if not self.running:
                    break
                time.sleep(1)

    def start(self):
        if not self.enabled or self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        scan_interval = self.global_config.get("scan_interval", 15)
        max_per_scan = self.global_config.get("max_per_scan", 10)
        log(f"[{self.name}] Auto redeem started | scan interval: {scan_interval}s | max per scan: {max_per_scan}", "OK")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        log(f"[{self.name}] Auto redeem stopped", "INFO")


class AutoRedeemer:
    def __init__(self, config_path=None):
        self.config_path = config_path or CONFIG_JSON_PATH
        self.enabled = False
        self.account_redeemers = []
        self.global_config = {}
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            log(f"JSON config not found: {self.config_path}", "ERR")
            return

        try:
            self.global_config, accounts = load_config(self.config_path)
        except Exception as e:
            log(f"Failed to load config: {e}", "ERR")
            return

        self.enabled = self.global_config.get("enabled", False)

        if not accounts:
            log("No account config found", "WARN")
            return

        valid_accounts = []
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            if not acc.get("enabled", True):
                continue
            if not acc.get("private_key"):
                log(f"Account [{acc.get('name', 'Unnamed')}] missing private_key, skipped", "WARN")
                continue
            if not acc.get("funder_address"):
                log(f"Account [{acc.get('name', 'Unnamed')}] missing funder_address, skipped", "WARN")
                continue
            if not (acc.get("builder_api_key") and acc.get("builder_secret") and acc.get("builder_passphrase")):
                log(f"Account [{acc.get('name', 'Unnamed')}] missing Builder credentials, skipped", "WARN")
                continue
            valid_accounts.append(acc)

        if not valid_accounts:
            log("No valid account config found", "ERR")
            return

        for acc in valid_accounts:
            redeemer = AccountRedeemer(acc, self.global_config)
            if redeemer.enabled:
                self.account_redeemers.append(redeemer)

        if self.account_redeemers:
            log(f"Initialized auto redeemers for {len(self.account_redeemers)} account(s)", "OK")
        else:
            log("No account was successfully initialized", "ERR")

    def scan_once(self):
        for redeemer in self.account_redeemers:
            redeemer.scan_once()

    def start(self):
        if not self.enabled:
            return
        for redeemer in self.account_redeemers:
            redeemer.start()

    def stop(self):
        for redeemer in self.account_redeemers:
            redeemer.stop()


def bootstrap_config_if_missing(config_path=CONFIG_JSON_PATH):
    if os.path.exists(config_path):
        return False
    create_default_config_json(config_path)
    return True
