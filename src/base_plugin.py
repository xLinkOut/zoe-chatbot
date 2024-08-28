from abc import ABC, abstractmethod
from logging import Logger

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from database import Database


class BasePlugin(ABC):
    def __init__(
        self,
        application: Application,
        logger: Logger,
        database: Database,
        scheduler: AsyncIOScheduler,
        admin_chat_ids: set[str],
    ):
        self.application = application
        self.logger = logger
        self.database = database
        self.scheduler = scheduler
        self.admin_chat_ids = admin_chat_ids

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return "No description available."

    @property
    def commands(self) -> dict[str, str]:
        return {}

    @abstractmethod
    def register_handlers(self) -> None:
        pass

    def _can_use_this_command(self, user_chat_id: str | int) -> bool:
        return not self.admin_chat_ids or str(user_chat_id) in self.admin_chat_ids