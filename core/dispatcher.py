import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from middlewares import (
    AdminGateMiddleware, RateLimitMiddleware, 
    ErrorHandlerMiddleware, LanguageMiddleware, CacheMiddleware
)
from routers import ALL_ROUTERS
from services import init_scheduler

logger = logging.getLogger(__name__)

async def on_startup(bot: Bot, dp: Dispatcher):
    logger.info("Initializing bot lifecycle...")
    from database import init_database
    await init_database()
    
    dp.startup.update(
        {
            "bot_token_hash": hash(settings.BOT_TOKEN),
            "admin_ids": settings.ADMIN_IDS,
            "semantic_enabled": settings.ENABLE_SEMANTIC_SEARCH
        }
    )
    
    init_scheduler(bot)
    logger.info("Bot startup complete. Polling initiated.")

async def on_shutdown(bot: Bot, dp: Dispatcher):
    from database import db
    from services import scheduler
    
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await db.close()
    await bot.session.close()
    logger.info("Graceful shutdown complete.")

async def setup_dispatcher() -> Dispatcher:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Middleware order matters: outer to inner
    dp.message.middleware(CacheMiddleware(ttl_seconds=30))
    dp.message.middleware(RateLimitMiddleware(max_messages=10, window_seconds=60))
    dp.message.middleware(LanguageMiddleware())
    dp.message.middleware(AdminGateMiddleware())
    
    dp.errors.register(ErrorHandlerMiddleware())
    
    for router in ALL_ROUTERS:
        dp.include_router(router)
        
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    return dp