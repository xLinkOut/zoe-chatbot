from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from base_plugin import BasePlugin


class ExampleEcho(BasePlugin):
    name = "EchoBot"
    description = "Demonstrative bot plugin."
    commands = {
        "/ee_echo": "Echo the user's message",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_tables()
        self._register_scheduler()

    def _create_tables(self):
        with self.database:
            self.database.execute(
                """
                CREATE TABLE IF NOT EXISTS example_echo_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """
            )

    def _register_scheduler(self):
        self.scheduler.add_job(
            self._good_morning,
            "cron",
            hour=9,
            max_instances=1,
            coalesce=True,
            id="example_echo_good_morning",
        )

    def register_handlers(self):
        self.application.add_handler(CommandHandler("ee_echo", self.echo))

    async def echo(self, update: Update, context: CallbackContext):
        with self.database:
            self.database.execute(
                "INSERT INTO example_echo_messages (chat_id, message) VALUES (?, ?)",
                (update.effective_chat.id, update.message.text),
            )

        await update.message.reply_text(update.message.text)

    async def _good_morning(self):
        users = self.database.execute("SELECT DISTINCT chat_id FROM example_echo_messages")
        for user in users:
            await self.application.bot.send_message(chat_id=user["chat_id"], text="Good morning!")
