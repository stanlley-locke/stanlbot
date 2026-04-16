import logging
import psutil
from config import settings

logger = logging.getLogger(__name__)

class MemoryGuard:
    def __init__(self, threshold_percent: int = None, margin: int = 5):
        self.threshold = threshold_percent or settings.MAX_MEMORY_PERCENT
        self.margin = margin
        self.heavy_features_disabled = False

    def check(self) -> bool:
        mem_percent = psutil.virtual_memory().percent
        
        if mem_percent >= self.threshold:
            if not self.heavy_features_disabled:
                logger.warning(f"High RAM usage detected: {mem_percent}%. Disabling heavy features.")
                self.heavy_features_disabled = True
            return True
        elif mem_percent <= (self.threshold - self.margin) and self.heavy_features_disabled:
            logger.info(f"RAM normalized: {mem_percent}%. Re-enabling heavy features.")
            self.heavy_features_disabled = False
            return False
        return self.heavy_features_disabled

    def should_load_embeddings(self) -> bool:
        if not settings.ENABLE_SEMANTIC_SEARCH:
            return False
        return not self.check()

memory_guard = MemoryGuard()