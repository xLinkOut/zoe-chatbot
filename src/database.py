import sqlite3


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT
            )"""
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                user_id INTEGER,
                message_text TEXT,
                direction TEXT,  -- 'in' o 'out'
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )

    def add_user(self, *args):
        self.connection.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)", (*args,))
        self.connection.commit()

    def get_user(self, chat_id):
        return self.connection.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()

    def execute(self, query: str, params: tuple = ()):
        return self.connection.execute(query, params)

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
