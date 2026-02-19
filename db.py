import aiosqlite
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def init(self) -> None:
        assert self.conn is not None
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance_cents INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                crypto_invoice_id TEXT,
                crypto_pay_url TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                crypto_invoice_id TEXT,
                crypto_pay_url TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_products_active_id
                ON products(is_active, id DESC);
            CREATE INDEX IF NOT EXISTS idx_orders_user_status_id
                ON orders(user_id, status, id DESC);
            CREATE INDEX IF NOT EXISTS idx_orders_invoice
                ON orders(crypto_invoice_id);
            CREATE INDEX IF NOT EXISTS idx_topups_user_status_id
                ON topups(user_id, status, id DESC);
            CREATE INDEX IF NOT EXISTS idx_topups_invoice
                ON topups(crypto_invoice_id);
            CREATE INDEX IF NOT EXISTS idx_users_username
                ON users(username);
            """
        )
        await self.conn.commit()

    async def add_or_update_user(self, user_id: int, username: str, full_name: str) -> None:
        assert self.conn is not None
        row = await self.get_user(user_id)
        if row:
            await self.conn.execute(
                """
                UPDATE users
                SET
                    username = COALESCE(NULLIF(?, ''), username),
                    full_name = COALESCE(NULLIF(?, ''), full_name)
                WHERE id = ?
                """,
                (username, full_name, user_id),
            )
        else:
            await self.conn.execute(
                "INSERT INTO users (id, username, full_name, balance_cents, created_at) VALUES (?, ?, ?, 0, ?)",
                (user_id, username, full_name, utc_now()),
            )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> Optional[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return await cur.fetchone()

    async def update_balance(self, user_id: int, delta_cents: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
            (delta_cents, user_id),
        )
        await self.conn.commit()

    async def set_balance(self, user_id: int, new_balance_cents: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE users SET balance_cents = ? WHERE id = ?",
            (new_balance_cents, user_id),
        )
        await self.conn.commit()

    async def list_active_products(self) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY id DESC"
        )
        return await cur.fetchall()

    async def list_active_products_paged(
        self, limit: int = 10, offset: int = 0
    ) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cur.fetchall()

    async def count_active_products(self) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT COUNT(1) AS cnt FROM products WHERE is_active = 1"
        )
        row = await cur.fetchone()
        return int(row["cnt"]) if row else 0

    async def list_all_products(self) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM products ORDER BY id DESC")
        return await cur.fetchall()

    async def list_users(self, limit: int = 10, offset: int = 0) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cur.fetchall()

    async def count_users(self) -> int:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT COUNT(1) AS cnt FROM users")
        row = await cur.fetchone()
        return int(row["cnt"]) if row else 0

    async def search_users(self, query: str, limit: int = 10) -> list[aiosqlite.Row]:
        assert self.conn is not None
        like = f"%{query}%"
        cur = await self.conn.execute(
            """
            SELECT * FROM users
            WHERE username LIKE ? OR full_name LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (like, like, limit),
        )
        return await cur.fetchall()

    async def get_product(self, product_id: int) -> Optional[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return await cur.fetchone()

    async def create_product(
        self, title: str, description: str, price_cents: int, content: str
    ) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            "INSERT INTO products (title, description, price_cents, content, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (title, description, price_cents, content, utc_now()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def toggle_product(self, product_id: int, is_active: bool) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE products SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, product_id),
        )
        await self.conn.commit()

    async def create_order(
        self,
        user_id: int,
        product_id: int,
        amount_cents: int,
        payment_method: str,
        crypto_invoice_id: Optional[str] = None,
        crypto_pay_url: Optional[str] = None,
    ) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            """
            INSERT INTO orders
            (user_id, product_id, amount_cents, status, payment_method, crypto_invoice_id, crypto_pay_url, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
            """,
            (user_id, product_id, amount_cents, payment_method, crypto_invoice_id, crypto_pay_url, utc_now()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_order(self, order_id: int) -> Optional[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cur.fetchone()

    async def get_order_by_invoice(self, invoice_id: str) -> Optional[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM orders WHERE crypto_invoice_id = ?", (invoice_id,)
        )
        return await cur.fetchone()

    async def set_order_paid(self, order_id: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ?",
            (utc_now(), order_id),
        )
        await self.conn.commit()

    async def list_user_orders(self, user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            """
            SELECT o.*, p.title
            FROM orders o
            JOIN products p ON p.id = o.product_id
            WHERE o.user_id = ?
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return await cur.fetchall()

    async def list_recent_orders(self, limit: int = 20) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            """
            SELECT o.*, p.title
            FROM orders o
            JOIN products p ON p.id = o.product_id
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cur.fetchall()

    async def create_topup(
        self, user_id: int, amount_cents: int, crypto_invoice_id: str, crypto_pay_url: str
    ) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            """
            INSERT INTO topups
            (user_id, amount_cents, status, crypto_invoice_id, crypto_pay_url, created_at)
            VALUES (?, ?, 'pending', ?, ?, ?)
            """,
            (user_id, amount_cents, crypto_invoice_id, crypto_pay_url, utc_now()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_topup(self, topup_id: int) -> Optional[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute("SELECT * FROM topups WHERE id = ?", (topup_id,))
        return await cur.fetchone()

    async def get_topup_by_invoice(self, invoice_id: str) -> Optional[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM topups WHERE crypto_invoice_id = ?", (invoice_id,)
        )
        return await cur.fetchone()

    async def set_topup_paid(self, topup_id: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE topups SET status = 'paid', paid_at = ? WHERE id = ?",
            (utc_now(), topup_id),
        )
        await self.conn.commit()

    async def list_user_topups(self, user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT * FROM topups WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return await cur.fetchall()

    async def count_orders(self, user_id: int) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            "SELECT COUNT(1) AS cnt FROM orders WHERE user_id = ? AND status = 'paid'",
            (user_id,),
        )
        row = await cur.fetchone()
        return int(row["cnt"]) if row else 0
