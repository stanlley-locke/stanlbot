"""
Finance router for expense tracking with LLM-powered parsing.
Commands: /expense, /expenses, /budget, /spending
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import settings
from database.queries import (
    add_expense, get_expenses_by_period, get_expense_summary,
    set_budget, get_all_budgets, get_budget_status
)
from services.llm_service import llm_service
router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "menu:finance")
async def cb_finance_menu(cb: CallbackQuery):
    """Show the interactive Finance dashboard."""
    text = (
        f"{EMOJI['finance']} <b>Personal Finance Hub</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome to your AI-powered wallet! I can help you tracking expenses, managing budgets, and analyzing your spending habits.\n\n"
        "<b>Available Features:</b>\n"
        "• 💰 <b>Log Spending</b>: Just type <i>'Spent 20 on groceries'</i>\n"
        "• 📊 <b>Visual Charts</b>: Use /summary_chart\n"
        "• 🧠 <b>AI Review</b>: Use /budget_review\n"
        "• 📉 <b>Budgets</b>: Set monthly limits with /budget"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Back to Menu", callback_data="menu:back")]
    ])
    await cb.message.edit_text(text, reply_markup=kb)
logger = logging.getLogger(__name__)

CATEGORIES = ["food", "transport", "utilities", "entertainment", "shopping", "health", "education", "other"]

class ExpenseState(StatesGroup):
    amount = State()
    category = State()
    description = State()
    date = State()

@router.message(Command("expense", "spend"))
async def cmd_expense(message: Message, state: FSMContext):
    """Add expense manually or via LLM parsing"""
    args = message.text.split(maxsplit=1)

    # If message has content, try LLM parsing first
    if len(args) > 1:
        # Show "Parsing..." only if it's likely an LLM case
        status_msg = await message.answer(f"{EMOJI['ai']} Parsing expense...")
        expense_data = await llm_service.parse_expense(args[1])

        if expense_data:
            await add_expense(
                user_id=message.from_user.id,
                amount=expense_data['amount'],
                category=expense_data['category'],
                description=expense_data['description'],
                expense_date=expense_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            )
            await status_msg.delete()
            return await message.answer(
                f"{EMOJI['success']} <b>Expense Logged!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>Amount:</b> ${expense_data['amount']:.2f}\n"
                f"🏷 <b>Category:</b> {expense_data['category']}\n"
                f"📝 <b>Note:</b> {expense_data['description']}\n"
                f"📅 <b>Date:</b> {expense_data.get('date', 'Today')}"
            )
        await status_msg.delete()

    await message.answer(
        f"{EMOJI['finance']} <b>Add Expense</b>\n\n"
        "Just tell me what you spent! <i>(e.g., '15 on coffee')</i>\n"
        "Or use guided entry by sending the amount:",
        parse_mode="HTML"
    )
    await state.set_state(ExpenseState.amount)

@router.message(Command("expenses", "spending"))
async def cmd_expenses(message: Message):
    """View expenses summary with premium formatting"""
    args = message.text.split()
    period = args[1] if len(args) > 1 else "month"

    now = datetime.now()
    start_date = now.replace(day=1).strftime('%Y-%m-%d') if period == "month" else (now - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')

    expenses = await get_expenses_by_period(message.from_user.id, start_date, end_date)

    if not expenses:
        return await message.answer(f"No expenses recorded this {period}.")

    total = sum(exp[1] for exp in expenses)
    summary = await get_expense_summary(message.from_user.id, now.strftime('%Y-%m'))

    text = f"📊 <b>Spending Report ({period.capitalize()})</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"💵 <b>Total Spent:</b> ${total:.2f}\n\n"
    
    text += "<b>Category Breakdown:</b>\n"
    for cat, amount in sorted(summary.items(), key=lambda x: x[1], reverse=True):
        percent = (amount / total * 100) if total > 0 else 0
        text += f"<code>{cat.capitalize():<12}</code> ${amount:>7.2f} ({percent:>2.0f}%)\n"

    text += f"\n<b>Recent Transactions:</b>\n"
    for _, amount, category, desc, date, _ in expenses[:5]:
        text += f"• <code>{date[5:]}</code> ${amount:.2f} | <i>{desc[:20]}</i>\n"

    await message.answer(text)

@router.message(Command("savings", "goals"))
async def cmd_savings(message: Message):
    """Placeholder for Savings feature"""
    await message.answer(
        f"🎯 <b>Savings Goals</b>\n\n"
        "Track progress towards your big purchases!\n"
        "<i>Coming soon in the next update.</i>"
    )

@router.message(Command("budget"))
async def cmd_budget(message: Message):
    """Set/view budget limits and get alerts"""
    args = message.text.split()

    if len(args) < 2:
        # Show current budgets
        budgets = await get_all_budgets(message.from_user.id)

        if not budgets:
            return await message.answer(
                "Budget Management\n\n"
                "No budgets set yet. Use:\n"
                "/budget food 500 - Set $500 monthly budget for food\n"
                "/budget transport 200 - Set $200 for transport\n\n"
                f"Categories: {', '.join(CATEGORIES)}"
            )

        text = "Your Monthly Budgets\n\n"
        for budget in budgets:
            # budget tuple: (id, user_id, category, amount, period, start_date, created_at, updated_at)
            cat = budget[2]
            limit = budget[3]
            text += f"- {cat.capitalize()}: ${limit:.2f}\n"

        text += "\nUse /budget category amount to modify."
        return await message.answer(text)

    # Set budget: /budget food 500
    if len(args) == 3:
        category = args[1].lower()
        try:
            amount = float(args[2])

            if category not in CATEGORIES:
                return await message.answer(
                    f"Invalid category. Choose from: {', '.join(CATEGORIES)}"
                )

            await set_budget(message.from_user.id, category, amount)

            await message.answer(
                f"Budget set!\n"
                f"{category.capitalize()}: ${amount:.2f}/month\n\n"
                "You will be alerted when approaching this limit!"
            )

        except ValueError:
            await message.answer("Invalid amount. Please enter a number (e.g., 500)")
        return

    await message.answer(
        "Budget Management\n\n"
        "Usage:\n"
        "/budget - View all budgets\n"
        "/budget food 500 - Set monthly budget\n\n"
        f"Categories: {', '.join(CATEGORIES)}"
    )

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiogram.types import BufferedInputFile

@router.message(Command("summary_chart"))
async def cmd_summary_chart(message: Message):
    """Generate a visual spending chart using Pillow."""
    summary = await get_expense_summary(message.from_user.id, datetime.now().strftime('%Y-%m'))
    
    if not summary:
        return await message.answer("No spending recorded this month to create a chart.")

    # Chart Configuration
    width, height = 600, 400
    margin = 50
    bar_gap = 20
    
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.text((width//2 - 50, 10), "Monthly Spending", fill=(0, 0, 0))
    
    # Calculate bar widths
    categories = list(summary.keys())
    values = list(summary.values())
    max_val = max(values)
    
    bar_width = (width - 2*margin - (len(categories)-1)*bar_gap) // len(categories)
    
    for i, (cat, val) in enumerate(summary.items()):
        # Bar height scaled to max
        bar_height = int((val / max_val) * (height - 2*margin))
        x0 = margin + i * (bar_width + bar_gap)
        y0 = height - margin - bar_height
        x1 = x0 + bar_width
        y1 = height - margin
        
        # Draw bar (different colors for variety)
        color = (52, 152, 219) if i % 2 == 0 else (46, 204, 113)
        draw.rectangle([x0, y0, x1, y1], fill=color)
        
        # Label
        label = f"{cat[:8]}"
        draw.text((x0, y1 + 5), label, fill=(0, 0, 0))
        # Value
        draw.text((x0, y0 - 15), f"${int(val)}", fill=(0, 0, 0))

    # Send image as file
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    
    photo = BufferedInputFile(bio.read(), filename="spending_chart.png")
    await message.answer_photo(photo, caption="📸 <b>Your Monthly Spending Chart</b>")

@router.message(Command("budget_review"))
async def cmd_budget_review(message: Message):
    """AI analysis of spending habits."""
    status_msg = await message.answer(f"{EMOJI['ai']} Analyzing habits...")
    
    summary = await get_expense_summary(message.from_user.id, datetime.now().strftime('%Y-%m'))
    if not summary:
        await status_msg.delete()
        return await message.answer("Need more data for analysis. Go spend some money! 😉")

    data_str = "\n".join([f"{k}: ${v}" for k, v in summary.items()])
    
    sys_prompt = (
        "You are a professional financial advisor. Analyze this user's monthly "
        "spending data and provide 3 specific, actionable tips to save money. "
        "Be encouraging but direct."
    )
    
    analysis = await llm_service.generate_response(
        prompt=f"Analyze this spending data:\n{data_str}",
        system_instruction=sys_prompt
    )
    
    await status_msg.delete()
    await message.answer(
        f"💡 <b>AI Financial Review</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{analysis}\n\n"
        f"<i>Disclaimer: This is AI advice, not professional financial planning.</i>"
    )

@router.message(Command("budget_status", "budget_check"))
async def cmd_budget_status(message: Message):
    """Check current spending vs budget"""
    now = datetime.now()
    month_str = now.strftime('%Y-%m')

    status_list = await get_budget_status(message.from_user.id)

    if not status_list:
        return await message.answer(
            "Budget Status\n\n"
            "No budgets configured. Use /budget category amount to set one."
        )

    text = f"Budget Status ({now.strftime('%B %Y')})\n\n"

    alerts = []
    for item in sorted(status_list, key=lambda x: x['percent_used'], reverse=True):
        category = item['category']
        budgeted = item['budgeted']
        spent = item['spent']
        remaining = item['remaining']
        percent = item['percent_used']

        status_icon = "[OVER]" if percent >= 100 else "[WARN]" if percent > 80 else "[OK]"
        text += (
            f"{status_icon} {category.capitalize()}\n"
            f"  Spent: ${spent:.2f} / ${budgeted:.2f}\n"
            f"  {percent:.1f}% used"
        )
        if remaining > 0:
            text += f" (${remaining:.2f} left)\n"
        else:
            text += f" (Over by ${abs(remaining):.2f}!)\n"
            alerts.append(f"You have exceeded your {category} budget!")
        text += "\n"

    if alerts:
        text += "\n" + "\n".join(alerts)

    await message.answer(text)