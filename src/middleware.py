from telegram import Bot, BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CallbackContext, CommandHandler, MessageHandler, filters


class MiddlewareBot(Bot):
    commands = {
        "start": "Start the bot and display the list of loaded plugins",
        "help": "Display a help message with all available commands",
    }

    def __init__(self, token, database):
        super().__init__(token)
        self._database = database
        self._first_run = True

    async def start(self, update: Update, context: CallbackContext):
        with self._database:
            self._database.add_user(
                update.effective_user.id,
                update.effective_user.username,
                update.effective_user.first_name,
                update.effective_user.last_name,
                update.effective_user.language_code,
            )

        keyboard = [[KeyboardButton(plugin)] for plugin in sorted(plugin.name for plugin in context.bot_data["plugins"])]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)

        if self._first_run:
            commands = []
            for plugin in context.application.bot_data.get("plugins", []) + [self]:
                for command, description in plugin.commands.items():
                    commands.append(BotCommand(command, description))
            await context.application.bot.set_my_commands(commands)
            self._first_run = False

        await update.message.reply_text(
            f"Hi {update.effective_user.first_name or updates.effective_user.username}! "
            "Which plugin do you want to use today?",
            reply_markup=reply_markup,
        )

    async def help_me(self, update: Update, context: CallbackContext):
        commands = ""
        for plugin in context.bot_data["plugins"]:
            for command, description in plugin.commands.items():
                command += f"{command}: {description}\n"
        
        # This solution loop over bot handlers, more reliable than commands dict
        # command_handlers = []
        # for handler in context.application.handlers.get(0, []):
        #     if isinstance(handler, CommandHandler):
        #         command_handlers.extend(handler.commands)
        # command_handlers = "\n".join(f"/{command}" for command in command_handlers)

        await update.message.reply_text(commands)

    async def plugin_details(self, update: Update, context: CallbackContext):
        for plugin in context.bot_data["plugins"]:
            if plugin.name == update.message.text:
                break
        else:
            await update.message.reply_text(f"Plugin '{update.message.text}' not found.")
            return

        message = f"{plugin.name}\n\n{plugin.description}\n\n"
        message += "\n".join(
            f"{command}: {description}"
            for command, description in plugin.commands.items()
        )

        await update.message.reply_text(message)

    async def send_message(self, chat_id, text, *args, **kwargs) -> Message:
        message = await super().send_message(chat_id, text, *args, **kwargs)

        with self._database:
            self._database.execute(
                """
                INSERT INTO users_messages (message_id, chat_id, user_id, message_text, direction)
                VALUES (?, ?, ?, ?, 'out')
                """,
                (
                    message.message_id,
                    message.chat_id,
                    message.from_user.id,
                    message.text,
                ),
            )

        return message

    async def log_incoming_message(self, update: Update, context: CallbackContext):
        with self._database:
            self._database.execute(
                """
                INSERT INTO users_messages (message_id, chat_id, user_id, message_text, direction)
                VALUES (?, ?, ?, ?, 'in')
                """,
                (
                    update.message.message_id,
                    update.effective_chat.id,
                    update.effective_user.id,
                    update.message.text,
                ),
            )
