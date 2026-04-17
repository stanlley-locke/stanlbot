import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from services.whatsapp_parser import WhatsAppParser
from database.queries import index_whatsapp_messages, search_whatsapp_messages
from utils.validators import sanitize_input

router = Router()
logger = logging.getLogger(__name__)

class ImportState(StatesGroup):
    waiting_file = State()

parser = WhatsAppParser()

@router.message(Command("import_whatsapp"))
async def cmd_import(message: Message, state: FSMContext):
    await message.answer("Send the WhatsApp .txt export file now.")
    await state.set_state(ImportState.waiting_file)

@router.message(ImportState.waiting_file, F.document)
async def handle_import(message: Message, state: FSMContext):
    if not message.document.file_name.endswith(".txt"):
        return await message.answer("Only .txt exports are supported.")
    await message.answer("Processing file... This may take a moment.")
    file = await message.bot.download(message.document.file_id, destination=f"storage/whatsapp_exports/{message.document.file_name}")
    messages = parser.parse_file(str(file))
    await index_whatsapp_messages(message.from_user.id, messages, file.name)
    await message.answer(f"Import complete. Indexed {len(messages)} messages.")
    await state.clear()

@router.message(Command("find"))
async def cmd_find(message: Message):
    query = sanitize_input(message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "")
    if not query:
        return await message.answer("Usage: <code>/find &lt;query&gt;</code>")
    results = await search_whatsapp_messages(message.from_user.id, query)
    if not results:
        return await message.answer("No matches found.")
    text = "Results:\n" + "\n---\n".join(f"From: {sender}\n{content}" for sender, content, _ in results)
    await message.answer(text)