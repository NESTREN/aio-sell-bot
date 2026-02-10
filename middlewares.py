from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Dict, Any


class DbMiddleware(BaseMiddleware):
    def __init__(self, db):
        self.db = db

    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]):
        data["db"] = self.db
        return await handler(event, data)


class ConfigMiddleware(BaseMiddleware):
    def __init__(self, config):
        self.config = config

    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]):
        data["config"] = self.config
        return await handler(event, data)


class CryptoMiddleware(BaseMiddleware):
    def __init__(self, crypto_api):
        self.crypto_api = crypto_api

    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]):
        data["crypto"] = self.crypto_api
        return await handler(event, data)
