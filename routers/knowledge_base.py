import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.queries import save_note, get_notes_paginated, search_notes_fts
from utils.validators import sanitize_input, validate_tags
from utils.formatters import safe_html, build_pagination_kb

router = Router()
logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 5

class NoteState(StatesGroup):
    content = State()
    tags = State()

@router.message(Command("note", "save"))
async def cmd_note(message: Message, state: FSMContext):
    content = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not content:
        return await message.answer(safe_html("Usage: <code>/note &lt;your note here&gt;</code>"))
    await state.update_data(content=content)
    await message.answer("Add tags (comma separated, or send 'skip'):")
    await state.set_state(NoteState.tags)

@router.message(NoteState.tags)
async def process_note_tags(message: Message, state: FSMContext):
    data = await state.get_data()
    # Pass raw text; validator handles splitting
    tags = validate_tags(message.text) 
    await save_note(message.from_user.id, data["content"], tags)
    await message.answer("Note saved successfully.")
    await state.clear()

@router.message(Command("notes"))
async def cmd_notes(message: Message):
    notes = await get_notes_paginated(message.from_user.id, limit=ITEMS_PER_PAGE, offset=0)
    total = len(notes)
    if total == 0:
        return await message.answer("No notes found. Use /note to save your first one.")
    text = "<b>Saved Notes</b>\n" + "\n".join(
        f"{idx+1}. {safe_html(content)}\n<i>{created}</i>" 
        for idx, (_, content, _, created) in enumerate(notes)
    )
    await message.answer(text, reply_markup=build_pagination_kb("notes", 1, max(1, total // ITEMS_PER_PAGE + 1)))

@router.message(Command("find"))
async def cmd_find(message: Message):
    query = sanitize_input(message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "")
    if not query:
        return await message.answer(safe_html("Usage: <code>/find &lt;query&gt;</code>"))
    results = await search_notes_fts(query, message.from_user.id, limit=5)
    if not results:
        return await message.answer(f"No matches found for: <code>{safe_html(query)}</code>")
    text = "<b>Search Results</b>\n" + "\n---\n".join(
        f"<pre>{safe_html(content)}</pre>" for _, content, _, _ in results
    )
    await message.answer(text)