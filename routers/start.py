import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import settings
from utils.formatters import (
    safe_html, build_main_menu_kb, build_settings_kb, 
    format_dashboard, EMOJI
)
from database.queries import (
    get_user_profile, set_user_language, upsert_user,
    get_budget_status, get_assignments
)
from services.rag_service import rag_service

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        f"👋 Welcome to <b>StanlBot Premium</b>\n\n"
        "I am your AI-powered assistant for finance, notes, and productivity.\n"
        "Please select your preferred language:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang:en"),
             InlineKeyboardButton(text="🇰🇪 Kiswahili", callback_data="lang:sw")]
        ])
    )

@router.message(Command("menu"))
@router.callback_query(F.data == "menu:back")
async def cmd_menu(event: Message | CallbackQuery):
    user_id = event.from_user.id
    
    # Fetch dashboard data
    budgets = await get_budget_status(user_id)
    assignments = await get_assignments(user_id, status="pending")
    rag_stats = await rag_service.get_stats(user_id)
    
    # Format Finance snippet
    if not budgets:
        finance_str = "No budgets set. Use /budget to start."
    else:
        # Get highest usage
        top_budget = max(budgets, key=lambda x: x['percent_used'])
        finance_str = f"{top_budget['category'].capitalize()}: {top_budget['percent_used']}% used"

    # Format Academic snippet
    if not assignments:
        academic_str = "All caught up! No pending tasks."
    else:
        academic_str = f"Next: {assignments[0][2]} ({assignments[0][3][:10]})"

    dashboard_text = format_dashboard({
        "finance": finance_str,
        "academic": academic_str,
        "knowledge_count": rag_stats.get("total_documents", 0)
    })

    if isinstance(event, Message):
        await event.answer(dashboard_text, reply_markup=build_main_menu_kb())
    else:
        await event.message.edit_text(dashboard_text, reply_markup=build_main_menu_kb())

@router.callback_query(F.data == "menu:help")
async def cb_help(cb: CallbackQuery):
    text = (
        f"{EMOJI['help']} <b>StanlBot Help Center</b>\n\n"
        "Select a category to see available commands and tips:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Finance", callback_data="help:finance"),
         InlineKeyboardButton(text="🎓 Academic", callback_data="help:academic")],
        [InlineKeyboardButton(text="✍️ Knowledge", callback_data="help:knowledge"),
         InlineKeyboardButton(text="🛠️ DevOps", callback_data="help:devops")],
        [InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")]
    ])
    await cb.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("help:"))
async def cb_help_category(cb: CallbackQuery):
    category = cb.data.split(":")[1]
    
    help_texts = {
        "finance": (
            "💰 <b>Finance Commands</b>\n\n"
            "• /expense &lt;amount&gt; &lt;cat&gt; &lt;desc&gt; - Log expense\n"
            "• /expenses - Monthly summary\n"
            "• /budget &lt;cat&gt; &lt;amount&gt; - Set monthly limit\n\n"
            "<i>💡 Try: 'Spent $15 on lunch' (AI will parse it!)</i>"
        ),
        "academic": (
            "🎓 <b>Academic Commands</b>\n\n"
            "• /assign - Add new assignment\n"
            "• /assignments - View pending tasks\n"
            "• /prioritize - AI-ranked task list"
        ),
        "knowledge": (
            "✍️ <b>Knowledge Base</b>\n\n"
            "• /note &lt;text&gt; - Save a quick note\n"
            "• /find &lt;query&gt; - Search notes/chats\n"
            "• /ask &lt;question&gt; - Query AI + notes\n"
            "• /teach &lt;info&gt; - Feed AI local knowledge"
        ),
        "devops": (
            "🛠️ <b>DevOps & Server</b>\n\n"
            "• /ec2 - Check instance status\n"
            "• /deploy - Trigger CI/CD webhook"
        )
    }
    
    text = help_texts.get(category, "Category info coming soon...")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Back to Help", callback_data="menu:help")]
    ])
    await cb.message.edit_text(text, reply_markup=kb)
