from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
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
    """Initialize bot lifecycle: database, scheduler, commands."""
    logger.info("Initializing bot lifecycle...")
    
    from database import init_database
    await init_database()
    
    await _set_bot_commands(bot)
    
    init_scheduler(bot)
    
    logger.info("Bot startup complete. Polling initiated.")


async def on_shutdown(bot: Bot) -> None:
    """Graceful shutdown: close DB, stop scheduler, close session."""
    logger.info("Initiating graceful shutdown...")
    
    from services import scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)
    
    from database import db
    await db.close()
    
    await bot.session.close()
    
    logger.info("Graceful shutdown complete.")


async def _set_bot_commands(bot: Bot) -> None:
    """Register slash commands visible in Telegram chat input."""
    commands = [
        BotCommand(command="start", description="Initialize your profile"),
        BotCommand(command="help", description="Show available commands"),
        BotCommand(command="profile", description="View your account status"),
        BotCommand(command="note", description="Save a quick note"),
        BotCommand(command="notes", description="List your saved notes"),
        BotCommand(command="find", description="Search notes and history"),
        BotCommand(command="assign", description="Track an assignment"),
        BotCommand(command="assignments", description="View pending assignments"),
        BotCommand(command="recipe", description="Get a meal suggestion"),
        BotCommand(command="grocery", description="Manage grocery list"),
        BotCommand(command="trivia", description="Start a quiz"),
        BotCommand(command="checkin", description="Daily check-in for points"),
        BotCommand(command="ec2", description="Check EC2 status (admin)"),
        BotCommand(command="deploy", description="Trigger deployment (admin)"),
        BotCommand(command="logs", description="View recent logs (admin)"),
        BotCommand(command="backup", description="Create DB backup (admin)"),
    ]
    await bot.set_my_commands(commands)


async def setup_dispatcher() -> tuple[Dispatcher, Bot]:
    """
    Create and configure the Dispatcher and Bot instances.
    
    Returns:
        tuple[Dispatcher, Bot]: Configured dispatcher and bot ready for polling.
    """
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middlewares in order (outermost to innermost)
    dp.message.middleware(CacheMiddleware(ttl_seconds=30))
    dp.message.middleware(
        RateLimitMiddleware(
            max_messages=settings.RATE_LIMIT_MSGS,
            window_seconds=settings.RATE_LIMIT_WINDOW
        )
    )
    dp.message.middleware(LanguageMiddleware())
    dp.message.middleware(AdminGateMiddleware())
    
    dp.errors.register(ErrorHandlerMiddleware())
    
    for router in ALL_ROUTERS:
        dp.include_router(router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    return dp, bot