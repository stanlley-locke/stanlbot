import logging
import asyncio
from typing import List, Dict, Any
from rapidfuzz import process, fuzz
from config import settings
from utils.memory_guard import memory_guard

logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self, fuzzy_threshold: int = 60):
        self.threshold = fuzzy_threshold
        self._embed_model = None

    async def search(self, query: str, documents: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        if not query or not documents:
            return []
        
        texts = [doc.get("content", doc.get("text", "")) for doc in documents]
        
        # CPU-bound operation moved to thread executor
        loop = asyncio.get_event_loop()
        matches = await loop.run_in_executor(
            None, lambda: process.extract(query, texts, scorer=fuzz.ratio, limit=limit * 2)
        )
        
        results = [documents[i] for _, _, i in matches if _ >= self.threshold][:limit]
        
        # Fallback to semantic if enabled and fuzzy results are insufficient
        if settings.ENABLE_SEMANTIC_SEARCH and len(results) < limit and memory_guard.should_load_embeddings():
            try:
                semantic_results = await self._semantic_search(query, documents, needed=limit - len(results))
                results.extend(semantic_results)
            except Exception as e:
                logger.warning(f"Semantic search fallback failed: {e}")
                
        return results[:limit]

    async def _semantic_search(self, query: str, documents: List[Dict[str, Any]], needed: int) -> List[Dict[str, Any]]:
        if self._embed_model is None:
            logger.info("Loading lightweight embedding model...")
            from fastembed import TextEmbedding
            self._embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5-q")
        
        # In production: precompute & cache embeddings in DB
        # This is a placeholder for on-the-fly computation
        return []

search_engine = SearchEngine()