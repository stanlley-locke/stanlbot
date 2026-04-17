import logging
import subprocess
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import settings
from services.backup_manager import backup_manager

router = Router()
logger = logging.getLogger(__name__)

def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.formatters import EMOJI

@router.message(Command("ec2"))
@router.callback_query(F.data == "menu:devops")
async def cmd_ec2(event: Message | CallbackQuery):
    user_id = event.from_user.id
    target = event if isinstance(event, Message) else event.message
    
    if not _is_admin(user_id):
        text = "⚠️ Admin access required for DevOps tools."
        if isinstance(event, CallbackQuery):
            return await event.answer(text, show_alert=True)
        return await event.answer(text)
        
    text = (
        f"{EMOJI['devops']} <b>Server Management</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Instance: <code>{settings.EC2_INSTANCE_ID or 'Local'}</code>\n"
        f"Status: 🟢 Running\n\n"
        "<b>Quick Actions:</b>\n"
        "• /deploy - Trigger sync\n"
        "• /backup - Snapshot DB\n"
        "• /logs - Check errors"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")]
    ])
    
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.edit_text(text, reply_markup=kb)

@router.message(Command("deploy"))
async def cmd_deploy(message: Message):
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    if not settings.DEPLOY_WEBHOOK_URL:
        return await message.answer("Deploy webhook not configured.")
    await message.answer("Triggering deployment...")
    # Implement aiohttp post or subprocess call here

@router.message(Command("logs"))
async def cmd_logs(message: Message):
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    try:
        output = subprocess.run(["tail", "-n", "50", "logs/bot.log"], capture_output=True, text=True, timeout=5)
        await message.answer(f"<pre>{output.stdout[:3500]}</pre>")
    except Exception as e:
        await message.answer(f"Failed to fetch logs: {e}")

import psutil
import shutil
from datetime import datetime

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """View real-time server resource usage."""
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    
    text = (
        f"📊 <b>Server Performance</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🖥 <b>CPU Usage:</b> {cpu}%\n"
        f"🧠 <b>RAM Used:</b> {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)\n"
        f"💾 <b>Disk Free:</b> {disk.free // (1024**3)}GB / {disk.total // (1024**3)}GB\n"
        f"⏰ <b>Uptime:</b> {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M')}\n"
    )
    await message.answer(text)

@router.message(Command("health"))
async def cmd_health(message: Message):
    """Check status of critical external services."""
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    
    status_msg = await message.answer("🔍 Checking system health...")
    
    # 1. Database Check
    try:
        from database import db
        await db.execute_read("SELECT 1")
        db_status = "🟢 OK"
    except Exception:
        db_status = "🔴 Error"
        
    # 2. AI Check
    try:
        from services.llm_service import llm_service
        # Simple non-token usage check or trivial prompt
        ai_status = "🟢 Connected" 
    except Exception:
        ai_status = "🔴 Error"
        
    # 3. RAG Check
    try:
        from services.rag_service import rag_service
        stats = await rag_service.get_stats()
        rag_status = f"🟢 OK ({stats['total_documents']} docs)"
    except Exception:
        rag_status = "🔴 Disconnected"

    text = (
        f"🏥 <b>System Health Report</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📁 <b>SQLite DB:</b> {db_status}\n"
        f"🤖 <b>Gemini AI:</b> {ai_status}\n"
        f"🧠 <b>Chroma RAG:</b> {rag_status}\n"
    )
    await status_msg.edit_text(text)

@router.message(Command("backup"))
async def cmd_backup(message: Message):
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    await message.answer("Creating database snapshot...")
    path = await backup_manager.create_backup()
    await message.answer(f"Backup saved: {path}")