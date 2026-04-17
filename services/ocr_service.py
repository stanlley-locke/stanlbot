import logging
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import easyocr
    import numpy as np
    from PIL import Image
    
    class OCRService:
        def __init__(self):
            self._reader = None
            self._initialized = False
            
        async def _get_reader(self):
            if not self._reader:
                # Load models in a separate thread
                # This will download ~100MB on first run
                self._reader = await asyncio.to_thread(
                    easyocr.Reader, ['en'], gpu=False
                )
                self._initialized = True
            return self._reader

        async def extract_text(self, image_path: str) -> Optional[str]:
            """Extract text from image locally"""
            try:
                reader = await self._get_reader()
                
                # Perform OCR in thread
                results = await asyncio.to_thread(
                    reader.readtext, image_path, detail=0
                )
                
                if results:
                    return " ".join(results)
                return None
                
            except Exception as e:
                logger.error(f"OCR Error: {e}")
                return None
                
    ocr_service = OCRService()

except ImportError:
    logger.warning("easyocr not installed. Local OCR disabled.")
    
    class OCRService:
        async def extract_text(self, image_path: str) -> Optional[str]:
            return None
            
    ocr_service = OCRService()
