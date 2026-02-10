from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from ..config import Config
from ..db import Database
from ..keyboards.reply import admin_menu, cancel_menu
from ..keyboards.inline import (
    admin_product_kb,
    admin_users_menu_kb,
    admin_users_list_kb,
    admin_user_card_kb,
    admin_user_search_results_kb,
    admin_user_orders_kb,
)
from ..utils.formatters import parse_amount_to_cents, format_product, cents_to_amount
from ..utils.callbacks import AdminProductCb, AdminUserPageCb, AdminUserActionCb
from ..utils import texts

router = Router()


class AddProduct(StatesGroup):
    title = State()
    description = State()
    price = State()
    content = State()


class AdminTopup(StatesGroup):
    user_id = State()
    amount = State()


class AdminUserSearch(StatesGroup):
    query = State()


class AdminUserBalance(StatesGroup):
    amount = State()


def _is_admin(message: Message, config: Config) -> bool:
    user = message.from_user
    return bool(user and config.is_admin(user.id))


async def _edit_or_send(message: Message, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup)


@router.message(F.text.in_(["✖️ Отмена", "Отмена"]))
async def admin_cancel(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("⛔ Доступ запрещен")
        return
    await state.clear()
    await message.answer("✅ Действие отменено.", reply_markup=admin_menu())


@router.message(F.text.in_(["🛠️ Админ панель", "Админ панель"]))
async def admin_panel(message: Message, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("Доступ запрещен")
        return
    await message.answer(texts.admin_menu_text(), reply_markup=admin_menu())


@router.message(F.text.in_(["➕ Добавить товар", "Добавить товар"]))
async def add_product_start(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("Доступ запрещен")
        return
    await state.set_state(AddProduct.title)
    await message.answer("Введите название товара:", reply_markup=cancel_menu())


@router.message(AddProduct.title)
async def add_product_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AddProduct.description)
    await message.answer("Введите описание товара:", reply_markup=cancel_menu())


@router.message(AddProduct.description)
async def add_product_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProduct.price)
    await message.answer("Введите цену (например 9.99):", reply_markup=cancel_menu())


@router.message(AddProduct.price)
async def add_product_price(message: Message, state: FSMContext) -> None:
    try:
        price_cents = parse_amount_to_cents(message.text)
    except ValueError:
        await message.answer("Не понял цену. Пример: 9.99")
        return
    await state.update_data(price_cents=price_cents)
    await state.set_state(AddProduct.content)
    await message.answer("Введите контент товара (что получит покупатель):", reply_markup=cancel_menu())


@router.message(AddProduct.content)
async def add_product_content(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    title = data.get("title", "")
    description = data.get("description", "")
    price_cents = int(data.get("price_cents", 0))
    content = message.text.strip()

    await db.create_product(title, description, price_cents, content)
    await state.clear()
    await message.answer(
        f"Товар добавлен. Цена: {cents_to_amount(price_cents)} USDT",
        reply_markup=admin_menu(),
    )


@router.message(F.text.in_(["📦 Товары", "Товары"]))
async def admin_products(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("Доступ запрещен")
        return
    products = await db.list_all_products()
    if not products:
        await message.answer("Товаров пока нет.")
        return
    await message.answer("<b>Товары</b>")
    for product in products:
        status = "активен" if product["is_active"] else "выключен"
        text = format_product(product) + f"\nСтатус: <b>{status}</b>"
        await message.answer(text, reply_markup=admin_product_kb(product["id"], bool(product["is_active"])))


@router.callback_query(AdminProductCb.filter())
async def admin_product_toggle(
    callback: CallbackQuery, callback_data: AdminProductCb, db: Database, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    product = await db.get_product(callback_data.product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    new_active = not bool(product["is_active"])
    await db.toggle_product(product["id"], new_active)
    status = "активен" if new_active else "выключен"
    text = format_product(product) + f"\nСтатус: <b>{status}</b>"
    await callback.message.edit_text(
        text, reply_markup=admin_product_kb(product["id"], new_active)
    )
    await callback.answer("Готово")


@router.message(F.text.in_(["🧾 Заказы", "Заказы"]))
async def admin_orders(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("Доступ запрещен")
        return
    orders = await db.list_recent_orders(limit=20)
    if not orders:
        await message.answer("Заказов пока нет.")
        return
    lines = ["<b>Последние заказы</b>"]
    for order in orders:
        status = "оплачено" if order["status"] == "paid" else "ожидает"
        amount = cents_to_amount(int(order["amount_cents"]))
        lines.append(
            f"#{order['id']} - {order['title']} - {amount} USDT - {status} (user {order['user_id']})"
        )
    await message.answer("\n".join(lines))


@router.message(F.text.in_(["💰 Начислить баланс", "Начислить баланс"]))
async def admin_topup_start(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("Доступ запрещен")
        return
    await state.set_state(AdminTopup.user_id)
    await message.answer("Введите ID пользователя:", reply_markup=cancel_menu())


@router.message(AdminTopup.user_id)
async def admin_topup_user(message: Message, state: FSMContext) -> None:
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(AdminTopup.amount)
    await message.answer("Введите сумму (например 5 или 12.5):", reply_markup=cancel_menu())


@router.message(AdminTopup.amount)
async def admin_topup_amount(message: Message, state: FSMContext, db: Database) -> None:
    try:
        amount_cents = parse_amount_to_cents(message.text)
    except ValueError:
        await message.answer("Не понял сумму. Пример: 10 или 10.50")
        return
    data = await state.get_data()
    user_id = int(data.get("user_id"))
    await db.add_or_update_user(user_id, "", "")
    await db.update_balance(user_id, amount_cents)
    await state.clear()
    await message.answer(
        f"Баланс пользователя {user_id} пополнен на {cents_to_amount(amount_cents)} USDT.",
        reply_markup=admin_menu(),
    )


@router.message(F.text.in_(["👥 Пользователи", "Пользователи"]))
async def admin_users_menu(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message, config):
        await message.answer("Доступ запрещен")
        return
    total = await db.count_users()
    await message.answer(texts.admin_users_menu_text(total), reply_markup=admin_users_menu_kb())


@router.callback_query(F.data == "admin_users_back")
async def admin_users_back(callback: CallbackQuery, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await callback.message.answer(texts.admin_menu_text(), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_users_search")
async def admin_users_search(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await state.set_state(AdminUserSearch.query)
    await callback.message.answer("Введите ID или @username:", reply_markup=cancel_menu())
    await callback.answer()


@router.message(AdminUserSearch.query)
async def admin_users_search_query(message: Message, state: FSMContext, db: Database) -> None:
    query = (message.text or "").strip()
    await state.clear()

    if not query:
        await message.answer("Пустой запрос.", reply_markup=admin_menu())
        return

    if query.startswith("@"):
        query = query[1:]

    if query.isdigit():
        user = await db.get_user(int(query))
        await message.answer("Готово.", reply_markup=admin_menu())
        if not user:
            await message.answer("Пользователь не найден.")
            return
        order_count = await db.count_orders(user["id"])
        await message.answer(
            texts.admin_user_card_text(user, order_count),
            reply_markup=admin_user_card_kb(int(user["id"]), 0),
        )
        return

    users = await db.search_users(query, limit=10)
    await message.answer("Готово.", reply_markup=admin_menu())
    if not users:
        await message.answer("Пользователи не найдены.")
        return

    await message.answer(
        f"Найдено: {len(users)}",
        reply_markup=admin_user_search_results_kb(users),
    )


@router.callback_query(AdminUserPageCb.filter())
async def admin_users_list(
    callback: CallbackQuery, callback_data: AdminUserPageCb, db: Database, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    page = max(0, int(callback_data.page))
    limit = 8
    offset = page * limit
    users = await db.list_users(limit=limit + 1, offset=offset)
    has_more = len(users) > limit
    users = users[:limit]
    total = await db.count_users()

    if not users:
        await _edit_or_send(callback.message, "Пользователей пока нет.")
        await callback.answer()
        return

    text = (
        "<b>Пользователи</b>\n"
        f"Всего: <b>{total}</b>\n"
        f"Страница: <b>{page + 1}</b>\n"
        "Выберите пользователя:"
    )
    await _edit_or_send(
        callback.message, text, reply_markup=admin_users_list_kb(users, page, has_more)
    )
    await callback.answer()


@router.callback_query(AdminUserActionCb.filter(F.action == "view"))
async def admin_user_view(
    callback: CallbackQuery, callback_data: AdminUserActionCb, db: Database, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    user = await db.get_user(callback_data.user_id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    order_count = await db.count_orders(user["id"])
    await _edit_or_send(
        callback.message,
        texts.admin_user_card_text(user, order_count),
        reply_markup=admin_user_card_kb(int(user["id"]), int(callback_data.page)),
    )
    await callback.answer()


@router.callback_query(
    AdminUserActionCb.filter(
        F.action.in_(["balance_add", "balance_sub", "balance_set"])
    )
)
async def admin_user_balance_start(
    callback: CallbackQuery, callback_data: AdminUserActionCb, state: FSMContext, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await state.set_state(AdminUserBalance.amount)
    await state.update_data(
        user_id=callback_data.user_id, mode=callback_data.action, page=callback_data.page
    )
    if callback_data.action == "balance_add":
        prompt = "Введите сумму пополнения:"
    elif callback_data.action == "balance_sub":
        prompt = "Введите сумму списания:"
    else:
        prompt = "Введите сумму баланса, которую нужно установить:"
    await callback.message.answer(prompt, reply_markup=cancel_menu())
    await callback.answer()


@router.message(AdminUserBalance.amount)
async def admin_user_balance_apply(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    await state.clear()

    try:
        amount_cents = parse_amount_to_cents(message.text or "")
    except ValueError:
        await message.answer("Не понял сумму. Пример: 10 или 10.50", reply_markup=admin_menu())
        return

    user_id = int(data.get("user_id", 0))
    mode = data.get("mode", "")
    page = int(data.get("page", 0))

    user = await db.get_user(user_id)
    if not user:
        await db.add_or_update_user(user_id, "", "")
        user = await db.get_user(user_id)
        if not user:
            await message.answer("Пользователь не найден.", reply_markup=admin_menu())
            return

    if mode == "balance_add":
        await db.update_balance(user_id, amount_cents)
        result_text = f"Баланс пополнен на {cents_to_amount(amount_cents)} USDT."
    elif mode == "balance_sub":
        await db.update_balance(user_id, -amount_cents)
        result_text = f"С баланса списано {cents_to_amount(amount_cents)} USDT."
    elif mode == "balance_set":
        await db.set_balance(user_id, amount_cents)
        result_text = f"Баланс установлен: {cents_to_amount(amount_cents)} USDT."
    else:
        await message.answer("Неизвестная операция.", reply_markup=admin_menu())
        return

    await message.answer(result_text, reply_markup=admin_menu())
    user = await db.get_user(user_id)
    order_count = await db.count_orders(user_id)
    await message.answer(
        texts.admin_user_card_text(user, order_count),
        reply_markup=admin_user_card_kb(user_id, page),
    )


@router.callback_query(AdminUserActionCb.filter(F.action == "orders"))
async def admin_user_orders(
    callback: CallbackQuery, callback_data: AdminUserActionCb, db: Database, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    orders = await db.list_user_orders(callback_data.user_id, limit=10)
    if not orders:
        await _edit_or_send(
            callback.message,
            "У пользователя пока нет покупок.",
            reply_markup=admin_user_orders_kb(callback_data.user_id, callback_data.page),
        )
        await callback.answer()
        return

    lines = ["<b>Покупки пользователя</b>"]
    for order in orders:
        status = "оплачено" if order["status"] == "paid" else "ожидает"
        amount = cents_to_amount(int(order["amount_cents"]))
        lines.append(f"#{order['id']} - {order['title']} - {amount} USDT - {status}")

    await _edit_or_send(
        callback.message,
        "\n".join(lines),
        reply_markup=admin_user_orders_kb(callback_data.user_id, callback_data.page),
    )
    await callback.answer()


