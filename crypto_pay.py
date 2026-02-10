import aiohttp
from typing import Any, Optional


class CryptoPayError(RuntimeError):
    pass


class CryptoPayAPI:
    def __init__(self, token: str, base_url: str, asset: str = "USDT"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.asset = asset
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.session:
            raise RuntimeError("CryptoPayAPI session is not started")
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Crypto-Pay-API-Token": self.token}
        async with self.session.request(method, url, headers=headers, **kwargs) as resp:
            data = await resp.json()
        if not data.get("ok"):
            raise CryptoPayError(data)
        return data

    async def create_invoice(self, amount: str, description: str, payload: str) -> dict[str, Any]:
        payload_data = {
            "asset": self.asset,
            "amount": amount,
            "description": description,
            "payload": payload,
            "allow_comments": False,
            "allow_anonymous": False,
        }
        data = await self._request("POST", "createInvoice", json=payload_data)
        return data["result"]

    async def get_invoice(self, invoice_id: str) -> Optional[dict[str, Any]]:
        params = {"invoice_ids": str(invoice_id)}
        data = await self._request("GET", "getInvoices", params=params)
        items = data.get("result", {}).get("items", [])
        if not items:
            return None
        return items[0]
