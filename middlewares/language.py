import json
import logging
from pathlib import Path
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config import settings

logger = logging.getLogger(__name__)
TRANSLATIONS_PATH = Path("data/translations")

class LanguageMiddleware(BaseMiddleware):
    def __init__(self):
        self._translations: Dict[str, dict] = {}
        self._load_translations()

    def _load_translations(self):
        if not TRANSLATIONS_PATH.exists():
            return
        for file in TRANSLATIONS_PATH.glob("*.json"):
            lang = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self._translations[lang] = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load translation {file}: {e}")

    def _resolve(self, lang: str, key: str, default: str = "") -> str:
        chain = [lang, settings.DEFAULT_LANG, "en"]
        for l in chain:
            val = self._translations.get(l, {}).get(key)
            if val:
                return val
        return default

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        from database.queries import get_user_profile
        
        profile = await get_user_profile(event.from_user.id)
        lang = profile[3] if profile else settings.DEFAULT_LANG
        data["lang"] = lang
        data["t"] = lambda key, default="": self._resolve(lang, key, default)
        return await handler(event, data)