import asyncio
import logging
import sys
from pathlib import Path
from config import settings
from utils.logging_config import setup_logging

def initialize():
    Path("logs").mkdir(exist_ok=True)
    setup_logging(level=settings.LOG_LEVEL, log_dir="logs")
    logging.info("Initializing StanlBot...")

async def main():
    initialize()
    
    try:
        from core.dispatcher import setup_dispatcher
        dp = await setup_dispatcher()
        
        logging.info("Starting long polling loop...")
        await dp.start_polling(skip_updates=True)
    except KeyboardInterrupt:
        logging.info("Shutdown requested by user.")
    except Exception as e:
        logging.critical(f"Fatal startup error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("Bot process terminated.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        sys.exit(1)