from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from config import Config
from db import Database
from keyboards.reply import main_menu
from utils import texts

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, config: Config) -> None:
    user = message.from_user
    if not user:
        return
    await db.add_or_update_user(user.id, user.username or "", user.full_name)
    await message.answer(
        texts.welcome_text(user.full_name), reply_markup=main_menu(config.is_admin(user.id))
    )


@router.message(Command("help"))
@router.message(F.text.in_(["ℹ️ Помощь", "Помощь"]))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.help_text())


@router.message(F.text.in_(["⬅️ Назад", "Назад"]))
async def back_to_main(message: Message, config: Config) -> None:
    user = message.from_user
    if not user:
        return
    await message.answer("🏠 Главное меню", reply_markup=main_menu(config.is_admin(user.id)))
