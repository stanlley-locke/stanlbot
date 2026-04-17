from datetime import datetime
from html import escape
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Standard thematic emojis
EMOJI = {
    "finance": "💰",
    "academic": "🎓",
    "notes": "✍️",
    "kitchen": "🍳",
    "devops": "🛠️",
    "settings": "⚙️",
    "help": "❓",
    "ai": "🤖",
    "alert": "⚠️",
    "success": "✅",
    "time": "⏰",
    "stats": "📊"
}

def safe_html(text: str) -> str:
    """Escapes HTML but preserves Telegram-supported tags."""
    if not text: return ""
    text = escape(text, quote=False)
    for tag in ['b', 'i', 'code', 'pre', 'u', 's', 'a']:
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return text

def truncate_message(text: str, max_len: int = 4000) -> str:
    """Truncates messages to Telegram's 4096 character limit safely."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 40] + "\n\n[Message truncated due to length limits]"

def format_dashboard(data: dict) -> str:
    """Creates a premium 'Daily Briefing' dashboard text."""
    now = datetime.now().strftime("%A, %b %d")
    
    # Financial progress (simplified)
    finance_status = data.get("finance", "No budget set")
    
    # Academic status (nearest deadline)
    academic_status = data.get("academic", "No pending tasks")
    
    # Knowledge stats
    knowledge_count = data.get("knowledge_count", 0)

    text = (
        f"✨ <b>StanlBot Premium</b> | {now}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['finance']} <b>Finance</b>\n"
        f"└ {finance_status}\n\n"
        f"{EMOJI['academic']} <b>Academic</b>\n"
        f"└ {academic_status}\n\n"
        f"{EMOJI['notes']} <b>Knowledge</b>\n"
        f"└ {knowledge_count} items in local memory\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>How can I assist you today?</i>"
    )
    return text

def build_pagination_kb(prefix: str, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = []
    row = []
    if current_page > 1:
        row.append(InlineKeyboardButton(text="« Prev", callback_data=f"{prefix}_page:{current_page-1}"))
    row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        row.append(InlineKeyboardButton(text="Next »", callback_data=f"{prefix}_page:{current_page+1}"))
    kb.append(row)
    kb.append([InlineKeyboardButton(text="Close", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def build_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['academic']} Academic", callback_data="menu:academic"),
         InlineKeyboardButton(text=f"{EMOJI['kitchen']} Kitchen", callback_data="menu:kitchen")],
        [InlineKeyboardButton(text=f"{EMOJI['notes']} Notes", callback_data="menu:notes"),
         InlineKeyboardButton(text=f"{EMOJI['devops']} DevOps", callback_data="menu:devops")],
        [InlineKeyboardButton(text=f"{EMOJI['settings']} Settings", callback_data="menu:settings"),
         InlineKeyboardButton(text=f"{EMOJI['help']} Help", callback_data="menu:help")],
        [InlineKeyboardButton(text="💬 Ask AI Anything", callback_data="menu:ai_chat")]
    ])

def build_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Language", callback_data="settings:lang"),
         InlineKeyboardButton(text="Notifications", callback_data="settings:notify")],
        [InlineKeyboardButton(text="Export JSON", callback_data="settings:export"),
         InlineKeyboardButton(text="🚨 Delete All", callback_data="settings:delete")],
        [InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")]
    ])