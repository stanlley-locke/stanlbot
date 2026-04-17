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
    set_budget, get_all_budgets, check_budget_status
)
from services.llm_service import llm_service
from utils.formatters import safe_html

router = Router()
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
    if len(args) > 1 and settings.ENABLE_RAG:
        expense_data = await llm_service.parse_expense(args[1])

        if expense_:
            await add_expense(
                user_id=message.from_user.id,
                amount=expense_data['amount'],
                category=expense_data['category'],
                description=expense_data['description'],
                expense_date=expense_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            )

            return await message.answer(
                f"✅ Expense logged!\n"
                f"💰 Amount: ${expense_data['amount']:.2f}\n"
                f"📂 Category: {expense_data['category']}\n"
                f"📝 {expense_data['description']}"
            )

    # Manual entry flow
    if len(args) > 1:
        # Quick format: /expense 15 food lunch
        parts = args[1].split()
        if len(parts) >= 3:
            try:
                amount = float(parts[0])
                category = parts[1] if parts[1] in CATEGORIES else "other"
                description = " ".join(parts[2:])

                await add_expense(
                    user_id=message.from_user.id,
                    amount=amount,
                    category=category,
                    description=description,
                    expense_date=datetime.now().strftime('%Y-%m-%d')
                )

                return await message.answer(
                    f"✅ Expense logged: ${amount:.2f} - {category} - {description}"
                )
            except ValueError:
                pass

    await message.answer(
        "💰 <b>Add Expense</b>\n\n"
        "Quick format:\n"
        "<code>/expense 15.50 food Lunch at cafe</code>\n\n"
        "Or send just the amount to start guided entry:"
    )
    await state.set_state(ExpenseState.amount)

