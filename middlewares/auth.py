import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config import settings

logger = logging.getLogger(__name__)
ADMIN_COMMANDS = {"ec2", "deploy", "logs", "backup", "broadcast", "shutdown"}

class AdminGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            cmd = event.text.split()[0].lstrip("/").lower()
            if cmd in ADMIN_COMMANDS and event.from_user.id not in settings.ADMIN_IDS:
                logger.warning(f"Unauthorized admin attempt by user {event.from_user.id}")
                await event.answer("Access denied. This command requires administrator privileges.")
                return None
        return await handler(event, data)