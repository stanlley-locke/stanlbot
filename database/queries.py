import json
import logging
from datetime import datetime
from database.connection import db
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)

# ==================== USER MANAGEMENT ====================
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

# ==================== NOTES ====================
async def save_note(user_id: int, content: str, tags: List[str] = None, source: str = "manual"):
    """Saves a note and indexes it for search."""
    cursor = await db.execute_write(
        "INSERT INTO notes (user_id, content, tags, source) VALUES (?, ?, ?, ?) RETURNING id",
        (user_id, content, json.dumps(tags or []), source)
    )
    row = await cursor.fetchone()
    if row:
        note_id = row[0]
        await db.execute_write(
            "INSERT OR REPLACE INTO notes_fts (id, content) VALUES (?, ?)",
            (note_id, content)
        )

async def get_notes_paginated(user_id: int, offset: int = 0, limit: int = 10) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT id, content, tags, created_at FROM notes WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )
    return await cursor.fetchall()

async def search_notes_fts(query: str, user_id: int, limit: int = 10) -> List[Tuple]:
    # Use standard FTS5 column MATCH syntax with bound parameter
    cursor = await db.execute_read(
        """SELECT n.id, n.content, n.tags, n.created_at 
           FROM notes n 
           JOIN notes_fts f ON n.id = f.id 
           WHERE notes_fts MATCH ? AND n.user_id = ?
           ORDER BY rank LIMIT ?""",
        (query, user_id, limit)
    )
    return await cursor.fetchall()

# ==================== ASSIGNMENTS ====================
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

# ==================== REMINDERS ====================
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

# ==================== WHATSAPP INDEX ====================
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

# ==================== GROCERY ====================
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

# ==================== GAMIFICATION ====================
async def get_user_stats(user_id: int) -> dict:
    cursor = await db.execute_read("SELECT COUNT(*) FROM notes WHERE user_id=?", (user_id,))
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

# ==================== EXPENSE TRACKING ====================
async def add_expense(user_id: int, amount: float, category: str, description: str, expense_date: str):
    await db.execute_write(
        "INSERT INTO expenses (user_id, amount, category, description, expense_date) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, description, expense_date)
    )

async def get_expenses_by_period(user_id: int, start_date: str, end_date: str, category: Optional[str] = None) -> List[Tuple]:
    if category:
        cursor = await db.execute_read(
            """SELECT id, amount, category, description, expense_date, created_at 
               FROM expenses WHERE user_id=? AND expense_date BETWEEN ? AND ? AND category=?
               ORDER BY expense_date DESC""",
            (user_id, start_date, end_date, category)
        )
    else:
        cursor = await db.execute_read(
            """SELECT id, amount, category, description, expense_date, created_at 
               FROM expenses WHERE user_id=? AND expense_date BETWEEN ? AND ?
               ORDER BY expense_date DESC""",
            (user_id, start_date, end_date)
        )
    return await cursor.fetchall()

async def get_expense_summary(user_id: int, month: str) -> Dict[str, float]:
    cursor = await db.execute_read(
        """SELECT category, SUM(amount) as total FROM expenses
           WHERE user_id=? AND strftime('%Y-%m', expense_date) = ?
           GROUP BY category""",
        (user_id, month)
    )
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}

# ==================== HABIT TRACKING ====================
async def create_habit(user_id: int, name: str, frequency: str = "daily") -> int:
    await db.execute_write(
        "INSERT INTO habits (user_id, name, frequency) VALUES (?, ?, ?)",
        (user_id, name, frequency)
    )
    result = await db.execute_read("SELECT last_insert_rowid()")
    row = await result.fetchone()
    return row[0] if row else 0

async def get_user_habits(user_id: int) -> List[Tuple]:
    cursor = await db.execute_read(
        "SELECT * FROM habits WHERE user_id=? ORDER BY created_at", (user_id,)
    )
    return await cursor.fetchall()

async def log_habit_completion(habit_id: int, completed_date: str) -> bool:
    existing = await db.execute_read(
        "SELECT id FROM habit_logs WHERE habit_id=? AND completed_date=?", (habit_id, completed_date)
    )
    if await existing.fetchone():
        return False
    await db.execute_write(
        "INSERT INTO habit_logs (habit_id, completed_date) VALUES (?, ?)", (habit_id, completed_date)
    )
    await db.execute_write(
        "UPDATE habits SET streak = streak + 1, last_completed = ? WHERE id = ?",
        (completed_date, habit_id)
    )
    return True

async def reset_habit_streak(habit_id: int):
    await db.execute_write("UPDATE habits SET streak = 0 WHERE id = ?", (habit_id,))

async def get_habit_stats(habit_id: int) -> Dict:
    cursor = await db.execute_read("SELECT COUNT(*) FROM habit_logs WHERE habit_id=?", (habit_id,))
    total = (await cursor.fetchone())[0]
    cursor = await db.execute_read("SELECT streak FROM habits WHERE id=?", (habit_id,))
    streak = (await cursor.fetchone())[0]
    return {"total_completions": total, "current_streak": streak}

