import time
import asyncio
import logging
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, max_messages: int = 10, window_seconds: int = 60):
        self.max_msgs = max_messages
        self.window = window_seconds
        self._history: Dict[int, list[float]] = {}
        self._lock = asyncio.Lock()

    def _prune(self, user_id: int, now: float):
        if user_id in self._history:
            self._history[user_id] = [t for t in self._history[user_id] if now - t < self.window]

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()
        
        async with self._lock:
            self._prune(user_id, now)
            if user_id not in self._history:
                self._history[user_id] = []
                
            if len(self._history[user_id]) >= self.max_msgs:
                if isinstance(event, Message):
                    await event.answer("Rate limit exceeded. Please wait before sending another message.")
                return None
                
            self._history[user_id].append(now)
            
        return await handler(event, data)