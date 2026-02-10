from .formatters import cents_to_amount, escape


def welcome_text(full_name: str) -> str:
    name = escape(full_name)
    return (
        f"👋 Привет, <b>{name}</b>!\n"
        "Добро пожаловать в магазин.\n"
        "Здесь можно купить товары за крипту или с баланса.\n"
        "Выберите раздел ниже."
    )


def profile_text(user, order_count: int) -> str:
    balance = cents_to_amount(int(user["balance_cents"]))
    return (
        "👤 <b>Личный кабинет</b>\n"
        f"🆔 ID: <code>{user['id']}</code>\n"
        f"💰 Баланс: <b>{balance} USDT</b>\n"
        f"🧾 Покупок: <b>{order_count}</b>"
    )


def topup_created_text(amount_cents: int) -> str:
    amount = cents_to_amount(amount_cents)
    return (
        "💳 Счет на пополнение создан.\n"
        f"💎 Сумма: <b>{amount} USDT</b>\n"
        "Нажмите «Оплатить», затем «Проверить оплату»."
    )


def order_created_text(title: str, amount_cents: int) -> str:
    amount = cents_to_amount(amount_cents)
    title_safe = escape(title)
    return (
        f"🧾 Счет за товар «<b>{title_safe}</b>» создан.\n"
        f"💎 Сумма: <b>{amount} USDT</b>\n"
        "Нажмите «Оплатить», затем «Проверить оплату»."
    )


def order_paid_text(title: str, content: str) -> str:
    return (
        f"✅ Оплата получена. Товар «<b>{escape(title)}</b>» активирован.\n\n"
        f"📦 <b>Ваш товар:</b>\n{escape(content)}"
    )


def balance_payment_text(title: str, content: str, balance_left_cents: int) -> str:
    balance_left = cents_to_amount(balance_left_cents)
    return (
        f"✅ Покупка «<b>{escape(title)}</b>» оплачена с баланса.\n\n"
        f"📦 <b>Ваш товар:</b>\n{escape(content)}\n\n"
        f"💰 Остаток баланса: <b>{balance_left} USDT</b>"
    )


def not_enough_balance_text(price_cents: int, balance_cents: int) -> str:
    price = cents_to_amount(price_cents)
    balance = cents_to_amount(balance_cents)
    return (
        "⚠️ Недостаточно средств на балансе.\n"
        f"💎 Цена: <b>{price} USDT</b>\n"
        f"💰 Баланс: <b>{balance} USDT</b>"
    )


def admin_menu_text() -> str:
    return "🛠️ <b>Админ-панель</b>\nВыберите действие."


def admin_users_menu_text(total: int) -> str:
    return (
        "👥 <b>Пользователи</b>\n"
        f"Всего пользователей: <b>{total}</b>\n"
        "Выберите действие."
    )


def admin_user_card_text(user, order_count: int) -> str:
    username = user["username"] or "-"
    full_name = user["full_name"] or "-"
    balance = cents_to_amount(int(user["balance_cents"]))
    created_at = user["created_at"]
    return (
        "👤 <b>Карточка пользователя</b>\n"
        f"🆔 ID: <code>{user['id']}</code>\n"
        f"🔗 Username: <b>{escape(username)}</b>\n"
        f"👤 Имя: <b>{escape(full_name)}</b>\n"
        f"💰 Баланс: <b>{balance} USDT</b>\n"
        f"🧾 Покупок: <b>{order_count}</b>\n"
        f"🗓️ Создан: <code>{created_at}</code>"
    )


def help_text() -> str:
    return (
        "ℹ️ <b>Помощь</b>\n"
        "🛍️ Покупайте товары в разделе «Каталог».\n"
        "💳 Пополняйте баланс в «Личном кабинете».\n"
        "✉️ По вопросам напишите администратору."
    )
