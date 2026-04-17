import time
import asyncio
import logging
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

class CacheMiddleware(BaseMiddleware):
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    def _key(self, event) -> str:
        if isinstance(event, Message):
            return f"msg_{event.from_user.id}_{event.text}"
        elif isinstance(event, CallbackQuery):
            return f"cb_{event.from_user.id}_{event.data}"
        return f"evt_{event.from_user.id}"

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        key = self._key(event)
        now = time.time()
        
        async with self._lock:
            if key in self._cache:
                val, ts = self._cache[key]
                if now - ts < self.ttl:
                    return val
                    
        result = await handler(event, data)
        async with self._lock:
            self._cache[key] = (result, now)
            self._cache = {k: v for k, v in self._cache.items() if now - v[1] < self.ttl}
            
        return result