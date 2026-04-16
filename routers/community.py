import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()
logger = logging.getLogger(__name__)

class PollState(StatesGroup):
    question = State()

@router.message(Command("poll"))
async def cmd_poll_start(message: Message, state: FSMContext):
    await message.answer("Enter poll question:")
    await state.set_state(PollState.question)

@router.message(PollState.question)
async def poll_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer("Enter options separated by commas:")
    await state.set_state(State())

@router.message(F.text.contains(","))
async def poll_options(message: Message, state: FSMContext):
    data = await state.get_data()
    options = [o.strip() for o in message.text.split(",")[:6]]
    kb = [[InlineKeyboardButton(text=o, callback_data=f"poll:{i}")] for i, o in enumerate(options)]
    await message.answer(data["question"], reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("poll:"))
async def cb_poll(cb: CallbackQuery):
    await cb.answer("Vote recorded.")
    # Implement vote tracking in DB