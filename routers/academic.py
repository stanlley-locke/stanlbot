import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dateutil import parser as dateparser
from database.queries import add_assignment, get_assignments, update_assignment_status, add_reminder

router = Router()
logger = logging.getLogger(__name__)

class AssignState(StatesGroup):
    title = State()
    deadline = State()

@router.message(Command("assign"))
async def cmd_assign_start(message: Message, state: FSMContext):
    await message.answer("Enter assignment title:")
    await state.set_state(AssignState.title)

@router.message(AssignState.title)
async def assign_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Enter deadline (e.g., Friday 4pm, Nov 15):")
    await state.set_state(AssignState.deadline)

@router.message(AssignState.deadline)
async def assign_deadline(message: Message, state: FSMContext):
    # Prevent commands from being parsed as dates
    if message.text.startswith('/'):
        await message.answer("Please enter a valid date or time, not a command.")
        return

    data = await state.get_data()
    try:
        deadline = dateparser.parse(message.text)
        await add_assignment(message.from_user.id, data["title"], deadline)
        await add_reminder(message.from_user.id, f"Assignment due: {data['title']}", deadline)
        await message.answer("Assignment saved and reminder scheduled.")
        await state.clear()
    except Exception as e:
        await message.answer("Invalid date format. Please try again (e.g., Friday 4pm, Nov 15).")
        logger.warning(f"Date parse error: {e}")

from services.llm_service import llm_service
from utils.formatters import EMOJI

@router.message(Command("assignments"))
@router.callback_query(F.data == "menu:academic")
async def cmd_assignments(event: Message | CallbackQuery):
    user_id = event.from_user.id
    target = event if isinstance(event, Message) else event.message
    
    items = await get_assignments(user_id, status="pending")
    if not items:
        text = f"{EMOJI['success']} No pending assignments!"
        if isinstance(event, CallbackQuery):
            return await event.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Back", callback_data="menu:back")]]))
        return await event.answer(text)
    
    kb = []
    text = f"{EMOJI['academic']} <b>Pending Assignments</b>\n\n"
    for item in items:
        deadline_str = item[3][:10] if isinstance(item[3], str) else item[3].strftime("%Y-%m-%d")
        text += f"• <b>{item[2]}</b>\n  └ ⏰ Due: {deadline_str}\n\n"
        kb.append([InlineKeyboardButton(text=f"✅ Complete: {item[2][:15]}...", callback_data=f"complete:{item[0]}")])
    
    kb.append([InlineKeyboardButton(text="🧠 AI Prioritize", callback_data="academic:prioritize")])
    kb.append([InlineKeyboardButton(text="🧠 AI Breakdown", callback_data="academic:breakdown_help")])
    kb.append([InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")])
    
    if isinstance(event, Message):
        await event.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await event.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(Command("prioritize"))
@router.callback_query(F.data == "academic:prioritize")
async def cmd_prioritize(event: Message | CallbackQuery):
    user_id = event.from_user.id
    target = event if isinstance(event, Message) else event.message
    
    items = await get_assignments(user_id, status="pending")
    if not items:
        return await target.answer("Nothing to prioritize!")

    status_msg = await target.answer(f"{EMOJI['ai']} Analyzing workload...")
    
    # Prepare data for LLM
    task_list = "\n".join([f"- {i[2]} (Due: {i[3]})" for i in items])
    sys_prompt = "You are a study coach. Prioritize these tasks based on urgency and likely effort. Keep it concise."
    
    recommendation = await llm_service.generate_response(
        prompt=f"Prioritize these assignments:\n{task_list}",
        system_instruction=sys_prompt
    )
    
    await status_msg.delete()
    await target.answer(
        f"🧠 <b>AI Study Plan</b>\n\n"
        f"{recommendation}\n\n"
        f"<i>Stay focused! You got this!</i>"
    )

@router.message(Command("breakdown"))
async def cmd_breakdown(message: Message):
    """Breakdown an assignment into manageable steps."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(f"{EMOJI['academic']} Usage: <code>/breakdown Assignment Title</code>")
    
    title = args[1]
    status_msg = await message.answer(f"{EMOJI['ai']} Decomposing task...")
    
    sys_prompt = (
        "You are an expert academic tutor. Breakdown the given assignment title into "
        "exactly 5 actionable, sequence-ordered study steps. Be concise. "
        "Format with numbers 1-5."
    )
    
    breakdown = await llm_service.generate_response(
        prompt=f"Breakdown this assignment: {title}",
        system_instruction=sys_prompt
    )
    
    await status_msg.delete()
    await message.answer(
        f"🧠 <b>Study Plan: {safe_html(title)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{breakdown}\n\n"
        f"<i>Tip: Follow these steps to finish faster!</i>"
    )

from utils.formatters import EMOJI, safe_html

@router.callback_query(F.data == "academic:breakdown_help")
async def cb_breakdown_help(cb: CallbackQuery):
    await cb.answer("Tip: Use /breakdown <topic> for AI study steps!", show_alert=True)

@router.callback_query(F.data.startswith("complete:"))
async def cb_complete(cb: CallbackQuery):
    aid = cb.data.split(":")[1]
    await update_assignment_status(int(aid), "completed")
    await cb.answer("Marked as complete.")
    await cb.message.edit_text("Assignment updated.")