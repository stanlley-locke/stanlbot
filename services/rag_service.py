"""
RAG Service using ChromaDB for vector storage and semantic search.
Provides context retrieval for LLM-enhanced responses.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

from config import settings

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    
    class RAGService:
        def __init__(self):
            self._initialized = False
            self._client = None
            self._collection = None
            self._embedding_fn = None
            
            if settings.ENABLE_RAG:
                try:
                    # Offload embeddings to Gemini Cloud to save local RAM
                    from chromadb.utils import embedding_functions
                    self._embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                        api_key=settings.GEMINI_API_KEY
                    )
                    
                    # Initialize ChromaDB with persistent storage
                    chroma_path = settings.CHROMA_DB_PATH
                    chroma_path.mkdir(parents=True, exist_ok=True)
                    
                    self._client = chromadb.PersistentClient(
                        path=str(chroma_path),
                        settings=ChromaSettings(anonymized_telemetry=False)
                    )
                    
                    self._collection = self._client.get_or_create_collection(
                        name="stanlbot_knowledge",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=self._embedding_fn
                    )
                    
                    self._initialized = True
                    logger.info("RAG Service initialized with Gemini Cloud Embeddings (RAM optimized)")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize ChromaDB: {e}")
            else:
                logger.info("RAG disabled in settings")
        
        def _generate_id(self, content: str, user_id: int) -> str:
            """Generate unique ID for document"""
            return hashlib.md5(f"{user_id}:{content[:100]}".encode()).hexdigest()
        
        async def add_document(
            self, 
            user_id: int, 
            content: str, 
            metadata: Optional[Dict[str, Any]] = None
        ) -> bool:
            """Add document to vector store"""
            if not self._initialized: return False
            
            try:
                doc_id = self._generate_id(content, user_id)
                doc_metadata = {
                    "user_id": str(user_id),
                    "source": metadata.get("source", "manual") if metadata else "manual",
                    "tags": metadata.get("tags", "[]") if metadata else "[]",
                    **(metadata or {})
                }
                
                # Run in thread to avoid blocking event loop
                await asyncio.to_thread(
                    self._collection.upsert,
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[doc_metadata]
                )
                return True
            except Exception as e:
                logger.error(f"Error adding document: {e}")
                return False
        
        async def search_similar(
            self, 
            user_id: int, 
            query: str, 
            top_k: Optional[int] = None
        ) -> List[Dict[str, Any]]:
            """Search for similar documents with user isolation"""
            if not self._initialized: return []
            
            top_k = top_k or settings.RAG_TOP_K
            
            try:
                # Run in thread to avoid blocking event loop
                results = await asyncio.to_thread(
                    self._collection.query,
                    query_texts=[query],
                    n_results=top_k,
                    where={"user_id": str(user_id)},
                    include=["documents", "metadatas", "distances"]
                )
                
                if not results['ids'] or not results['ids'][0]:
                    return []
                
                formatted_results = []
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        'id': doc_id,
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })
                
                return formatted_results
            except Exception as e:
                logger.error(f"Error searching documents: {e}")
                return []
        
        async def get_context_for_query(
            self, 
            user_id: int, 
            query: str
        ) -> Optional[str]:
            """Retrieve relevant context for a query"""
            results = await self.search_similar(user_id, query)
            
            if not results:
                return None
            
            context_parts = []
            for result in results:
                context_parts.append(f"- {result['content']}")
            
            return "\n".join(context_parts)
        
        async def delete_user_documents(self, user_id: int) -> bool:
            """Delete all documents for a user (GDPR compliance)"""
            if not self._initialized:
                return False
            
            try:
                # Get all user documents
                results = self._collection.get(
                    where={"user_id": str(user_id)},
                    include=["ids"]
                )
                
                if results['ids']:
                    self._collection.delete(ids=results['ids'])
                    logger.info(f"Deleted {len(results['ids'])} documents for user {user_id}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error deleting documents: {e}")
                return False
        
        async def get_stats(self, user_id: Optional[int] = None) -> Dict[str, int]:
            """Get collection statistics"""
            if not self._initialized:
                return {"total_documents": 0}
            
            try:
                if user_id:
                    results = self._collection.get(
                        where={"user_id": str(user_id)},
                        include=[]
                    )
                    count = len(results['ids']) if results['ids'] else 0
                else:
                    count = self._collection.count()
                
                return {"total_documents": count}
                
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return {"total_documents": 0}
    
    # Singleton instance
    rag_service = RAGService()
    
except ImportError:
    logger.warning("chromadb not installed. RAG features disabled.")
    
    class RAGService:
        async def add_document(self, *args, **kwargs):
            return False
        
        async def search_similar(self, *args, **kwargs):
            return []
        
        async def get_context_for_query(self, *args, **kwargs):
            return None
        
        async def delete_user_documents(self, *args, **kwargs):
            return False
        
        async def get_stats(self, *args, **kwargs):
            return {"total_documents": 0}
    
    rag_service = RAGService()
