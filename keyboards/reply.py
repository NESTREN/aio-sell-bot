from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🛍️ Каталог"), KeyboardButton(text="👤 Личный кабинет")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🛠️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="➕ Добавить товар")],
        [KeyboardButton(text="📦 Товары"), KeyboardButton(text="🧾 Заказы")],
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="💰 Начислить баланс")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✖️ Отмена")]], resize_keyboard=True
    )
