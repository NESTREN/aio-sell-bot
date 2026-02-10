from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from ..db import Database
from ..crypto_pay import CryptoPayAPI, CryptoPayError
from ..keyboards.reply import cancel_menu
from ..keyboards.inline import (
    product_buy_kb,
    product_view_kb,
    catalog_list_kb,
    pay_methods_kb,
    invoice_kb,
    profile_kb,
    topup_amounts_kb,
)
from ..utils.callbacks import (
    ProductCb,
    CatalogPageCb,
    CatalogItemCb,
    PayCb,
    CheckCb,
    TopupCb,
)
from ..utils.formatters import format_product, cents_to_amount, parse_amount_to_cents
from ..utils import texts

router = Router()

TOPUP_AMOUNTS = [5, 10, 20, 50, 100]
MIN_TOPUP_CENTS = 5
CATALOG_PAGE_SIZE = 8


class TopupInput(StatesGroup):
    amount = State()


async def _safe_edit(message: Message, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        raise


async def _render_my_orders(
    message: Message, user_id: int, db: Database, edit: bool = False
) -> None:
    orders = await db.list_user_orders(user_id, limit=10)
    if not orders:
        text = "🧾 Покупок пока нет."
        if edit:
            await _safe_edit(message, text, reply_markup=profile_kb())
        else:
            await message.answer(text, reply_markup=profile_kb())
        return

    lines = ["🧾 <b>Мои покупки</b>"]
    for order in orders:
        status = "✅ оплачено" if order["status"] == "paid" else "⏳ ожидает"
        amount = cents_to_amount(int(order["amount_cents"]))
        lines.append(f"#{order['id']} - {order['title']} - {amount} USDT - {status}")

    text = "\n".join(lines)
    if edit:
        await _safe_edit(message, text, reply_markup=profile_kb())
    else:
        await message.answer(text, reply_markup=profile_kb())


async def _show_catalog_page(
    message: Message, db: Database, page: int, edit: bool = False
) -> None:
    page = max(0, page)
    limit = CATALOG_PAGE_SIZE
    offset = page * limit
    products = await db.list_active_products_paged(limit=limit + 1, offset=offset)
    has_more = len(products) > limit
    products = products[:limit]
    total = await db.count_active_products()

    if not products:
        text = "🛍️ Пока нет активных товаров."
        if edit:
            await _safe_edit(message, text)
        else:
            await message.answer(text)
        return

    text = (
        "🛍️ <b>Каталог</b>\n"
        f"Всего: <b>{total}</b>\n"
        f"Страница: <b>{page + 1}</b>\n"
        "Выберите товар:"
    )

    if edit:
        await _safe_edit(message, text, reply_markup=catalog_list_kb(products, page, has_more))
    else:
        await message.answer(text, reply_markup=catalog_list_kb(products, page, has_more))


@router.message(F.text.in_(["🛍️ Каталог", "Каталог"]))
async def show_catalog(message: Message, db: Database) -> None:
    await _show_catalog_page(message, db, page=0, edit=False)


@router.callback_query(CatalogPageCb.filter())
async def catalog_page(callback: CallbackQuery, callback_data: CatalogPageCb, db: Database) -> None:
    await _show_catalog_page(callback.message, db, page=callback_data.page, edit=True)
    await callback.answer()


@router.callback_query(CatalogItemCb.filter())
async def catalog_item_view(
    callback: CallbackQuery, callback_data: CatalogItemCb, db: Database
) -> None:
    product = await db.get_product(callback_data.product_id)
    if not product or not product["is_active"]:
        await callback.answer("⚠️ Товар недоступен", show_alert=True)
        return

    text = format_product(product) + "\n\n📦 Выберите действие:"
    try:
        await _safe_edit(
            callback.message, text, reply_markup=product_view_kb(product["id"], callback_data.page)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text, reply_markup=product_view_kb(product["id"], callback_data.page)
        )
    await callback.answer()


@router.callback_query(ProductCb.filter(F.action == "buy"))
async def product_buy(callback: CallbackQuery, callback_data: ProductCb, db: Database) -> None:
    product = await db.get_product(callback_data.product_id)
    if not product or not product["is_active"]:
        await callback.answer("⚠️ Товар недоступен", show_alert=True)
        return

    text = format_product(product) + "\n\n💳 Выберите способ оплаты:"
    try:
        await _safe_edit(callback.message, text, reply_markup=pay_methods_kb(product["id"]))
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=pay_methods_kb(product["id"]))
    await callback.answer()


