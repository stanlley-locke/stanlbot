import json
import logging
from datetime import datetime
from database.connection import db
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)

async def upsert_user(user_id: int, username: Optional[str], first_name: str):
    await db.execute_write(
        "INSERT INTO users (id, username, first_name) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET username=?, first_name=?, last_active=CURRENT_TIMESTAMP",
        (user_id, username, first_name, username, first_name)
    )

async def get_user_profile(user_id: int) -> Optional[Tuple]:
    cursor = await db.execute_read("SELECT * FROM users WHERE id = ?", (user_id,))
    return await cursor.fetchone()

async def set_user_language(user_id: int, lang: str):
    await db.execute_write("UPDATE users SET language = ? WHERE id = ?", (lang, user_id))

async def save_note(user_id: int, content: str, tags: List[str] = None, source: str = "manual"):
    await db.execute_write(
        "INSERT INTO notes (user_id, content, tags, source) VALUES (?, ?, ?, ?)",
        (user_id, content, json.dumps(tags or []), source)
    )
    # Sync to FTS table
    cursor = await db.execute_read("SELECT last_insert_rowid()")
    row = await cursor.fetchone()  # Await the async fetchone
    if row:
        note_id = row[0]
        await db.execute_write(
            "INSERT INTO notes_fts (id, content) VALUES (?, ?)",
            (note_id, content)
        )

async def get_notes_paginated(user_id: int, offset: int = 0, limit: int = 10) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT id, content, tags, created_at FROM notes WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )
    return await cursor.fetchall()

async def search_notes_fts(query: str, user_id: int, limit: int = 10) -> List[Tuple]:
    cursor = await db.execute_read(
        """SELECT n.id, n.content, n.tags, n.created_at 
           FROM notes n 
           JOIN notes_fts_idx f ON n.id = f.rowid 
           WHERE notes_fts_idx MATCH ? AND n.user_id = ?
           ORDER BY rank LIMIT ?""",
        (query, user_id, limit)
    )
    return await cursor.fetchall()

async def add_assignment(user_id: int, title: str, deadline: datetime):
    await db.execute_write(
        "INSERT INTO assignments (user_id, title, deadline) VALUES (?, ?, ?)",
        (user_id, title, deadline)
    )

async def get_assignments(user_id: int, status: str = None) -> List[Tuple]:
    if status:
        cursor = await db.execute_read(
            "SELECT * FROM assignments WHERE user_id=? AND status=? ORDER BY deadline",
            (user_id, status)
        )
    else:
        cursor = await db.execute_read(
            "SELECT * FROM assignments WHERE user_id=? ORDER BY deadline",
            (user_id,)
        )
    return await cursor.fetchall()

async def update_assignment_status(assignment_id: int, status: str):
    await db.execute_write("UPDATE assignments SET status = ? WHERE id = ?", (status, assignment_id))

async def add_reminder(user_id: int, message: str, trigger_time: datetime):
    await db.execute_write(
        "INSERT INTO reminders (user_id, message, trigger_time) VALUES (?, ?, ?)",
        (user_id, message, trigger_time)
    )

async def get_due_reminders(current_time: datetime) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT id, user_id, message FROM reminders WHERE trigger_time <= ? AND sent = 0",
        (current_time,)
    )
    return await cursor.fetchall()

async def mark_reminder_sent(reminder_id: int):
    await db.execute_write("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))

async def index_whatsapp_messages(user_id: int, messages: List[dict], file_path: str):
    values = [(user_id, m["sender"], m["content"], m.get("timestamp"), file_path) for m in messages]
    await db.execute_write(
        "INSERT INTO whatsapp_messages (user_id, sender, content, timestamp, file_path) VALUES (?, ?, ?, ?, ?)",
        values
    )

async def search_whatsapp_messages(user_id: int, query: str, limit: int = 5) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT sender, content, timestamp FROM whatsapp_messages WHERE user_id=? AND content LIKE ? LIMIT ?",
        (user_id, f"%{query}%", limit)
    )
    return await cursor.fetchall()

async def add_grocery_item(user_id: int, item: str, quantity: int = 1):
    await db.execute_write(
        "INSERT INTO grocery_items (user_id, item, quantity) VALUES (?, ?, ?) "
        "ON CONFLICT DO UPDATE SET quantity = quantity + ?",
        (user_id, item, quantity, quantity)
    )

