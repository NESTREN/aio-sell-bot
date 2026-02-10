from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import html


def parse_amount_to_cents(text: str) -> int:
    value = text.strip().replace(",", ".")
    try:
        dec = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid_amount") from exc

    if dec <= 0:
        raise ValueError("invalid_amount")

    cents = int((dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return cents


def cents_to_amount(cents: int) -> str:
    return f"{cents / 100:.2f}"


def escape(text: str) -> str:
    return html.escape(text or "")


def format_product(product: dict | object) -> str:
    title = escape(getattr(product, "title", None) or product["title"])
    description = escape(getattr(product, "description", None) or product["description"])
    price_cents = getattr(product, "price_cents", None)
    if price_cents is None:
        price_cents = product["price_cents"]

    return (
        f"🛍️ <b>{title}</b>\n"
        f"📝 {description}\n"
        f"💎 Цена: <b>{cents_to_amount(int(price_cents))} USDT</b>"
    )
