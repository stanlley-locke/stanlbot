"""
AI Chat router with RAG-enhanced conversations.
Provides intelligent responses using Gemini + context from user's notes.
Commands: /ask, /chat, /summarize, /rag-status
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import settings
from services.llm_service import llm_service
from services.rag_service import rag_service
from utils.formatters import safe_html

router = Router()
logger = logging.getLogger(__name__)

# System instructions for different modes
SYSTEM_INSTRUCTIONS = {
    "default": "You are StanlBot, a helpful personal assistant. Be concise, friendly, and practical.",
    "academic": "You are an academic tutor. Explain concepts clearly with examples. Help with studying and assignments.",
    "cooking": "You are a culinary assistant. Provide recipes, cooking tips, and meal planning advice.",
    "productivity": "You are a productivity coach. Help with time management, goal setting, and habit building."
}

from database.queries import search_notes_hybrid
from utils.formatters import EMOJI, format_dashboard

@router.message(Command("ask", "ai"))
async def cmd_ask(message: Message):
    """Ask AI a question with local-first optimization"""
    query_parts = message.text.split(maxsplit=1)

    if len(query_parts) < 2:
        return await message.answer(
            f"{EMOJI['ai']} <b>AI Assistant</b>\n\n"
            "Usage: <code>/ask your question</code>\n\n"
            "<i>I search your local notes first to save tokens!</i>"
        )

    question = query_parts[1]
    user_id = message.from_user.id
    
    # STEP 1: Local-First Search (Saves Gemini Tokens)
    local_results = await search_notes_hybrid(question, user_id, limit=1)
    
    if local_results:
        # If we found a direct match, show it first
        match = local_results[0]
        text = (
            f"🔍 <b>Local Match Found:</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<code>{match['content']}</code>\n\n"
            f"<i>Found in your {match['source']} notes.</i>\n\n"
            f"Do you still want to ask the AI for a deeper analysis?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Yes, Ask AI", callback_data=f"ask_ai:{match['id']}"),
             InlineKeyboardButton(text="❌ No, Thanks", callback_data="close_menu")]
        ])
        return await message.answer(text, reply_markup=kb)

    # STEP 2: Cloud AI (If no local match)
    status_msg = await message.answer(f"{EMOJI['ai']} Consulting Gemini...")

    context = None
    if settings.ENABLE_RAG:
        context = await rag_service.get_context_for_query(user_id, question)

    response = await llm_service.generate_response(
        prompt=question,
        context=context,
        system_instruction=SYSTEM_INSTRUCTIONS["default"]
    )

    await status_msg.delete()
    if response:
        answer = f"🤖 <b>AI Analysis:</b>\n\n{response[:3500]}"
        if context:
            answer += f"\n\n{EMOJI['knowledge']} <i>Enhanced with your notes.</i>"
        await message.answer(answer)
    else:
        await message.answer(f"{EMOJI['alert']} AI limited. Please try again soon.")

@router.message(Command("chat"))
async def cmd_chat(message: Message):
    """Start conversational chat mode"""
    await message.answer(
        "💬 <b>Chat Mode</b>\n\n"
        "Just send me any message and I'll respond conversationally!\n"
        "I can help with:\n"
        "• Answering questions\n"
        "• Brainstorming ideas\n"
        "• Explaining concepts\n"
        "• Casual conversation\n\n"
        "Type anything to start chatting!"
    )

@router.message(Command("summarize"))
async def cmd_summarize(message: Message):
    """Summarize text using AI"""
    text = message.text.split(maxsplit=1)

    if len(text) < 2:
        return await message.answer(
            "📝 <b>Summarize</b>\n\n"
            "Usage: <code>/summarize your text here</code>\n\n"
            "Paste any text and I'll create a concise summary!"
        )

    content = " ".join(text[1:])

    if len(content) < 50:
        return await message.answer("Please provide more text to summarize (at least 50 characters).")

    await message.answer("📖 Summarizing...")

    summary = await llm_service.summarize_text(content, max_length=150)

    if summary:
        await message.answer(
            f"<b>Summary:</b>\n{summary}\n\n"
            f"<i>Original: {len(content)} chars → Summary: {len(summary)} chars</i>"
        )
    else:
        await message.answer("⚠️ Unable to summarize right now. Please try again.")

@router.message(Command("rag_status", "vector_stats"))
async def cmd_rag_status(message: Message):
    """Check RAG/vector store status"""
    if not settings.ENABLE_RAG:
        return await message.answer(
            "📊 <b>RAG Status</b>\n\n"
            "RAG is currently disabled.\n"
            "Enable it by setting ENABLE_RAG=true in your config."
        )

    stats = await rag_service.get_stats(message.from_user.id)

    text = (
        "📊 <b>Vector Store Status</b>\n\n"
        f"Your documents indexed: <b>{stats.get('total_documents', 0)}</b>\n\n"
        "Your saved notes are automatically indexed for semantic search.\n"
        "Use /ask to get AI answers enhanced with your notes!"
    )

    await message.answer(text)

@router.message(Command("teach"))
async def cmd_teach(message: Message):
    """Manually add knowledge to RAG store"""
    content = message.text.split(maxsplit=1)

    if len(content) < 2:
        return await message.answer(
            "📚 <b>Add Knowledge</b>\n\n"
            "Usage: <code>/teach important information to remember</code>\n\n"
            "This adds content to your personal knowledge base for AI-enhanced answers."
        )

    knowledge = " ".join(content[1:])

    if not settings.ENABLE_RAG:
        return await message.answer(
            "⚠️ RAG is disabled. Enable ENABLE_RAG in config to use this feature."
        )

    success = await rag_service.add_document(
        user_id=message.from_user.id,
        content=knowledge,
        metadata={"source": "manual_teach"}
    )

    if success:
        await message.answer(
            "✅ Knowledge added!\n\n"
            f"Content: {knowledge[:100]}...\n\n"
            "This will now be used to enhance AI responses to related questions."
        )
    else:
        await message.answer(
            "⚠️ Failed to add knowledge. RAG may not be properly configured."
        )

@router.message(Command("forget"))
async def cmd_forget(message: Message):
    """Delete all vector data for user (GDPR)"""
    if not settings.ENABLE_RAG:
        return await message.answer("RAG is disabled.")

    # Require confirmation
    args = message.text.split()
    if len(args) < 2 or args[1] != "confirm":
        return await message.answer(
            "⚠️ <b>Delete Knowledge Base</b>\n\n"
            "This will permanently delete all your indexed documents.\n"
            "Type <code>/forget confirm</code> to proceed."
        )

    success = await rag_service.delete_user_documents(message.from_user.id)

    if success:
        await message.answer("✅ All indexed knowledge has been deleted.")
    else:
        await message.answer("⚠️ Failed to delete knowledge base.")

@router.callback_query(F.data.startswith("ask_ai:"))
async def cb_ask_ai_deep(cb: CallbackQuery):
    """Callback to trigger AI analysis if local search wasn't enough"""
    # Extract original question from the message text if possible, 
    # or just use the note content as context for a generic search.
    # For now, let's just trigger a search based on what was being asked.
    
    # In a real scenario, we might want to store the state. 
    # For simplicity, we'll consult the AI using the prompt that triggered this.
    
    # Let's assume the user wants 'Deep Analysis' of the topic.
    question = cb.message.text.split("Found:")[0].strip() # This is a bit fragile
    # Better: just use the query from a state or re-prompt.
    
    await cb.answer("Consulting AI Deep Analysis...")
    status_msg = await cb.message.answer(f"{EMOJI['ai']} Deep Analysis in progress...")
    
    context = await rag_service.get_context_for_query(cb.from_user.id, cb.message.text)
    
    response = await llm_service.generate_response(
        prompt=f"Provide a deep analysis and summary of this topic: {cb.message.text}",
        context=context,
        system_instruction=SYSTEM_INSTRUCTIONS["default"]
    )
    
    await status_msg.delete()
    if response:
        await cb.message.answer(f"🤖 <b>Deep Analysis:</b>\n\n{response[:3500]}")
    else:
        await cb.message.answer(f"{EMOJI['alert']} Deep Analysis failed.")

