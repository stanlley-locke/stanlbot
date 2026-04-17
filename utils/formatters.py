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
    "stats": "📊",
    "knowledge": "🧠"
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
    now = datetime.now().strftime("%A, %B %d")
    
    finance_status = data.get("finance", "No trends yet")
    academic_status = data.get("academic", "All clear!")
    knowledge_count = data.get("knowledge_count", 0)

    text = (
        f"💎 <b>StanlBot Premium</b>\n"
        f"📅 {now}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['finance']} <b>Finance Trend</b>\n"
        f"└ {finance_status}\n\n"
        f"{EMOJI['academic']} <b>Next Deadline</b>\n"
        f"└ {academic_status}\n\n"
        f"{EMOJI['notes']} <b>Local Knowledge</b>\n"
        f"└ {knowledge_count} items indexed\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Select a module below to begin:</i>"
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

def build_main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    # Build standard rows
    rows = [
        [InlineKeyboardButton(text=f"{EMOJI['academic']} Academic", callback_data="menu:academic"),
         InlineKeyboardButton(text=f"{EMOJI['kitchen']} Kitchen", callback_data="menu:kitchen")],
        [InlineKeyboardButton(text=f"{EMOJI['notes']} Notes", callback_data="menu:notes")]
    ]
    
    # Add DevOps only for admins - shared row with Notes for space efficiency
    if is_admin:
        rows[1].append(InlineKeyboardButton(text=f"{EMOJI['devops']} DevOps", callback_data="menu:devops"))
    
    # Add bottom rows
    rows.append([InlineKeyboardButton(text=f"{EMOJI['settings']} Settings", callback_data="menu:settings"),
                InlineKeyboardButton(text=f"{EMOJI['help']} Help", callback_data="menu:help")])
    rows.append([InlineKeyboardButton(text="💬 Ask AI Anything", callback_data="menu:ai_chat")])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Language", callback_data="settings:lang"),
         InlineKeyboardButton(text="Notifications", callback_data="settings:notify")],
        [InlineKeyboardButton(text="Export JSON", callback_data="settings:export"),
         InlineKeyboardButton(text="🚨 Delete All", callback_data="settings:delete")],
        [InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")]
    ])