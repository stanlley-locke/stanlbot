import logging
import random
import yaml
from pathlib import Path
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.queries import add_grocery_item, get_grocery_list, clear_grocery_list

router = Router()
logger = logging.getLogger(__name__)
RECIPES_PATH = Path("data/recipes.yaml")

def _load_recipes():
    if not RECIPES_PATH.exists():
        return []
    with open(RECIPES_PATH, "r") as f:
        return yaml.safe_load(f) or []

@router.message(Command("recipe"))
async def cmd_recipe(message: Message):
    recipes = _load_recipes()
    if not recipes:
        return await message.answer("No recipes configured.")
    r = random.choice(recipes)
    text = f"Recipe: {r['name']}\nLanguage: {r.get('lang', 'en')}\n\nIngredients:\n- " + "\n- ".join(r["ingredients"])
    text += f"\n\nSteps:\n{r['steps']}"
    await message.answer(text)

@router.message(Command("grocery"))
async def cmd_grocery(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        items = await get_grocery_list(message.from_user.id)
        if not items:
            return await message.answer("Grocery list is empty.")
        text = "Current List:\n" + "\n".join(f"- {qty}x {name}" for name, qty in items)
        return await message.answer(text)
    
    item = args[1].strip()
    await add_grocery_item(message.from_user.id, item)
    await message.answer(f"Added {item} to grocery list.")

@router.message(Command("clear_grocery"))
async def cmd_clear_grocery(message: Message):
    await clear_grocery_list(message.from_user.id)
    await message.answer("Grocery list cleared.")