@router.callback_query(PayCb.filter(F.method == "crypto"))
async def pay_crypto(
    callback: CallbackQuery,
    callback_data: PayCb,
    db: Database,
    crypto: CryptoPayAPI,
) -> None:
    product = await db.get_product(callback_data.product_id)
    if not product or not product["is_active"]:
        await callback.answer("⚠️ Товар недоступен", show_alert=True)
        return

    amount_str = cents_to_amount(int(product["price_cents"]))
    description = f"Оплата товара #{product['id']}"
    payload = f"u{callback.from_user.id}-p{product['id']}"

    try:
        invoice = await crypto.create_invoice(amount_str, description, payload)
    except CryptoPayError:
        await callback.answer("Не удалось создать счет", show_alert=True)
        return

    invoice_id = str(invoice["invoice_id"])
    pay_url = invoice["pay_url"]
    order_id = await db.create_order(
        user_id=callback.from_user.id,
        product_id=product["id"],
        amount_cents=int(product["price_cents"]),
        payment_method="crypto",
        crypto_invoice_id=invoice_id,
        crypto_pay_url=pay_url,
    )

    text = texts.order_created_text(product["title"], int(product["price_cents"]))
    try:
        await callback.message.edit_text(
            text, reply_markup=invoice_kb(pay_url, "order", invoice_id, order_id)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text, reply_markup=invoice_kb(pay_url, "order", invoice_id, order_id)
        )
    await callback.answer()


@router.callback_query(PayCb.filter(F.method == "balance"))
async def pay_balance(callback: CallbackQuery, callback_data: PayCb, db: Database) -> None:
    product = await db.get_product(callback_data.product_id)
    if not product or not product["is_active"]:
        await callback.answer("⚠️ Товар недоступен", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    price_cents = int(product["price_cents"])
    balance_cents = int(user["balance_cents"])

    if balance_cents < price_cents:
        await callback.message.answer(texts.not_enough_balance_text(price_cents, balance_cents))
        await callback.answer()
        return

    await db.update_balance(callback.from_user.id, -price_cents)
    order_id = await db.create_order(
        user_id=callback.from_user.id,
        product_id=product["id"],
        amount_cents=price_cents,
        payment_method="balance",
    )
    await db.set_order_paid(order_id)

    new_balance = balance_cents - price_cents
    text = texts.balance_payment_text(product["title"], product["content"], new_balance)
    await callback.message.answer(text)
    await callback.answer("✅ Оплачено")


@router.message(F.text.in_(["👤 Личный кабинет", "Личный кабинет"]))
async def profile(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return
    await db.add_or_update_user(user.id, user.username or "", user.full_name)
    user_row = await db.get_user(user.id)
    order_count = await db.count_orders(user.id)
    await message.answer(texts.profile_text(user_row, order_count), reply_markup=profile_kb())


@router.callback_query(F.data == "topup_menu")
async def topup_menu(callback: CallbackQuery) -> None:
    await _safe_edit(
        callback.message,
        "💳 Выберите сумму пополнения:",
        reply_markup=topup_amounts_kb(TOPUP_AMOUNTS),
    )
    await callback.answer()


async def _create_topup_invoice(
    user_id: int, amount_cents: int, db: Database, crypto: CryptoPayAPI
) -> tuple[str, object]:
    amount_str = cents_to_amount(amount_cents)
    description = "Пополнение баланса"
    payload = f"topup:u{user_id}"

    invoice = await crypto.create_invoice(amount_str, description, payload)
    invoice_id = str(invoice["invoice_id"])
    pay_url = invoice["pay_url"]
    topup_id = await db.create_topup(
        user_id=user_id,
        amount_cents=amount_cents,
        crypto_invoice_id=invoice_id,
        crypto_pay_url=pay_url,
    )

    text = texts.topup_created_text(amount_cents)
    return text, invoice_kb(pay_url, "topup", invoice_id, topup_id)


@router.callback_query(TopupCb.filter())
async def topup_create(
    callback: CallbackQuery, callback_data: TopupCb, db: Database, crypto: CryptoPayAPI
) -> None:
    amount_cents = int(callback_data.amount) * 100
    if amount_cents < MIN_TOPUP_CENTS:
        await callback.answer("⚠️ Минимум 0.05 USDT", show_alert=True)
        return

    try:
        text, kb = await _create_topup_invoice(callback.from_user.id, amount_cents, db, crypto)
    except CryptoPayError:
        await callback.answer("❌ Не удалось создать счет", show_alert=True)
        return

    await _safe_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "topup_custom")
async def topup_custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TopupInput.amount)
    await callback.message.answer(
        "Введите сумму пополнения (минимум 0.05 USDT):", reply_markup=cancel_menu()
    )
    await callback.answer()


