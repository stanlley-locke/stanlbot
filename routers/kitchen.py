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

@router.message(Command("recipe"))
async def cmd_recipe(message: Message):
    recipes = _load_recipes()
    if not recipes: return await message.answer("No recipes configured.")
    r = random.choice(recipes)
    text = (
        f"<b>{safe_html(r['name'])}</b>\n"
        f"<i>Language: {r.get('lang', 'en')}</i>\n\n"
        "<b>Ingredients:</b>\n" + "\n".join(f"- {i}" for i in r["ingredients"]) + "\n\n"
        f"<b>Steps:</b>\n{safe_html(r['steps'])}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add Ingredients to Grocery", callback_data="recipe:add_grocery")],
        [InlineKeyboardButton(text="Next Recipe", callback_data="recipe:random")]
    ])
    await message.answer(text, reply_markup=kb)

@router.message(Command("grocery"))
async def cmd_grocery(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        items = await get_grocery_list(message.from_user.id)
        if not items: return await message.answer("Grocery list is empty.")
        text = "<b>Current List</b>\n" + "\n".join(f"- {qty}x {safe_html(name)}" for name, qty in items)
        return await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Clear List", callback_data="grocery:clear")]
        ]))
    await add_grocery_item(message.from_user.id, args[1].strip())
    await message.answer("Item added.")