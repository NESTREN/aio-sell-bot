import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    bot_token: str
    crypto_token: str
    crypto_api_url: str
    crypto_asset: str
    admin_ids: set[int]
    db_path: str

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def _parse_admin_ids(value: str) -> set[int]:
    if not value:
        return set()
    parts = [p.strip() for p in value.split(",") if p.strip()]
    ids: set[int] = set()
    for part in parts:
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    crypto_token = os.getenv("CRYPTO_BOT_TOKEN", "").strip()
    crypto_api_url = os.getenv("CRYPTO_BOT_API_URL", "https://pay.crypt.bot/api").strip()
    crypto_asset = os.getenv("CRYPTO_ASSET", "USDT").strip()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    db_path = os.getenv("DB_PATH", "bot.db").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    if not crypto_token:
        raise RuntimeError("CRYPTO_BOT_TOKEN is required")

    return Config(
        bot_token=bot_token,
        crypto_token=crypto_token,
        crypto_api_url=crypto_api_url,
        crypto_asset=crypto_asset,
        admin_ids=admin_ids,
        db_path=db_path,
    )
