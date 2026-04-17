import logging
import random
import yaml
from pathlib import Path
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from utils.formatters import safe_html
from database.queries import add_grocery_item, get_grocery_list, clear_grocery_list

router = Router()
logger = logging.getLogger(__name__)
RECIPES_PATH = Path("data/recipes.yaml")

def _load_recipes():
    if not RECIPES_PATH.exists(): return []
    with open(RECIPES_PATH, "r") as f: return yaml.safe_load(f) or []

from services.llm_service import llm_service
from utils.formatters import EMOJI

@router.message(Command("recipe"))
async def cmd_recipe(message: Message):
    recipes = _load_recipes()
    if not recipes: return await message.answer(f"{EMOJI['alert']} No local recipes found. Try /suggest for AI ideas!")
    r = random.choice(recipes)
    text = (
        f"{EMOJI['kitchen']} <b>{safe_html(r['name'])}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Ingredients:</b>\n" + "\n".join(f"- {i}" for i in r["ingredients"]) + "\n\n"
        f"<b>Steps:</b>\n{safe_html(r['steps'])}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Add to Grocery", callback_data="kitchen:add_all_ingredients")],
        [InlineKeyboardButton(text="🎲 Another Random", callback_data="kitchen:random")]
    ])
    await message.answer(text, reply_markup=kb)

@router.message(Command("suggest", "chef"))
async def cmd_suggest(message: Message):
    """AI Recipe suggest based on grocery list"""
    items = await get_grocery_list(message.from_user.id)
    if not items:
        return await message.answer(f"{EMOJI['kitchen']} Your grocery list is empty. Add items first!")

    status_msg = await message.answer(f"{EMOJI['ai']} Consulting the AI Chef...")
    
    ingr_list = ", ".join([name for name, _ in items])
    sys_prompt = "You are a professional chef. Suggest a creative recipe based on these ingredients. Keep it simple and practical."
    
    recipe = await llm_service.generate_response(
        prompt=f"What can I cook with: {ingr_list}?",
        system_instruction=sys_prompt
    )
    
    await status_msg.delete()
    await message.answer(
        f"👨‍🍳 <b>AI Chef's Suggestion</b>\n\n"
        f"{recipe}\n\n"
        f"<i>Enjoy your meal!</i>"
    )

@router.message(Command("grocery"))
async def cmd_grocery(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        items = await get_grocery_list(message.from_user.id)
        if not items: return await message.answer(f"{EMOJI['success']} Grocery list is empty!")
        
        text = f"🛒 <b>Grocery List</b>\n━━━━━━━━━━━━━━━━━━\n"
        text += "\n".join(f"• <code>{qty}x</code> {safe_html(name)}" for name, qty in items)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Suggest Recipe", callback_data="kitchen:suggest")],
            [InlineKeyboardButton(text="🧹 Clear List", callback_data="grocery:clear")]
        ])
        return await message.answer(text, reply_markup=kb)
    
    await add_grocery_item(message.from_user.id, args[1].strip())
    await message.answer(f"{EMOJI['success']} Added <b>{args[1]}</b> to list.")