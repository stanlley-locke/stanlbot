import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.queries import save_note, get_notes_paginated, search_notes_fts
from utils.validators import sanitize_input, validate_tags

router = Router()
logger = logging.getLogger(__name__)

class NoteState(StatesGroup):
    content = State()
    tags = State()

@router.message(Command("note", "save"))
async def cmd_note(message: Message, state: FSMContext):
    content = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not content:
        return await message.answer("Usage: /note <content>")
    await state.update_data(content=content)
    await message.answer("Add tags (comma separated, or send 'skip'):")
    await state.set_state(NoteState.tags)

@router.message(NoteState.tags)
async def process_note_tags(message: Message, state: FSMContext):
    data = await state.get_data()
    tags = validate_tags(message.text.split(",")) if message.text.lower() != "skip" else []
    await save_note(message.from_user.id, data["content"], tags)
    await message.answer("Note saved successfully.")
    await state.clear()

@router.message(Command("notes"))
async def cmd_notes(message: Message):
    notes = await get_notes_paginated(message.from_user.id, limit=5)
    if not notes:
        return await message.answer("No notes found.")
    text = "Recent Notes:\n" + "\n---\n".join(f"[{created}] {content}" for _, content, _, created in notes)
    await message.answer(text)

@router.message(Command("find"))
async def cmd_find(message: Message):
    query = sanitize_input(message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "")
    if not query:
        return await message.answer("Usage: /find <query>")
    results = await search_notes_fts(query, message.from_user.id)
    if not results:
        return await message.answer("No matches found.")
    text = "Search Results:\n" + "\n---\n".join(f"[{created}] {content}" for _, content, _, created in results)
    await message.answer(text)