from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram.client.bot import Bot
from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import settings
from middlewares import (
    AdminGateMiddleware,
    RateLimitMiddleware,
    ErrorHandlerMiddleware,
    LanguageMiddleware,
    CacheMiddleware,
)
from routers import ALL_ROUTERS
from services import init_scheduler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Initializing bot lifecycle...")
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook cleared for polling mode")
    
    from database import init_database
    await init_database()
    await _set_bot_commands(bot)
    init_scheduler(bot)
    logger.info("Bot startup complete. Polling initiated.")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Initiating graceful shutdown...")
    from services import scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)
    from database import db
    await db.close()
    await bot.session.close()
    logger.info("Graceful shutdown complete.")


async def _set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Initialize profile & open menu"),
        BotCommand(command="menu", description="Open main dashboard"),
        BotCommand(command="help", description="Show command guide"),
        BotCommand(command="note", description="Save a quick note"),
        BotCommand(command="notes", description="Browse saved notes"),
        BotCommand(command="find", description="Search notes & chats"),
        BotCommand(command="assign", description="Track an assignment"),
        BotCommand(command="assignments", description="View pending tasks"),
        BotCommand(command="recipe", description="Get meal suggestion"),
        BotCommand(command="grocery", description="Manage grocery list"),
        BotCommand(command="trivia", description="Start knowledge quiz"),
        BotCommand(command="expense", description="Log an expense (AI-powered)"),
        BotCommand(command="expenses", description="View spending summary"),
        BotCommand(command="ask", description="Ask AI anything (RAG-enabled)"),
        BotCommand(command="summarize", description="Summarize text with AI"),
        BotCommand(command="teach", description="Add knowledge to memory"),
        BotCommand(command="settings", description="Preferences & data control"),
        BotCommand(command="ec2", description="Server status (admin)"),
        BotCommand(command="deploy", description="Trigger deployment (admin)"),
    ]
    await bot.set_my_commands(commands)


async def setup_dispatcher() -> tuple[Dispatcher, Bot]:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Cache & Rate Limit
    dp.message.middleware(CacheMiddleware(ttl_seconds=30))
    dp.callback_query.middleware(CacheMiddleware(ttl_seconds=30))
    dp.message.middleware(RateLimitMiddleware(max_messages=settings.RATE_LIMIT_MSGS, window_seconds=settings.RATE_LIMIT_WINDOW))
    dp.callback_query.middleware(RateLimitMiddleware(max_messages=settings.RATE_LIMIT_MSGS, window_seconds=settings.RATE_LIMIT_WINDOW))
    
    # Language & Auth
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    dp.message.middleware(AdminGateMiddleware())
    dp.callback_query.middleware(AdminGateMiddleware())
    
    # Error Handler (Registered as middleware, NOT via dp.errors)
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    
    for router in ALL_ROUTERS:
        dp.include_router(router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    return dp, bot