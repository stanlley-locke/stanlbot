import logging
import os
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message
from services.ocr_service import ocr_service
from services.rag_service import rag_service
from database.queries import save_note
from utils.formatters import EMOJI

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.photo)
async def handle_photo(message: Message):
    """Handle incoming photos with local OCR"""
    await message.answer("🔍 Processing image locally...")
    
    # Download photo
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    os.makedirs("storage/temp", exist_ok=True)
    file_path = f"storage/temp/{photo.file_id}.jpg"
    await message.bot.download_file(file.file_path, file_path)
    
    # Run OCR
    text = await ocr_service.extract_text(file_path)
    
    if not text:
        await message.answer(f"{EMOJI['alert']} No text detected in the image.")
        return

    # Store as a note automatically
    await save_note(message.from_user.id, text, tags=["ocr"], source="image")
    await rag_service.add_document(message.from_user.id, text, metadata={"source": "ocr"})
    
    preview = text[:200] + "..." if len(text) > 200 else text
    await message.answer(
        f"{EMOJI['success']} <b>Text Extracted & Saved!</b>\n\n"
        f"<code>{preview}</code>\n\n"
        "This note is now searchable and part of your AI memory."
    )
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

@router.message(F.voice)
async def handle_voice(message: Message):
    """Placeholder for Voice Note handling"""
    await message.answer(f"{EMOJI['ai']} Voice transcription coming soon to save your fingers!")
