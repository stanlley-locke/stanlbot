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

from services.llm_service import llm_service
from utils.formatters import EMOJI

class QuizState(StatesGroup):
    waiting_answer = State()

@router.message(Command("trivia"))
async def cmd_trivia(message: Message, state: FSMContext):
    """Start a Gemini-powered trivia quiz."""
    args = message.text.split(maxsplit=1)
    topic = args[1] if len(args) > 1 else "General Knowledge"
    
    status_msg = await message.answer(f"{EMOJI['ai']} Generating challenge for '{topic}'...")
    
    sys_prompt = (
        "You are a quiz master. Generate exactly one challenging trivia question "
        "and its short answer. Return them in JSON format: "
        "{\"question\": \"...\", \"answer\": \"...\"}. "
        "Keep the answer very short (max 5 words)."
    )
    
    try:
        response = await llm_service.generate_response(
            prompt=f"Topic: {topic}",
            system_instruction=sys_prompt
        )
        # Handle potential markdown formatting from LLM
        clean_json = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        await status_msg.delete()
        await state.update_data(answer=data["answer"])
        await state.set_state(QuizState.waiting_answer)
        await message.answer(
            f"🎯 <b>Trivia: {topic}</b>\n\n"
            f"Question: <i>{data['question']}</i>\n\n"
            f"Reply with your answer!"
        )
    except Exception as e:
        logger.error(f"Trivia error: {e}")
        await status_msg.edit_text("Failed to generate trivia. Using fallback...")
        await state.update_data(answer="Python")
        await state.set_state(QuizState.waiting_answer)
        await message.answer("Fallback Question: What is the best programming language for AI?\nReply with your answer.")

@router.message(QuizState.waiting_answer)
async def process_quiz(message: Message, state: FSMContext):
    data = await state.get_data()
    user_ans = message.text.strip().lower()
    correct_ans = data["answer"].lower()
    
    # Simple fuzzy match
    if correct_ans in user_ans or user_ans in correct_ans:
        await increment_points(message.from_user.id, 10)
        await message.answer(f"{EMOJI['success']} <b>Correct!</b>\nYou earned +10 points.")
    else:
        await message.answer(f"❌ <b>Incorrect.</b>\nThe correct answer was: <code>{data['answer']}</code>")
    await state.clear()

@router.message(Command("checkin"))
async def cmd_checkin(message: Message):
    await increment_points(message.from_user.id, 5)
    await message.answer(f"{EMOJI['success']} Daily check-in complete. +5 points.")