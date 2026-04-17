from html import escape
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def safe_html(text: str) -> str:
    """Escapes HTML but preserves Telegram-supported tags."""
    text = escape(text, quote=False)
    for tag in ['b', 'i', 'code', 'pre', 'u', 's', 'a']:
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return text

def truncate_message(text: str, max_length: int = 4000) -> str:
    """Truncate message to fit Telegram limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def build_pagination_kb(prefix: str, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = []
    row = []
    if current_page > 1:
        row.append(InlineKeyboardButton(text="Prev", callback_data=f"{prefix}_page:{current_page-1}"))
    row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        row.append(InlineKeyboardButton(text="Next", callback_data=f"{prefix}_page:{current_page+1}"))
    kb.append(row)
    kb.append([InlineKeyboardButton(text="Close Menu", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def build_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Academic", callback_data="menu:academic"),
         InlineKeyboardButton(text="Kitchen", callback_data="menu:kitchen")],
        [InlineKeyboardButton(text="Notes", callback_data="menu:notes"),
         InlineKeyboardButton(text="DevOps", callback_data="menu:devops")],
        [InlineKeyboardButton(text="Settings", callback_data="menu:settings"),
         InlineKeyboardButton(text="Help", callback_data="menu:help")],
        [InlineKeyboardButton(text="Send Feedback", callback_data="menu:feedback")]
    ])

def build_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Language", callback_data="settings:lang"),
         InlineKeyboardButton(text="Notifications", callback_data="settings:notify")],
        [InlineKeyboardButton(text="Export Data", callback_data="settings:export"),
         InlineKeyboardButton(text="Delete Data", callback_data="settings:delete")],
        [InlineKeyboardButton(text="Back to Menu", callback_data="menu:back")]
    ])