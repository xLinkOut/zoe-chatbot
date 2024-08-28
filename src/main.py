import importlib.util
import logging
import os
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from base_plugin import BasePlugin
from database import Database
from middleware import MiddlewareBot

load_dotenv()

debug_mode = "--debug" in sys.argv

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
root_logger.addHandler(console_handler)

if not debug_mode:
    logging.getLogger("httpx").propagate = False

database = Database(db_path=os.getenv("DATABASE_PATH"))
middleware_bot = MiddlewareBot(token=os.getenv("TELEGRAM_TOKEN"), database=database)
application = Application.builder().bot(middleware_bot).build()
scheduler = AsyncIOScheduler(timezone=os.getenv("TIMEZONE", "UTC"))
admin_chat_ids = set(filter(None, (os.getenv("ADMIN_CHAT_IDS", "") or "").split(", ")))

application.bot_data["plugins"]: list[BasePlugin] = []

for plugin_dir in Path(os.getenv("PLUGINS_PATH")).iterdir():
    root_logger.debug(f"Searching for a plugin in {plugin_dir}")

    if not plugin_dir.is_dir():
        root_logger.warning(f"Found a plugin dir that is not a dir: {plugin_dir}")
        continue

    if not (plugin_file := plugin_dir / f"{plugin_dir.name}.py").exists():
        root_logger.warning(f"Found a plugin dir without a main file: {plugin_file}")
        continue

    try:
        spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        root_logger.debug(f"Searching for plugin class in module {plugin_module}")

        for attr in dir(plugin_module):
            PluginClass = getattr(plugin_module, attr)
            if (
                isinstance(PluginClass, type)
                and issubclass(PluginClass, BasePlugin)
                and PluginClass is not BasePlugin
            ):
                plugin_instance = PluginClass(
                    application,
                    logging.getLogger(PluginClass.__name__),
                    database,
                    scheduler,
                    admin_chat_ids,
                )
                plugin_instance.register_handlers()
                application.bot_data["plugins"].append(plugin_instance)
                root_logger.info(f"Loaded plugin {PluginClass.__name__}")

    except Exception as e:
        root_logger.error(f"An error occurred while loading plugin {plugin_file}: {e}")


application.add_handler(MessageHandler(filters.ALL, middleware_bot.log_incoming_message), group=-1)
application.add_handler(CommandHandler("start", middleware_bot.start))
application.add_handler(CommandHandler("help", middleware_bot.help_me))
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, middleware_bot.plugin_details)
)

scheduler.start()
application.run_polling()
