import logging
import asyncio
import traceback
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest, TelegramUnauthorizedError
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
         Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramRetryAfter as e:
            logger.warning(f"Telegram rate limit: retry after {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            return await handler(event, data)
        except TelegramBadRequest as e:
            logger.error(f"Telegram Bad Request: {e}")
            if isinstance(event, Message):
                await event.answer("Invalid format. Please check your input.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Invalid request format.", show_alert=True)
            return None
        except TelegramUnauthorizedError as e:
            logger.critical(f"Bot token revoked: {e}")
            raise SystemExit(1)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Handler error for user {event.from_user.id}:\n{tb}")
            safe_msg = "An unexpected error occurred. Your data is safe. Try again shortly."
            if isinstance(event, Message):
                await event.answer(safe_msg)
            elif isinstance(event, CallbackQuery):
                await event.answer(safe_msg, show_alert=True)
            return None