@router.message(TopupInput.amount, F.text.in_(["✖️ Отмена", "Отмена"]))
async def topup_custom_cancel(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    user = message.from_user
    if not user:
        return
    await db.add_or_update_user(user.id, user.username or "", user.full_name)
    user_row = await db.get_user(user.id)
    order_count = await db.count_orders(user.id)
    await message.answer(texts.profile_text(user_row, order_count), reply_markup=profile_kb())


@router.message(TopupInput.amount)
async def topup_custom_amount(
    message: Message, state: FSMContext, db: Database, crypto: CryptoPayAPI
) -> None:
    try:
        amount_cents = parse_amount_to_cents(message.text or "")
    except ValueError:
        await message.answer("⚠️ Не понял сумму. Пример: 1.25")
        return

    if amount_cents < MIN_TOPUP_CENTS:
        await message.answer("⚠️ Минимум 0.05 USDT")
        return

    await state.clear()

    try:
        text, kb = await _create_topup_invoice(message.from_user.id, amount_cents, db, crypto)
    except CryptoPayError:
        await message.answer("❌ Не удалось создать счет")
        return

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "back_profile")
async def back_profile(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    order_count = await db.count_orders(callback.from_user.id)
    await _safe_edit(callback.message, texts.profile_text(user, order_count), reply_markup=profile_kb())
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery, db: Database) -> None:
    await _render_my_orders(callback.message, callback.from_user.id, db, edit=True)
    await callback.answer()


@router.message(F.text.in_(["🧾 Мои покупки", "Мои покупки"]))
async def my_orders_message(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return
    await _render_my_orders(message, user.id, db, edit=False)


@router.callback_query(CheckCb.filter())
async def check_invoice(
    callback: CallbackQuery,
    callback_data: CheckCb,
    db: Database,
    crypto: CryptoPayAPI,
) -> None:
    invoice = await crypto.get_invoice(callback_data.invoice_id)
    if not invoice:
        await callback.answer("❌ Счет не найден", show_alert=True)
        return

    status = invoice.get("status")
    if status != "paid":
        if status == "active":
            await callback.answer("⏳ Платеж еще не подтвержден", show_alert=True)
        else:
            await callback.answer("❌ Счет не оплачен", show_alert=True)
        return

    if callback_data.kind == "order":
        order = await db.get_order(callback_data.internal_id)
        if not order or order["user_id"] != callback.from_user.id:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        if order["status"] == "paid":
            await callback.answer("ℹ️ Заказ уже оплачен", show_alert=True)
            return
        await db.set_order_paid(order["id"])
        product = await db.get_product(order["product_id"])
        await callback.message.answer(texts.order_paid_text(product["title"], product["content"]))
        await callback.answer("✅ Оплата подтверждена")
        return

    if callback_data.kind == "topup":
        topup = await db.get_topup(callback_data.internal_id)
        if not topup or topup["user_id"] != callback.from_user.id:
            await callback.answer("❌ Пополнение не найдено", show_alert=True)
            return
        if topup["status"] == "paid":
            await callback.answer("ℹ️ Баланс уже пополнен", show_alert=True)
            return
        await db.set_topup_paid(topup["id"])
        await db.update_balance(callback.from_user.id, int(topup["amount_cents"]))
        user = await db.get_user(callback.from_user.id)
        balance = cents_to_amount(int(user["balance_cents"]))
        await callback.message.answer(f"✅ Баланс пополнен. Текущий баланс: <b>{balance} USDT</b>")
        await callback.answer("Готово")
        return

    await callback.answer("Неизвестный тип счета", show_alert=True)