async def get_grocery_list(user_id: int) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT item, quantity FROM grocery_items WHERE user_id=? AND completed=0 ORDER BY item",
        (user_id,)
    )
    return await cursor.fetchall()

async def clear_grocery_list(user_id: int):
    await db.execute_write("DELETE FROM grocery_items WHERE user_id=?", (user_id,))

async def get_user_stats(user_id: int) -> dict:
    cursor = await db.execute_read(
        "SELECT COUNT(*) FROM notes WHERE user_id=?", (user_id,)
    )
    notes_count = (await cursor.fetchone())[0]
    
    cursor = await db.execute_read(
        "SELECT COUNT(*) FROM assignments WHERE user_id=? AND status='completed'", (user_id,)
    )
    completed = (await cursor.fetchone())[0]
    
    return {"notes": notes_count, "completed_assignments": completed}

async def increment_points(user_id: int, amount: int = 1):
    await db.execute_write("UPDATE users SET points = points + ? WHERE id = ?", (amount, user_id))

async def get_user_points(user_id: int) -> int:
    cursor = await db.execute_read("SELECT points FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return row[0] if row else 0

# Expense tracking queries
async def add_expense(
    user_id: int, 
    amount: float, 
    category: str, 
    description: str, 
    expense_date: str
):
    await db.execute_write(
        "INSERT INTO expenses (user_id, amount, category, description, expense_date) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, description, expense_date)
    )

async def get_expenses_by_period(
    user_id: int, 
    start_date: str, 
    end_date: str,
    category: Optional[str] = None
) -> List[Tuple]:
    if category:
        cursor = await db.execute_read(
            """SELECT id, amount, category, description, expense_date, created_at 
               FROM expenses 
               WHERE user_id=? AND expense_date BETWEEN ? AND ? AND category=?
               ORDER BY expense_date DESC""",
            (user_id, start_date, end_date, category)
        )
    else:
        cursor = await db.execute_read(
            """SELECT id, amount, category, description, expense_date, created_at 
               FROM expenses 
               WHERE user_id=? AND expense_date BETWEEN ? AND ?
               ORDER BY expense_date DESC""",
            (user_id, start_date, end_date)
        )
    return await cursor.fetchall()

async def get_expense_summary(user_id: int, month: str) -> Dict[str, float]:
    """Get total expenses by category for a given month (YYYY-MM)"""
    cursor = await db.execute_read(
        """SELECT category, SUM(amount) as total
           FROM expenses
           WHERE user_id=? AND strftime('%Y-%m', expense_date) = ?
           GROUP BY category""",
        (user_id, month)
    )
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}

# Habit tracking queries
async def create_habit(user_id: int, name: str, frequency: str = "daily") -> int:
    cursor = await db.execute_write(
        "INSERT INTO habits (user_id, name, frequency) VALUES (?, ?, ?)",
        (user_id, name, frequency)
    )
    # Get the last inserted ID
    result = await db.execute_read("SELECT last_insert_rowid()")
    row = await result.fetchone()
    return row[0] if row else 0

async def get_user_habits(user_id: int) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT * FROM habits WHERE user_id=? ORDER BY created_at",
        (user_id,)
    )
    return await cursor.fetchall()

async def log_habit_completion(habit_id: int, completed_date: str):
    # Check if already logged today
    existing = await db.execute_read(
        "SELECT id FROM habit_logs WHERE habit_id=? AND completed_date=?",
        (habit_id, completed_date)
    )
    if await existing.fetchone():
        return False
    
    await db.execute_write(
        "INSERT INTO habit_logs (habit_id, completed_date) VALUES (?, ?)",
        (habit_id, completed_date)
    )
    
    # Update streak
    await db.execute_write(
        """UPDATE habits 
           SET streak = streak + 1, last_completed = ?
           WHERE id = ?""",
        (completed_date, habit_id)
    )
    return True

async def reset_habit_streak(habit_id: int):
    await db.execute_write(
        "UPDATE habits SET streak = 0 WHERE id = ?",
        (habit_id,)
    )

async def get_habit_stats(habit_id: int) -> Dict:
    cursor = await db.execute_read(
        "SELECT COUNT(*) FROM habit_logs WHERE habit_id=?",
        (habit_id,)
    )
    total_completions = (await cursor.fetchone())[0]
    
    cursor = await db.execute_read(
        "SELECT streak FROM habits WHERE id=?",
        (habit_id,)
    )
    current_streak = (await cursor.fetchone())[0]
    
    return {"total_completions": total_completions, "current_streak": current_streak}