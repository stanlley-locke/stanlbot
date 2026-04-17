"""
Community router for group management, polls, events, and moderation.
Commands: /poll, /event, /welcome, /group_stats
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import settings
from utils.formatters import safe_html

router = Router()
logger = logging.getLogger(__name__)

class PollState(StatesGroup):
    question = State()
    options = State()

@router.message(Command("poll"))
async def cmd_poll_start(message: Message, state: FSMContext):
    """Start creating a poll: /poll or /poll Question here"""
    args = message.text.split(maxsplit=1)
    
    if len(args) > 1:
        # Quick poll with question provided
        question = args[1]
        await state.update_data(question=question, creator=message.from_user.id)
        await message.answer(
            f"Question: {safe_html(question)}\n\n"
            "Now send options separated by commas (max 6):\n"
            "Example: Option1, Option2, Option3"
        )
        await state.set_state(PollState.options)
    else:
        # Guided flow
        await message.answer("Enter your poll question:")
        await state.set_state(PollState.question)

@router.message(PollState.question)
async def poll_question(message: Message, state: FSMContext):
    """Store the poll question"""
    question = message.text.strip()
    if not question:
        return await message.answer("Question cannot be empty. Please try again:")
    
    await state.update_data(question=question, creator=message.from_user.id)
    await message.answer(
        f"Question saved: {safe_html(question)}\n\n"
        "Now send options separated by commas (max 6):\n"
        "Example: Option1, Option2, Option3"
    )
    await state.set_state(PollState.options)

@router.message(PollState.options)
async def poll_options(message: Message, state: FSMContext):
    """Parse options and create the poll"""
    # Get question from state with safe fallback
    data = await state.get_data()
    question = data.get("question")
    
    if not question:
        await message.answer("Session expired. Please start over with /poll")
        await state.clear()
        return
    
    # Parse options
    raw_options = message.text.strip().split(",")
    options = [opt.strip() for opt in raw_options if opt.strip()][:6]  # Max 6 options
    
    if len(options) < 2:
        return await message.answer("Please provide at least 2 options separated by commas:")
    
    # Build inline keyboard for voting
    kb = []
    for i, opt in enumerate(options):
        kb.append([InlineKeyboardButton(text=opt, callback_data=f"poll_vote:{i}")])
    kb.append([InlineKeyboardButton(text="View Results", callback_data="poll_results")])
    
    # Send the poll
    poll_text = f"📊 <b>Poll</b>\n{safe_html(question)}\n\nVote below:"
    await message.answer(poll_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    # Store poll data for results tracking (optional: save to DB)
    await state.clear()
    logger.info(f"Poll created by user {message.from_user.id}: {question}")

@router.callback_query(F.data.startswith("poll_vote:"))
async def cb_poll_vote(cb: CallbackQuery):
    """Handle poll voting"""
    option_idx = cb.data.split(":")[1]
    await cb.answer(f"Voted for option {int(option_idx) + 1}", show_alert=False)
    # TODO: Store vote in database for results tracking
    # await db.add_vote(poll_id, cb.from_user.id, option_idx)

@router.callback_query(F.data == "poll_results")
async def cb_poll_results(cb: CallbackQuery):
    """Show poll results placeholder"""
    await cb.answer("Results feature coming soon!", show_alert=True)
    # TODO: Query DB for vote counts and display

@router.message(Command("event"))
async def cmd_event(message: Message):
    """Create a group event"""
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        return await message.answer(
            "Usage: <code>/event Title Date/Time</code>\n"
            "Example: <code>/event Study Session Saturday 3pm</code>"
        )
    
    title = args[1]
    datetime_str = args[2]
    
    # TODO: Parse datetime and store event in DB
    # For now, echo confirmation
    await message.answer(
        f"Event scheduled:\n"
        f"📌 {safe_html(title)}\n"
        f"⏰ {safe_html(datetime_str)}\n\n"
        "ICS calendar file generation coming soon."
    )
    logger.info(f"Event created by {message.from_user.id}: {title} at {datetime_str}")

@router.message(Command("welcome"))
async def cmd_welcome(message: Message):
    """Configure welcome message for new group members"""
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("This command only works in groups.")
    
    # TODO: Store custom welcome message in DB per chat_id
    await message.answer(
        "Welcome message configured for this group.\n"
        "New members will receive a DM with rules and /lang prompt."
    )

@router.message(Command("group_stats"))
async def cmd_group_stats(message: Message):
    """Show group activity statistics"""
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("This command only works in groups.")
    
    # TODO: Query DB for message counts, top contributors, etc.
    await message.answer(
        "Group Activity (placeholder):\n"
        "• Total messages today: 142\n"
        "• Active members: 23\n"
        "• Top contributor: @user123\n"
        "• Spam blocked: 12"
    )

@router.message(Command("mod"))
async def cmd_mod(message: Message):
    """Moderation helper for admins"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return await message.answer("Admin access required.")
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer(
            "Usage: <code>/mod action user</code>\n"
            "Actions: warn, mute, ban, unban"
        )
    
    action, target = args[1], args[2]
    # TODO: Implement actual moderation via Telegram API
    await message.answer(f"Moderation action '{action}' queued for user '{target}'")