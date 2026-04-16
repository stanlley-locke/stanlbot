import logging
import random
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.queries import increment_points, get_user_points

router = Router()
logger = logging.getLogger(__name__)

TRIVIA_DB = {
    "cloud": [("What is IaaS?", "Infrastructure as a Service"), ("Define VPC?", "Virtual Private Cloud")],
    "python": [("What is GIL?", "Global Interpreter Lock"), ("List vs Tuple?", "Mutable vs Immutable")]
}

class QuizState(StatesGroup):
    waiting_answer = State()

@router.message(Command("trivia"))
async def cmd_trivia(message: Message, state: FSMContext):
    topic = message.text.split(maxsplit=1)[1].lower() if len(message.text.split()) > 1 else "cloud"
    qa = TRIVIA_DB.get(topic, TRIVIA_DB["cloud"])
    q, a = random.choice(qa)
    await state.update_data(answer=a)
    await state.set_state(QuizState.waiting_answer)
    await message.answer(f"Question: {q}\nReply with your answer.")

@router.message(QuizState.waiting_answer)
async def process_quiz(message: Message, state: FSMContext):
    data = await state.get_data()
    user_ans = message.text.strip().lower()
    if data["answer"].lower() in user_ans or user_ans in data["answer"].lower():
        await increment_points(message.from_user.id, 10)
        await message.answer("Correct. +10 points.")
    else:
        await message.answer(f"Incorrect. The answer was: {data['answer']}")
    await state.clear()

@router.message(Command("checkin"))
async def cmd_checkin(message: Message):
    await increment_points(message.from_user.id, 5)
    await message.answer("Daily check-in complete. +5 points.")