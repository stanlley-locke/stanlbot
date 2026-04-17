import logging
from typing import Optional
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

class OCRService:
    """
    Cloud-based OCR service using Gemini Vision API.
    Replaces local EasyOCR to save RAM and Disk on Micro instances.
    """
    async def extract_text(self, image_path: str) -> Optional[str]:
        """Extract text from locally saved image using Gemini Cloud Vision"""
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # Use Gemini Vision for OCR
            # Prompt is optimized for raw text extraction
            text = await llm_service.analyze_image(
                image_bytes=image_bytes,
                prompt="OCR: Extract all readable text from this image exactly as it appears. Return raw text only."
            )
            
            if text and "OCR Error" not in text:
                return text
            return None
            
        except Exception as e:
            logger.error(f"Cloud OCR Error: {e}")
            return None

ocr_service = OCRService()
