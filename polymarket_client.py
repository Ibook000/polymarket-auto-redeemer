from typing import Dict, List, Tuple

import requests

from config import DATA_API


class PolymarketClient:
    def __init__(self, proxies=None, timeout=12):
        self.proxies = proxies or {}
        self.timeout = timeout

    @staticmethod
    def normalize_condition_id(value: str) -> str:
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

    def fetch_positions(self, user: str) -> List[Dict]:
        r = requests.get(
            f"{DATA_API}/positions",
            params={"user": user, "sizeThreshold": 0},
            proxies=self.proxies if self.proxies else None,
            timeout=self.timeout,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return data if isinstance(data, list) else []

    def collect_redeemable(self, scan_addresses: List[str], funder_address: str) -> Tuple[List[Dict], List[str]]:
        pending = []
        seen = set()
        claimable = []

        for owner in scan_addresses:
            rows = self.fetch_positions(owner)
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

                cid = self.normalize_condition_id(row.get("conditionId") or row.get("condition_id"))
                if not cid:
                    continue

                key = owner_l + "|" + cid
                if key in seen:
                    continue
                seen.add(key)

                pending.append({"owner": owner, "condition_id": cid})

                if owner_l == funder_address.lower() and cid not in claimable:
                    claimable.append(cid)

        return pending, claimable
