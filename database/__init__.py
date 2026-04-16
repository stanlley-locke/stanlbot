from .connection import db
from .models import init_database
from .queries import (
    upsert_user, get_user_profile, set_user_language,
    save_note, get_notes_paginated, search_notes_fts,
    add_assignment, get_assignments, update_assignment_status,
    add_reminder, get_due_reminders, mark_reminder_sent,
    index_whatsapp_messages, search_whatsapp_messages,
    add_grocery_item, get_grocery_list, clear_grocery_list,
    get_user_stats, increment_points, get_user_points
)

__all__ = [
    "db", "init_database", "upsert_user", "get_user_profile", "set_user_language",
    "save_note", "get_notes_paginated", "search_notes_fts",
    "add_assignment", "get_assignments", "update_assignment_status",
    "add_reminder", "get_due_reminders", "mark_reminder_sent",
    "index_whatsapp_messages", "search_whatsapp_messages",
    "add_grocery_item", "get_grocery_list", "clear_grocery_list",
    "get_user_stats", "increment_points", "get_user_points"
]