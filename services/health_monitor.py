import logging
import asyncio
import aiohttp
from config import settings

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, timeout: int = 10, retries: int = 3):
        self.timeout = timeout
        self.retries = retries

    async def check(self, url: str) -> bool:
        if not url:
            return True
            
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=self.timeout) as resp:
                        if resp.status == 200:
                            return True
            except Exception as e:
                logger.warning(f"Health check failed (attempt {attempt + 1}): {e}")
            if attempt < self.retries - 1:
                await asyncio.sleep(2 ** attempt)
        return False

health_monitor = HealthMonitor()