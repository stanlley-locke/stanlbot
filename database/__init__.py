from .connection import db
from .models import init_database
from .queries import (
    # User
    upsert_user, get_user_profile, set_user_language,
    # Notes
    save_note, get_notes_paginated, search_notes_fts,
    # Assignments
    add_assignment, get_assignments, update_assignment_status,
    # Reminders
    add_reminder, get_due_reminders, mark_reminder_sent,
    # WhatsApp
    index_whatsapp_messages, search_whatsapp_messages,
    # Grocery
    add_grocery_item, get_grocery_list, clear_grocery_list,
    # Gamification
    get_user_stats, increment_points, get_user_points,
    # Expenses
    add_expense, get_expenses_by_period, get_expense_summary,
    # Habits
    create_habit, get_user_habits, log_habit_completion, 
    reset_habit_streak, get_habit_stats,
    # Budgets (NEW)
    set_budget, get_budget, get_all_budgets, get_budget_status,
    update_budget, delete_budget, get_budget_alerts
)

__all__ = [
    "db", "init_database",
    "upsert_user", "get_user_profile", "set_user_language",
    "save_note", "get_notes_paginated", "search_notes_fts",
    "add_assignment", "get_assignments", "update_assignment_status",
    "add_reminder", "get_due_reminders", "mark_reminder_sent",
    "index_whatsapp_messages", "search_whatsapp_messages",
    "add_grocery_item", "get_grocery_list", "clear_grocery_list",
    "get_user_stats", "increment_points", "get_user_points",
    "add_expense", "get_expenses_by_period", "get_expense_summary",
    "create_habit", "get_user_habits", "log_habit_completion",
    "reset_habit_streak", "get_habit_stats",
    "set_budget", "get_budget", "get_all_budgets", "get_budget_status",
    "update_budget", "delete_budget", "get_budget_alerts"
]