# ==================== BUDGET MANAGEMENT (NEW) ====================
async def set_budget(user_id: int, category: str, amount: float, period: str = "monthly", start_date: str = "static"):
    """Set or update a budget for a category."""
    await db.execute_write(
        """INSERT INTO budgets (user_id, category, amount, period, start_date) 
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id, category, period, start_date) 
           DO UPDATE SET amount=?, updated_at=CURRENT_TIMESTAMP""",
        (user_id, category, amount, period, start_date, amount)
    )

async def get_budget_alerts(user_id: int) -> List[str]:
    """Check all budgets and return alert strings for those exceeded."""
    status = await get_budget_status(user_id)
    alerts = []
    for item in status:
        if item['percent_used'] >= 100:
            alerts.append(f"🚨 <b>{item['category'].capitalize()}</b> budget exceeded! ({item['percent_used']}%)")
        elif item['percent_used'] > 85:
            alerts.append(f"⚠️ <b>{item['category'].capitalize()}</b> budget almost full ({item['percent_used']}%)")
    return alerts

async def get_budget(user_id: int, category: str, period: str = "monthly") -> Optional[Tuple]:
    """Retrieve budget for a specific category and period."""
    cursor = await db.execute_read(
        "SELECT * FROM budgets WHERE user_id=? AND category=? AND period=?",
        (user_id, category, period)
    )
    return await cursor.fetchone()

async def get_all_budgets(user_id: int, period: str = "monthly") -> List[Tuple]:
    """Get all active budgets for a user."""
    cursor = await db.execute_read(
        "SELECT * FROM budgets WHERE user_id=? AND period=? ORDER BY category",
        (user_id, period)
    )
    return await cursor.fetchall()

async def get_budget_status(user_id: int, period: str = "monthly") -> List[Dict]:
    """Compare spending vs budget for all categories."""
    budgets = await get_all_budgets(user_id, period)
    results = []
    
    for budget in budgets:
        bid, uid, cat, amount, per, start, created, updated = budget
        # Calculate spent amount for this category/period
        cursor = await db.execute_read(
            """SELECT COALESCE(SUM(amount), 0) FROM expenses 
               WHERE user_id=? AND category=? AND strftime('%Y-%m', expense_date) = strftime('%Y-%m', 'now')""",
            (user_id, cat)
        )
        spent = (await cursor.fetchone())[0]
        remaining = amount - spent
        results.append({
            "category": cat,
            "budgeted": amount,
            "spent": spent,
            "remaining": remaining,
            "percent_used": round((spent / amount) * 100, 1) if amount > 0 else 0
        })
    return results

async def update_budget(budget_id: int, amount: float, category: Optional[str] = None):
    """Update an existing budget."""
    if category:
        await db.execute_write(
            "UPDATE budgets SET amount=?, category=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (amount, category, budget_id)
        )
    else:
        await db.execute_write(
            "UPDATE budgets SET amount=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (amount, budget_id)
        )

async def delete_budget(budget_id: int):
    """Remove a budget entry."""
    await db.execute_write("DELETE FROM budgets WHERE id=?", (budget_id,))

async def get_budget_alerts(user_id: int, threshold: float = 0.9) -> List[Dict]:
    """Find budgets where spending exceeds threshold (default 90%)."""
    statuses = await get_budget_status(user_id)
    return [s for s in statuses if s["percent_used"] >= threshold * 100]

# ==================== HYBRID SEARCH & DISCOVERY ====================
async def search_notes_hybrid(query: str, user_id: int, limit: int = 5) -> List[Dict]:
    """Combines FTS with structured metadata filtering."""
    # FTS part - Use standard FTS5 MATCH syntax
    cursor = await db.execute_read(
        """SELECT n.id, n.content, n.tags, n.created_at, n.source
           FROM notes n 
           JOIN notes_fts f ON n.id = f.id 
           WHERE notes_fts MATCH ? AND n.user_id = ?
           ORDER BY rank LIMIT ?""",
        (query, user_id, limit)
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "content": row[1],
            "tags": json.loads(row[2]),
            "created_at": row[3],
            "source": row[4],
            "score": 1.0  # Placeholder for ranking
        })
    return results

async def get_latest_activity(user_id: int) -> Dict:
    """Fetches a summary of recent activity for the dashboard."""
    # Last note
    cursor = await db.execute_read(
        "SELECT content, created_at FROM notes WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    last_note = await cursor.fetchone()
    
    # Last expense
    cursor = await db.execute_read(
        "SELECT amount, category, description FROM expenses WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    last_expense = await cursor.fetchone()
    
    return {
        "last_note": {"content": last_note[0], "date": last_note[1]} if last_note else None,
        "last_expense": {"amount": last_expense[0], "cat": last_expense[1], "desc": last_expense[2]} if last_expense else None
    }