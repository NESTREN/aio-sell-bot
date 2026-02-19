from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.callbacks import (
    ProductCb,
    CatalogPageCb,
    CatalogItemCb,
    PayCb,
    CheckCb,
    TopupCb,
    AdminProductCb,
    AdminUserPageCb,
    AdminUserActionCb,
)
from utils.formatters import cents_to_amount


def product_buy_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Купить",
                    callback_data=ProductCb(action="buy", product_id=product_id).pack(),
                )
            ]
        ]
    )


def product_view_kb(product_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Купить",
                    callback_data=ProductCb(action="buy", product_id=product_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data=CatalogPageCb(page=page).pack(),
                )
            ],
        ]
    )


def pay_methods_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 CryptoBot",
                    callback_data=PayCb(method="crypto", product_id=product_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 С баланса",
                    callback_data=PayCb(method="balance", product_id=product_id).pack(),
                )
            ],
        ]
    )


def invoice_kb(pay_url: str, kind: str, invoice_id: str, internal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
            [
                InlineKeyboardButton(
                    text="✅ Проверить оплату",
                    callback_data=CheckCb(
                        kind=kind, invoice_id=str(invoice_id), internal_id=internal_id
                    ).pack(),
                )
            ],
        ]
    )


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="topup_menu")],
            [InlineKeyboardButton(text="🧾 Мои покупки", callback_data="my_orders")],
        ]
    )


def topup_amounts_kb(amounts: list[int]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for amount in amounts:
        row.append(
            InlineKeyboardButton(
                text=f"💎 {amount} USDT",
                callback_data=TopupCb(amount=amount).pack(),
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="✍️ Ввести сумму", callback_data="topup_custom")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_product_kb(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    title = "🚫 Отключить" if is_active else "✅ Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=title,
                    callback_data=AdminProductCb(action="toggle", product_id=product_id).pack(),
                )
            ]
        ]
    )


def admin_users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Список пользователей", callback_data=AdminUserPageCb(page=0).pack()
                )
            ],
            [InlineKeyboardButton(text="🔎 Поиск", callback_data="admin_users_search")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users_back")],
        ]
    )


def admin_users_list_kb(
    users: list[dict], page: int, has_more: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users:
        username = user["username"] or ""
        label = (
            f"{user['id']} - @{username}"
            if username
            else f"{user['id']} - {user['full_name'] or 'без имени'}"
        )
        label = label[:40]
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=AdminUserActionCb(
                        action="view", user_id=int(user["id"]), page=page
                    ).pack(),
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Предыдущая", callback_data=AdminUserPageCb(page=page - 1).pack()
            )
        )
    if has_more:
        nav_row.append(
            InlineKeyboardButton(
                text="➡️ Следующая", callback_data=AdminUserPageCb(page=page + 1).pack()
            )
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_card_kb(user_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Пополнить баланс",
                    callback_data=AdminUserActionCb(
                        action="balance_add", user_id=user_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ Списать с баланса",
                    callback_data=AdminUserActionCb(
                        action="balance_sub", user_id=user_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Установить баланс",
                    callback_data=AdminUserActionCb(
                        action="balance_set", user_id=user_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Заказы",
                    callback_data=AdminUserActionCb(
                        action="orders", user_id=user_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data=AdminUserPageCb(page=page).pack(),
                )
            ],
        ]
    )


def admin_user_search_results_kb(users: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users:
        username = user["username"] or ""
        label = (
            f"{user['id']} - @{username}"
            if username
            else f"{user['id']} - {user['full_name'] or 'без имени'}"
        )
        label = label[:40]
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=AdminUserActionCb(
                        action="view", user_id=int(user["id"]), page=0
                    ).pack(),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_orders_kb(user_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к пользователю",
                    callback_data=AdminUserActionCb(
                        action="view", user_id=user_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data=AdminUserPageCb(page=page).pack(),
                )
            ],
        ]
    )


def catalog_list_kb(
    products: list[dict], page: int, has_more: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for product in products:
        title = product["title"]
        price = cents_to_amount(int(product["price_cents"]))
        label = f"🛍️ {title} - {price} USDT"
        label = label[:50]
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=CatalogItemCb(
                        product_id=int(product["id"]), page=page
                    ).pack(),
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Предыдущая", callback_data=CatalogPageCb(page=page - 1).pack()
            )
        )
    if has_more:
        nav_row.append(
            InlineKeyboardButton(
                text="➡️ Следующая", callback_data=CatalogPageCb(page=page + 1).pack()
            )
        )
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)
