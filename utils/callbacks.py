from aiogram.filters.callback_data import CallbackData


class ProductCb(CallbackData, prefix="prod"):
    action: str
    product_id: int


class CatalogPageCb(CallbackData, prefix="cat"):
    page: int


class CatalogItemCb(CallbackData, prefix="cati"):
    product_id: int
    page: int


class PayCb(CallbackData, prefix="pay"):
    method: str
    product_id: int


class CheckCb(CallbackData, prefix="check"):
    kind: str  # order | topup
    invoice_id: str
    internal_id: int


class TopupCb(CallbackData, prefix="topup"):
    amount: int


class AdminProductCb(CallbackData, prefix="ap"):
    action: str  # toggle
    product_id: int


class AdminUserPageCb(CallbackData, prefix="aup"):
    page: int


class AdminUserActionCb(CallbackData, prefix="aua"):
    action: str  # view | balance_add | balance_sub | balance_set | orders
    user_id: int
    page: int = 0
