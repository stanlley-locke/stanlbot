"""
LLM Service with Gemini API integration and rate limiting.
Handles AI conversations, expense parsing, and RAG-enhanced responses.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque
import asyncio

from config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    
    class GeminiRateLimitError(Exception):
        """Custom exception for rate limit errors"""
        pass
    
    class LLMService:
        def __init__(self):
            self._initialized = False
            self._model = None
            self._request_timestamps = deque()
            self._lock = asyncio.Lock()
            
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel(settings.LLM_MODEL)
                self._initialized = True
                logger.info(f"LLM Service initialized with {settings.LLM_MODEL}")
            else:
                logger.warning("GEMINI_API_KEY not configured. LLM features disabled.")
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type(GeminiRateLimitError),
            reraise=True
        )
        async def _check_rate_limit(self):
            """Check and enforce rate limiting before making API calls"""
            async with self._lock:
                now = datetime.now()
                window_start = now - timedelta(minutes=1)
                
                # Remove old timestamps outside the window
                while self._request_timestamps and self._request_timestamps[0] < window_start:
                    self._request_timestamps.popleft()
                
                if len(self._request_timestamps) >= settings.LLM_RATE_LIMIT_PER_MIN:
                    oldest = self._request_timestamps[0]
                    wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time + 1)
                    return await self._check_rate_limit()
                
                self._request_timestamps.append(now)
        
        async def generate_response(
            self, 
            prompt: str, 
            context: Optional[str] = None,
            system_instruction: Optional[str] = None
        ) -> Optional[str]:
            """Generate response from Gemini with optional context"""
            if not self._initialized:
                return None
            
            try:
                await self._check_rate_limit()
                
                full_prompt = ""
                if system_instruction:
                    full_prompt += f"{system_instruction}\n\n"
                if context:
                    full_prompt += f"Context:\n{context}\n\n"
                full_prompt += f"User: {prompt}"
                
                response = await asyncio.to_thread(
                    self._model.generate_content, 
                    full_prompt
                )
                
                if response and response.text:
                    return response.text.strip()
                return None
                
            except Exception as e:
                error_name = type(e).__name__
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in error_name:
                    logger.warning(f"Gemini rate limit hit: {e}")
                    raise GeminiRateLimitError(f"Rate limited: {e}")
                logger.error(f"LLM generation error: {e}")
                return None
        
        async def parse_expense(self, message: str) -> Optional[Dict[str, Any]]:
            """Parse expense from natural language using LLM"""
            if not self._initialized:
                return None
            
            system_prompt = """You are an expense parser. Extract structured data from expense messages.
Return ONLY valid JSON with these fields:
- amount: float (numeric value only)
- category: string (food, transport, utilities, entertainment, shopping, health, education, other)
- description: string (brief description)
- date: string (YYYY-MM-DD format, use today if not specified)

Examples:
"Spent $15 on lunch" -> {"amount": 15.0, "category": "food", "description": "lunch", "date": "2024-01-15"}
"Bought groceries for $45.50 yesterday" -> {"amount": 45.5, "category": "food", "description": "groceries", "date": "2024-01-14"}
"""
            
            try:
                json_response = await self.generate_response(
                    message, 
                    system_instruction=system_prompt
                )
                
                if json_response:
                    import json
                    # Clean up markdown code blocks if present
                    json_response = json_response.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(json_response)
                    
                    # Validate required fields
                    if all(k in parsed for k in ["amount", "category", "description"]):
                        return parsed
                        
            except Exception as e:
                logger.error(f"Expense parsing error: {e}")
            
            return None
        
        async def summarize_text(self, text: str, max_length: int = 100) -> Optional[str]:
            """Summarize text using LLM"""
            if not self._initialized:
                return None
            
            prompt = f"Summarize this in under {max_length} words:\n{text}"
            return await self.generate_response(prompt)
    
    # Singleton instance
    llm_service = LLMService()
    
except ImportError:
    logger.warning("google-generativeai not installed. LLM features disabled.")
    
    class LLMService:
        async def generate_response(self, *args, **kwargs):
            return None
        
        async def parse_expense(self, *args, **kwargs):
            return None
        
        async def summarize_text(self, *args, **kwargs):
            return None
    
    llm_service = LLMService()
