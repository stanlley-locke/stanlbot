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
            """Generate response from Gemini with token optimization"""
            if not self._initialized: return "AI currently offline."
            
            try:
                # Local confidence check: If context is very specific and 
                # prompt is simple, we could theoretically skip but 
                # for now let's just optimize the prompt.
                
                await self._check_rate_limit()
                
                # Token-focused prompt structure
                full_prompt = f"SYS: {system_instruction or SYSTEM_INSTRUCTIONS['default']}\n"
                if context:
                    full_prompt += f"CTX: {context}\n"
                full_prompt += f"USR: {prompt}"
                
                # Adjust generation config for brevity
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
                
                response = await asyncio.to_thread(
                    self._model.generate_content, 
                    full_prompt,
                    generation_config=generation_config
                )
                
                if response and response.text:
                    return response.text.strip()
                return "No response from AI."
                
            except Exception as e:
                # ... error handling ...
                return f"Error: {str(e)}"

        async def analyze_image(
            self, 
            image_bytes: bytes, 
            prompt: str = "Extract all text from this image.",
            mime_type: str = "image/jpeg"
        ) -> Optional[str]:
            """Cloud OCR and Image analysis using Gemini Vision"""
            if not self._initialized: return "AI currently offline."
            
            try:
                await self._check_rate_limit()
                
                # Format for Gemini Multimodal
                content = [
                    prompt,
                    {"mime_type": mime_type, "data": image_bytes}
                ]
                
                response = await asyncio.to_thread(
                    self._model.generate_content,
                    content
                )
                
                if response and response.text:
                    return response.text.strip()
                return "No text detected by Vision API."
                
            except Exception as e:
                logger.error(f"Vision API error: {e}")
                return f"OCR Error: {str(e)}"

        async def parse_expense(self, message: str) -> Optional[Dict[str, Any]]:
            """Highly optimized expense parser for Free Tier"""
            if not self._initialized: return None
            
            # Ultra-short instruction to save input tokens
            prompt = f"Extract JSON (amount, category, description, date): {message}"
            system = "Output raw JSON ONLY. Categories: food, transport, utilities, entertainment, shopping, health, education, other."
            
            try:
                raw = await self.generate_response(prompt, system_instruction=system)
                if raw:
                    import json
                    raw = raw.replace("```json", "").replace("```", "").strip()
                    return json.loads(raw)
            except:
                pass
            return None
        
        async def summarize_text(self, text: str, max_length: int = 100) -> Optional[str]:
            """Token-efficient summarizer"""
            prompt = f"TL;DR in <{max_length} words: {text}"
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
