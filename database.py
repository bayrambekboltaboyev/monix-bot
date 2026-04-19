import sqlite3


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    name        TEXT    NOT NULL,
                    username    TEXT    DEFAULT '',
                    balance     INTEGER DEFAULT 0,
                    referrer_id INTEGER DEFAULT NULL,
                    joined_at   TEXT    DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS referrals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    joined_at   TEXT    DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    card       TEXT    NOT NULL,
                    amount     INTEGER NOT NULL,
                    status     TEXT    DEFAULT 'pending',
                    created_at TEXT    DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def register_user(self, user_id, name, username, referrer_id=None) -> bool:
        with self.get_conn() as conn:
            if conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone():
                return False
            conn.execute(
                "INSERT INTO users (user_id, name, username, referrer_id) VALUES (?,?,?,?)",
                (user_id, name, username, referrer_id)
            )
            return True

    def get_user(self, user_id):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_all_users(self):
        with self.get_conn() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]

    def add_balance(self, user_id, amount):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))

    def deduct_balance(self, user_id, amount):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (amount, user_id))

    def add_referral(self, referrer_id, referred_id):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO referrals (referrer_id, referred_id) VALUES (?,?)",
                (referrer_id, referred_id)
            )

    def get_referral_count(self, user_id) -> int:
        with self.get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) as c FROM referrals WHERE referrer_id=?", (user_id,)
            ).fetchone()["c"]

    def create_withdrawal(self, user_id, card, amount) -> int:
        with self.get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO withdrawals (user_id, card, amount) VALUES (?,?,?)",
                (user_id, card, amount)
            )
            return cur.lastrowid

    def get_pending_withdrawals(self):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT w.id, w.user_id, w.card, w.amount, w.created_at, u.name
                FROM withdrawals w JOIN users u ON u.user_id=w.user_id
                WHERE w.status='pending' ORDER BY w.created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def get_withdrawal(self, wid):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
            return dict(row) if row else None

    def approve_withdrawal(self, wid):
        with self.get_conn() as conn:
            conn.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (wid,))

    def reject_withdrawal(self, wid):
        with self.get_conn() as conn:
            conn.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wid,))

    def get_stats(self):
        with self.get_conn() as conn:
            return {
                "total_users": conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
                "total_referrals": conn.execute("SELECT COUNT(*) as c FROM referrals").fetchone()["c"],
                "total_bonuses": conn.execute(
                    "SELECT COALESCE(SUM(amount),0) as s FROM withdrawals WHERE status='approved'"
                ).fetchone()["s"],
                "pending_withdrawals": conn.execute(
                    "SELECT COUNT(*) as c FROM withdrawals WHERE status='pending'"
                ).fetchone()["c"],
            }
