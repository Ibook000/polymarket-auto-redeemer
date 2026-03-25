import os
import sys
import time
import json
import threading
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_API = "https://data-api.polymarket.com"
CTF_CONTRACT = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
USDC_E_CONTRACT = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
CONFIG_JSON_PATH = os.path.join(BASE_DIR, "config_redeem.json")

try:
    from web3 import Web3
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    print("ERROR: Please install web3: pip install web3")

try:
    import py_builder_relayer_client
    import py_builder_signing_sdk
    HAS_BUILDER = True
except ImportError:
    HAS_BUILDER = False
    print("ERROR: Please install Builder SDK: pip install py-builder-relayer-client py-builder-signing-sdk")


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
        self.relayer_client = None
        self.relayer_error = ""
        self.last_pending_count = 0
        self.last_claimable_count = 0
        self.last_result = {}
        self.last_error = ""

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

        client, err = self._create_relayer_client()
        if client is None:
            log(f"[{self.name}] Auto redeem disabled: relayer init failed {err}", "ERR")
            self.enabled = False
            return
        self.relayer_client = client
        log(f"[{self.name}] AccountRedeemer initialized", "OK")

    def _normalize_condition_id(self, value):
        s = str(value or "").strip().lower()
        if not s:
            return ""
        if s.startswith("0x"):
            s = s[2:]
        if len(s) != 64:
            return ""
        try:
            int(s, 16)
        except Exception:
            return ""
        return "0x" + s

    def _fetch_positions(self, user):
        try:
            proxies = self.global_config.get("proxies", {})
            r = requests.get(
                f"{DATA_API}/positions",
                params={"user": user, "sizeThreshold": 0},
                proxies=proxies if proxies else None,
                timeout=12,
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data
        except Exception as e:
            log(f"[{self.name}] Failed to fetch positions: {e}", "ERR")
        return []

    def _create_relayer_client(self):
        try:
            import inspect
            import py_builder_relayer_client.client as rel_mod
            from py_builder_relayer_client.client import RelayClient

            try:
                from py_builder_signing_sdk import BuilderConfig, BuilderApiKeyCreds
            except Exception:
                from py_builder_signing_sdk.config import BuilderConfig, BuilderApiKeyCreds

            cfg = BuilderConfig(
                local_builder_creds=BuilderApiKeyCreds(
                    key=self.builder_api_key,
                    secret=self.builder_secret,
                    passphrase=self.builder_passphrase,
                )
            )

            relayer_url = self.global_config.get("relayer_url", "https://relayer-v2.polymarket.com")
            relayer_tx_type = self.global_config.get("relayer_tx_type", "SAFE")

            args = [relayer_url, 137, self.private_key, cfg]
            init_params = inspect.signature(RelayClient.__init__).parameters

            if len(init_params) >= 6:
                tx_enum = getattr(rel_mod, "RelayerTxType", None) or getattr(rel_mod, "TransactionType", None)
                tx_value = None
                if tx_enum is not None:
                    if relayer_tx_type == "PROXY" and hasattr(tx_enum, "PROXY"):
                        tx_value = getattr(tx_enum, "PROXY")
                    elif hasattr(tx_enum, "SAFE"):
                        tx_value = getattr(tx_enum, "SAFE")
                    elif hasattr(tx_enum, "SAFE_CREATE"):
                        tx_value = getattr(tx_enum, "SAFE_CREATE")
                if tx_value is not None:
                    args.append(tx_value)

            return RelayClient(*args), ""
        except Exception as e:
            return None, str(e)

    def _collect_redeemable(self):
        pending = []
        seen = set()
        claimable = []

        for owner in self.scan_addresses:
            rows = self._fetch_positions(owner)
            owner_l = owner.lower()

            for row in rows:
                if not isinstance(row, dict):
                    continue

                size = row.get("size")
                try:
                    size_f = float(size or 0)
                except Exception:
                    size_f = 0.0

                if size_f <= 0:
                    continue

                redeemable = bool(row.get("redeemable") or row.get("mergeable"))
                if not redeemable:
                    continue

                cid = self._normalize_condition_id(
                    row.get("conditionId") or row.get("condition_id")
                )
                if not cid:
                    continue

                key = owner_l + "|" + cid
                if key in seen:
                    continue
                seen.add(key)

                pending.append({"owner": owner, "condition_id": cid})

                if owner_l == self.funder_address.lower() and cid not in claimable:
                    claimable.append(cid)

        return pending, claimable

    def _redeem_conditions(self, condition_ids):
        try:
            from py_builder_relayer_client.models import SafeTransaction, OperationType

            ctf_addr = Web3.to_checksum_address(CTF_CONTRACT)
            usdc_addr = Web3.to_checksum_address(USDC_E_CONTRACT)
            contract = Web3().eth.contract(
                address=ctf_addr,
                abi=[{
                    "name": "redeemPositions",
                    "type": "function",
                    "stateMutability": "nonpayable",
                    "inputs": [
                        {"name": "collateralToken", "type": "address"},
                        {"name": "parentCollectionId", "type": "bytes32"},
                        {"name": "conditionId", "type": "bytes32"},
                        {"name": "indexSets", "type": "uint256[]"},
                    ],
                    "outputs": [],
                }],
            )

            txs = []
            for condition_id in condition_ids:
                cond_bytes = bytes.fromhex(condition_id[2:])
                data = contract.encode_abi(
                    abi_element_identifier="redeemPositions",
                    args=[usdc_addr, b"\x00" * 32, cond_bytes, [1, 2]],
                )

                op_call = getattr(OperationType, "Call", None)
                if op_call is None:
                    op_call = list(OperationType)[0]

                tx = SafeTransaction(to=str(ctf_addr), operation=op_call, data=str(data), value="0")
                txs.append(tx)

            def execute_once():
                resp = self.relayer_client.execute(txs, f"Redeem {len(txs)} conditions")
                result = resp.wait()
                txh = str(getattr(resp, "transaction_hash", "") or "")

                state = ""
                if isinstance(result, dict):
                    txh = str(result.get("transaction_hash") or result.get("transactionHash") or txh)
                    state = str(result.get("state") or "")
                else:
                    txh = str(getattr(result, "transaction_hash", "") or getattr(result, "transactionHash", "") or txh)
                    state = str(getattr(result, "state", "") or "")

                if result is None:
                    return False, txh, "relayer_not_confirmed"
                if state and state not in ["STATE_CONFIRMED", "STATE_MINED", "STATE_EXECUTED"]:
                    return False, txh, f"state={state}"
                return True, txh, ""

            try:
                return execute_once()
            except Exception as e:
                msg = str(e)
                low = msg.lower()
                if "expected safe" in low and "not deployed" in low:
                    dep = self.relayer_client.deploy()
                    dep.wait()
                    return execute_once()
                return False, "", msg

        except Exception as e:
            return False, "", str(e)

    def scan_once(self):
        if not self.enabled:
            return

        pending, claimable = self._collect_redeemable()
        now = time.time()

        self.last_pending_count = len(pending)
        self.last_claimable_count = len(claimable)

        if pending:
            signature = "|".join([f"{x['owner']}:{x['condition_id']}" for x in pending])
            if signature != self.last_pending_signature or (now - self.last_pending_log_ts) >= self.global_config.get("pending_log_interval", 30):
                self.last_pending_signature = signature
                self.last_pending_log_ts = now

                owners = sorted(list({x["owner"] for x in pending}))
                owner_text = ", ".join(owners[:3])
                if len(owners) > 3:
                    owner_text += f" and {len(owners)} addresses"

                log(f"[{self.name}] | redeemable: {len(pending)} | auto-redeemable: {len(claimable)} | address: {owner_text}", "WARN")

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
            ok, tx_hash, err = self._redeem_conditions(batch)

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
            sys.exit(1)

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            log(f"Failed to load config: {e}", "ERR")
            sys.exit(1)

        global_cfg = config.get("global", {})
        self.global_config = {
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
        if self.global_config.get("http_proxy"):
            proxies["http"] = self.global_config["http_proxy"]
        if self.global_config.get("https_proxy"):
            proxies["https"] = self.global_config["https_proxy"]
        self.global_config["proxies"] = proxies

        self.enabled = self.global_config.get("enabled", False)

        accounts = config.get("accounts", [])
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


def create_default_config_json():
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
            "https_proxy": ""
        },
        "accounts": [
            {
                "name": "account-1",
                "private_key": "0x",
                "funder_address": "0x",
                "builder_api_key": "",
                "builder_secret": "",
                "builder_passphrase": "",
                "enabled": True
            }
        ]
    }

    try:
        with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        log(f"Created default config: {CONFIG_JSON_PATH}", "OK")
        return True
    except Exception as e:
        log(f"Failed to create default config: {e}", "ERR")
        return False


def main():
    print("Polymarket Auto Redeemer")

    if not HAS_WEB3:
        log("Missing web3 dependency, exiting", "ERR")
        sys.exit(1)

    if not HAS_BUILDER:
        log("Missing Builder SDK dependency, exiting", "ERR")
        sys.exit(1)

    if not os.path.exists(CONFIG_JSON_PATH):
        log(f"Config not found: {CONFIG_JSON_PATH}", "WARN")
        log("Creating default config...", "INFO")
        create_default_config_json()
        log("Please edit the config file and rerun the program", "WARN")
        sys.exit(0)

    redeemer = AutoRedeemer()

    if not redeemer.enabled:
        log("Auto redeem not enabled, exiting", "WARN")
        sys.exit(0)

    if not redeemer.account_redeemers:
        log("No valid accounts, exiting", "WARN")
        sys.exit(0)

    redeemer.start()

    log("Press Ctrl+C to stop", "INFO")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        log("Stop signal received...", "WARN")
        redeemer.stop()
        log("Program exited", "OK")


if __name__ == "__main__":
    main()
