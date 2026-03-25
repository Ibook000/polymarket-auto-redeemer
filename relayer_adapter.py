import inspect
from typing import List, Tuple

from web3 import Web3

from config import CTF_CONTRACT, USDC_E_CONTRACT


class RelayerAdapter:
    def __init__(self, private_key: str, builder_api_key: str, builder_secret: str, builder_passphrase: str, relayer_url: str, relayer_tx_type: str):
        self.private_key = private_key
        self.builder_api_key = builder_api_key
        self.builder_secret = builder_secret
        self.builder_passphrase = builder_passphrase
        self.relayer_url = relayer_url
        self.relayer_tx_type = relayer_tx_type
        self.relayer_client = None

    def create_client(self):
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

        args = [self.relayer_url, 137, self.private_key, cfg]
        init_params = inspect.signature(RelayClient.__init__).parameters

        if len(init_params) >= 6:
            tx_enum = getattr(rel_mod, "RelayerTxType", None) or getattr(rel_mod, "TransactionType", None)
            tx_value = None
            if tx_enum is not None:
                if self.relayer_tx_type == "PROXY" and hasattr(tx_enum, "PROXY"):
                    tx_value = getattr(tx_enum, "PROXY")
                elif hasattr(tx_enum, "SAFE"):
                    tx_value = getattr(tx_enum, "SAFE")
                elif hasattr(tx_enum, "SAFE_CREATE"):
                    tx_value = getattr(tx_enum, "SAFE_CREATE")
            if tx_value is not None:
                args.append(tx_value)

        self.relayer_client = RelayClient(*args)
        return self.relayer_client

    def redeem_conditions(self, condition_ids: List[str]) -> Tuple[bool, str, str]:
        from py_builder_relayer_client.models import SafeTransaction, OperationType

        ctf_addr = Web3.to_checksum_address(CTF_CONTRACT)
        usdc_addr = Web3.to_checksum_address(USDC_E_CONTRACT)
        contract = Web3().eth.contract(
            address=ctf_addr,
            abi=[
                {
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
                }
            ],
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
