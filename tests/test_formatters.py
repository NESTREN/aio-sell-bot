import pytest

from utils.formatters import cents_to_amount, parse_amount_to_cents, format_product


def test_parse_amount_to_cents_accepts_comma_and_rounds() -> None:
    assert parse_amount_to_cents("1,235") == 124


def test_parse_amount_to_cents_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        parse_amount_to_cents("0")


def test_cents_to_amount_formats_two_digits() -> None:
    assert cents_to_amount(5) == "0.05"


def test_format_product_escapes_html() -> None:
    product = {
        "title": "<script>",
        "description": "desc & more",
        "price_cents": 199,
    }
    text = format_product(product)
    assert "&lt;script&gt;" in text
    assert "desc &amp; more" in text
    assert "1.99 USDT" in text
