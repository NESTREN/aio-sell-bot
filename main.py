import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from db import Database
from crypto_pay import CryptoPayAPI
from middlewares import DbMiddleware, ConfigMiddleware, CryptoMiddleware
from handlers import common, user, admin


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    db = Database(config.db_path)
    await db.connect()
    await db.init()

    crypto = CryptoPayAPI(
        token=config.crypto_token,
        base_url=config.crypto_api_url,
        asset=config.crypto_asset,
    )
    await crypto.start()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(DbMiddleware(db))
    dp.callback_query.middleware(DbMiddleware(db))
    dp.message.middleware(ConfigMiddleware(config))
    dp.callback_query.middleware(ConfigMiddleware(config))
    dp.message.middleware(CryptoMiddleware(crypto))
    dp.callback_query.middleware(CryptoMiddleware(crypto))

    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await crypto.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
