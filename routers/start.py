import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import settings
from database.queries import upsert_user, set_user_language, get_user_profile

router = Router()
logger = logging.getLogger(__name__)
LANGUAGES = {"en": "English", "sw": "Swahili", "fr": "French"}

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[k], callback_data=f"lang:{k}")] for k in LANGUAGES
    ])
    await message.answer("Welcome to StanlBot. Select your preferred language to begin.", reply_markup=kb)

@router.callback_query(F.data.startswith("lang:"))
async def cb_set_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split(":")[1]
    await set_user_language(cb.from_user.id, lang)
    await cb.message.edit_text(f"Language set to {LANGUAGES[lang]}. Use /help to view available commands.")
    logger.info(f"User {cb.from_user.id} set language to {lang}")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "Available Commands:\n"
        "/start - Initialize profile\n"
        "/profile - View account status\n"
        "/note - Save a quick note\n"
        "/assign - Track assignments\n"
        "/recipe - Get meal suggestion\n"
        "/find - Search notes and history\n"
        "/ec2 - Server status (admin)\n"
        "/trivia - Start quiz\n"
        "Forward any message to auto-save as a note."
    )
    await message.answer(help_text)

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    profile = await get_user_profile(message.from_user.id)
    if not profile:
        return await message.answer("Profile not found. Use /start first.")
    _, _, _, lang, points, streak, _, _ = profile
    await message.answer(
        f"Profile Summary:\n"
        f"Language: {lang}\n"
        f"Points: {points}\n"
        f"Streak: {streak} days"
    )