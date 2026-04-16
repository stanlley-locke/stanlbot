import logging
import subprocess
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from config import settings
from services.backup_manager import backup_manager

router = Router()
logger = logging.getLogger(__name__)

def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

@router.message(Command("ec2"))
async def cmd_ec2(message: Message):
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    # Replace with actual boto3 call
    await message.answer(f"EC2 Instance ID: {settings.EC2_INSTANCE_ID or 'Not configured'}\nStatus: Running")

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

@router.message(Command("backup"))
async def cmd_backup(message: Message):
    if not _is_admin(message.from_user.id):
        return await message.answer("Admin access required.")
    await message.answer("Creating database snapshot...")
    path = await backup_manager.create_backup()
    await message.answer(f"Backup saved: {path}")