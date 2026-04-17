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

@router.message(Command("ask", "ai"))
async def cmd_ask(message: Message):
    """Ask AI a question with optional RAG context"""
    query = message.text.split(maxsplit=1)
    
    if len(query) < 2:
        return await message.answer(
            "🤖 <b>AI Assistant</b>\n\n"
            "Usage: <code>/ask your question</code>\n\n"
            "Examples:\n"
            "• <code>/ask What is quantum computing?</code>\n"
            "• <code>/ask How do I make pasta?</code>\n\n"
            "If you have saved notes, I'll use them to provide contextual answers!"
        )
    
    question = " ".join(query[1:])
    await message.answer("🤔 Thinking...")
    
    # Get RAG context if enabled
    context = None
    if settings.ENABLE_RAG:
        context = await rag_service.get_context_for_query(message.from_user.id, question)
    
    # Generate response
    response = await llm_service.generate_response(
        prompt=question,
        context=context,
        system_instruction=SYSTEM_INSTRUCTIONS["default"]
    )
    
    if response:
        answer = response[:4000]  # Telegram limit
        
        if context:
            answer += "\n\n<i>(Answer enhanced with your saved notes)</i>"
        
        await message.answer(answer, parse_mode="HTML")
    else:
        await message.answer(
            "⚠️ Sorry, I couldn't generate a response right now.\n"
            "This could be due to API rate limits. Please try again in a minute."
        )

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

# Handle general chat messages when in chat mode (optional - can be enabled later)
# @router.message(F.text)
# async def handle_chat(message: Message):
#     # Only respond if user explicitly invoked chat mode recently
#     # This prevents the bot from responding to every message
#     pass
