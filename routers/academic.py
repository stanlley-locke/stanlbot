import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    data = await state.get_data()
    try:
        deadline = dateparser.parse(message.text)
        await add_assignment(message.from_user.id, data["title"], deadline)
        await add_reminder(message.from_user.id, f"Assignment due: {data['title']}", deadline)
        await message.answer("Assignment saved and reminder scheduled.")
    except Exception as e:
        await message.answer("Invalid date format. Please try again.")
        logger.error(f"Date parse error: {e}")
    await state.clear()

@router.message(Command("assignments"))
async def cmd_assignments(message: Message):
    items = await get_assignments(message.from_user.id, status="pending")
    if not items:
        return await message.answer("No pending assignments.")
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(text=f"[ ] {item[2]}", callback_data=f"complete:{item[0]}")])
    await message.answer("Pending Assignments:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("complete:"))
async def cb_complete(cb: CallbackQuery):
    aid = cb.data.split(":")[1]
    await update_assignment_status(int(aid), "completed")
    await cb.answer("Marked as complete.")
    await cb.message.edit_text("Assignment updated.")