@router.message(ExpenseState.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            return await message.answer("Please enter a positive amount:")

        await state.update_data(amount=amount)
        await message.answer(
            f"Amount: ${amount:.2f}\n"
            f"Choose category:\n" +
            "\n".join(f"{i+1}. {cat}" for i, cat in enumerate(CATEGORIES))
        )
        await state.set_state(ExpenseState.category)
    except ValueError:
        await message.answer("Invalid amount. Please enter a number:")

@router.message(ExpenseState.category)
async def process_category(message: Message, state: FSMContext):
    try:
        cat_idx = int(message.text.strip()) - 1
        if 0 <= cat_idx < len(CATEGORIES):
            category = CATEGORIES[cat_idx]
        else:
            category = message.text.strip().lower()
            if category not in CATEGORIES:
                category = "other"

        await state.update_data(category=category)
        await message.answer("Enter description (or 'skip'):")
        await state.set_state(ExpenseState.description)
    except ValueError:
        category = message.text.strip().lower()
        if category not in CATEGORIES:
            category = "other"
        await state.update_data(category=category)
        await message.answer("Enter description (or 'skip'):")
        await state.set_state(ExpenseState.description)

@router.message(ExpenseState.description)
async def process_description(message: Message, state: FSMContext):
    description = message.text.strip() if message.text.lower() != "skip" else "No description"
    await state.update_data(description=description)

    await message.answer("Enter date (YYYY-MM-DD) or 'today':")
    await state.set_state(ExpenseState.date)

@router.message(ExpenseState.date)
async def process_date(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.text.lower() == "today":
        expense_date = datetime.now().strftime('%Y-%m-%d')
    else:
        try:
            datetime.strptime(message.text.strip(), '%Y-%m-%d')
            expense_date = message.text.strip()
        except ValueError:
            await message.answer("Invalid date format. Using today:")
            expense_date = datetime.now().strftime('%Y-%m-%d')

    await add_expense(
        user_id=message.from_user.id,
        amount=data['amount'],
        category=data['category'],
        description=data['description'],
        expense_date=expense_date
    )

    await message.answer(
        f"✅ Expense saved!\n"
        f"${data['amount']:.2f} - {data['category']}\n"
        f"{data['description']} ({expense_date})"
    )
    await state.clear()

@router.message(Command("expenses", "spending"))
async def cmd_expenses(message: Message):
    """View expenses summary"""
    args = message.text.split()
    period = args[1] if len(args) > 1 else "month"

    now = datetime.now()
    if period == "week":
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == "month":
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
    else:
        start_date = now.replace(day=1).strftime('%Y-%m-%d')

    end_date = now.strftime('%Y-%m-%d')

    expenses = await get_expenses_by_period(
        user_id=message.from_user.id,
        start_date=start_date,
        end_date=end_date
    )

    if not expenses:
        return await message.answer(f"No expenses recorded this {period}.")

    total = sum(exp[1] for exp in expenses)

    # Get category breakdown
    month_str = now.strftime('%Y-%m')
    summary = await get_expense_summary(message.from_user.id, month_str)

    text = f"📊 <b>Expenses ({period})</b>\n\n"
    text += f"💵 Total: <b>${total:.2f}</b>\n\n"
    text += "<b>By Category:</b>\n"

    for cat, amount in sorted(summary.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total * 100) if total > 0 else 0
        text += f"• {cat.capitalize()}: ${amount:.2f} ({percentage:.1f}%)\n"

    text += f"\nLast 5 transactions:\n"
    for _, amount, category, desc, date, _ in expenses[:5]:
        text += f"  {date}: ${amount:.2f} - {category} ({desc})\n"

    await message.answer(text)

@router.message(Command("budget"))
async def cmd_budget(message: Message):
    """Set/view budget limits and get alerts"""
    args = message.text.split()

    if len(args) < 2:
        # Show current budgets
        budgets = await get_all_budgets(message.from_user.id)

        if not budgets:
            return await message.answer(
                "📋 <b>Budget Management</b>\n\n"
                "No budgets set yet. Use:\n"
                "<code>/budget food 500</code> - Set $500 monthly budget for food\n"
                "<code>/budget transport 200</code> - Set $200 for transport\n\n"
                f"Categories: {', '.join(CATEGORIES)}"
            )

        text = "📊 <b>Your Monthly Budgets</b>\n\n"
        for cat, limit in sorted(budgets.items()):
            text += f"• {cat.capitalize()}: ${limit:.2f}\n"

        text += "\nUse <code>/budget category amount</code> to modify."
        return await message.answer(text)

    # Set budget: /budget food 500
    if len(args) == 3:
        category = args[1].lower()
        try:
            amount = float(args[2])

            if category not in CATEGORIES:
                return await message.answer(
                    f"⚠️ Invalid category. Choose from: {', '.join(CATEGORIES)}"
                )

            success = await set_budget(message.from_user.id, category, amount)

            if success:
                await message.answer(
                    f"✅ Budget set!\n"
                    f"📂 {category.capitalize()}: ${amount:.2f}/month\n\n"
                    "You'll be alerted when approaching this limit!"
                )
            else:
                await message.answer("⚠️ Failed to set budget. Try again.")

        except ValueError:
            await message.answer("⚠️ Invalid amount. Please enter a number (e.g., 500)")
        return

    await message.answer(
        "📋 <b>Budget Management</b>\n\n"
        "Usage:\n"
        "<code>/budget</code> - View all budgets\n"
        "<code>/budget food 500</code> - Set monthly budget\n\n"
        f"Categories: {', '.join(CATEGORIES)}"
    )

@router.message(Command("budget_status", "budget_check"))
async def cmd_budget_status(message: Message):
    """Check current spending vs budget"""
    now = datetime.now()
    month_str = now.strftime('%Y-%m')

    status = await check_budget_status(message.from_user.id, month_str)

    if not status:
        return await message.answer(
            "📊 <b>Budget Status</b>\n\n"
            "No budgets configured. Use <code>/budget category amount</code> to set one."
        )

    text = f"📊 <b>Budget Status ({now.strftime('%B %Y')})</b>\n\n"

    alerts = []
    for category, data in sorted(status.items(), key=lambda x: x[1]['percentage'], reverse=True):
        emoji = "🔴" if data['over_budget'] else "🟡" if data['percentage'] > 80 else "🟢"
        text += (
            f"{emoji} <b>{category.capitalize()}</b>\n"
            f"  Spent: ${data['spent']:.2f} / ${data['budget']:.2f}\n"
            f"  {data['percentage']:.1f}% used"
        )
        if data['remaining'] > 0:
            text += f" (${data['remaining']:.2f} left)\n"
        else:
            text += f" (Over by ${abs(data['remaining']):.2f}!)\n"
            alerts.append(f"⚠️ You've exceeded your {category} budget!")
        text += "\n"

    if alerts:
        text += "\n" + "\n".join(alerts)

    await message.answer(text)

