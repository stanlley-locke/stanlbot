import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import settings
from utils.formatters import safe_html, build_main_menu_kb, build_settings_kb
from database.queries import get_user_profile, set_user_language, upsert_user

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "Welcome to StanlBot. Select your preferred language:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="English", callback_data="lang:en"),
             InlineKeyboardButton(text="Kiswahili", callback_data="lang:sw")]
        ])
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Main Dashboard", reply_markup=build_main_menu_kb())

@router.callback_query(F.data == "menu:help")
async def cb_help(cb: CallbackQuery):
    text = (
        "<b>Quick Guide</b>\n\n"
        "Commands:\n"
        "/start - Initialize profile\n"
        "/menu - Open dashboard\n"
        "/note - Save note\n"
        "/notes - Browse notes\n"
        "/find - Search data\n"
        "/assign - Track tasks\n"
        "/recipe - Meal ideas\n"
        "/settings - Preferences\n\n"
        "Use inline buttons for quick navigation."
    )
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back to Menu", callback_data="menu:back")]
    ]))

@router.callback_query(F.data.startswith("lang:"))
async def cb_set_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await set_user_language(cb.from_user.id, lang)
    await cb.answer(f"Language set to {lang}")
    await cb.message.edit_text("Language updated. Use /menu to continue.", reply_markup=build_main_menu_kb())

@router.callback_query(F.data == "menu:settings")
async def cb_settings(cb: CallbackQuery):
    await cb.message.edit_text("Settings & Data Control", reply_markup=build_settings_kb())

@router.callback_query(F.data == "settings:export")
async def cb_export(cb: CallbackQuery):
    await cb.answer("Preparing export...")
    # TODO: Generate JSON/CSV from DB
    await cb.message.answer("Data export feature coming soon. Use /feedback to request priority.")

@router.callback_query(F.data == "settings:delete")
async def cb_delete(cb: CallbackQuery):
    await cb.message.edit_text(
        "Data deletion will remove all your notes, assignments, and preferences.\n"
        "Reply with <code>CONFIRM DELETE</code> to proceed.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data="menu:settings")]
        ])
    )

@router.message(F.text == "CONFIRM DELETE")
async def process_delete(message: Message):
    # TODO: Implement actual DB deletion
    await message.answer("Data deletion request received. Processing...")

@router.callback_query(F.data == "close_menu")
async def cb_close(cb: CallbackQuery):
    await cb.message.delete()
