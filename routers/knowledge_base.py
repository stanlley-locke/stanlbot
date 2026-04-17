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
    tags = validate_tags(message.text.split(",")) if message.text.lower() != "skip" else []
    await save_note(message.from_user.id, data["content"], tags)
    await message.answer("Note saved successfully.")
    await state.clear()

@router.message(Command("notes"))
@router.callback_query(F.data == "menu:notes")
async def cmd_notes(event: Message | CallbackQuery):
    user_id = event.from_user.id
    notes = await get_notes_paginated(user_id, limit=ITEMS_PER_PAGE, offset=0)
    total = len(notes)
    
    text = "<b>Saved Notes</b>\n" + "\n".join(
        f"{idx+1}. {safe_html(content)}\n<i>{created}</i>"
        for idx, (_, content, _, created) in enumerate(notes)
    ) if total > 0 else "No notes found. Use /note to save your first one."
    
    kb = build_pagination_kb("notes", 1, max(1, total // ITEMS_PER_PAGE + 1)) if total > 0 else InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")]])
    
    if total > 0:
        # Add Find shortcut to pagination
        kb.inline_keyboard.insert(0, [InlineKeyboardButton(text="🔍 AI Find", callback_data="notes:find_help")])

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
    else:
        await event.answer(text, reply_markup=kb)

@router.callback_query(F.data == "notes:find_help")
async def cb_find_help(cb: CallbackQuery):
    await cb.answer("Tip: Use /find <query> to search notes & chats semanticly!", show_alert=True)

from services.rag_service import rag_service
from utils.formatters import EMOJI

@router.message(Command("find"))
async def cmd_find(message: Message):
    """Unified search: FTS5 (Local) + ChromaDB (Semantic)."""
    query = sanitize_input(message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "")
    if not query:
        return await message.answer(f"{EMOJI['help']} Usage: <code>/find &lt;query&gt;</code>")

    status_msg = await message.answer(f"🔍 Searching local and semantic memory...")
    
    user_id = message.from_user.id
    local_results = await search_notes_fts(query, user_id, limit=3)
    semantic_results = await rag_service.search_similar(user_id, query, top_k=3)
    
    await status_msg.delete()
    
    if not local_results and not semantic_results:
        return await message.answer(f"❌ No matches found for: <code>{safe_html(query)}</code>")
    
    text = f"🔎 <b>Search Results: {safe_html(query)}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    seen_content = set()
    if local_results:
        text += "<b>📍 Direct Matches (Local)</b>\n"
        for _, content, _, _ in local_results:
            clean_content = content.strip()[:100]
            if clean_content not in seen_content:
                text += f"• {safe_html(content[:200])}...\n\n"
                seen_content.add(clean_content)
    
    if semantic_results:
        text += "<b>🧠 Related Concepts (AI)</b>\n"
        for res in semantic_results:
            clean_content = res['content'].strip()[:100]
            if clean_content not in seen_content:
                text += f"• {safe_html(res['content'][:200])}...\n\n"
                seen_content.add(clean_content)
                
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Back to Notes", callback_data="menu:notes")]
    ])
    await message.answer(text, reply_markup=kb)
