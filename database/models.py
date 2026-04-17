import logging
from database.connection import db

logger = logging.getLogger(__name__)

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT, language TEXT DEFAULT 'en',
        points INTEGER DEFAULT 0, streak INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        content TEXT NOT NULL, tags TEXT DEFAULT '[]',
        source TEXT DEFAULT 'manual', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS notes_fts (
        id INTEGER PRIMARY KEY, content TEXT
    )""",
    """CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts_idx USING fts5(
        content, content='notes_fts', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes_fts BEGIN
        INSERT INTO notes_fts_idx(rowid, content) VALUES (new.id, new.content);
    END""",
    """CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id), title TEXT NOT NULL,
        deadline TIMESTAMP, status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id),
        message TEXT NOT NULL, trigger_time TIMESTAMP NOT NULL, sent INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS whatsapp_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id),
        sender TEXT, content TEXT, timestamp TIMESTAMP, file_path TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS grocery_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id),
        item TEXT NOT NULL, quantity INTEGER DEFAULT 1, completed INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        period TEXT DEFAULT 'monthly',
        start_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, category, period, start_date)
    )""",  
    """CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id),
        amount REAL NOT NULL, category TEXT NOT NULL, description TEXT,
        expense_date DATE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id),
        name TEXT NOT NULL, frequency TEXT DEFAULT 'daily', 
        streak INTEGER DEFAULT 0, last_completed DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, habit_id INTEGER REFERENCES habits(id),
        completed_date DATE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status)",
    "CREATE INDEX IF NOT EXISTS idx_reminders_sent ON reminders(sent)",
    "CREATE INDEX IF NOT EXISTS idx_grocery_user ON grocery_items(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)",
    "CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id)"
]

async def init_database():
    conn = await db.get_conn()
    for sql in SCHEMA_SQL:
        await conn.execute(sql)
    await conn.commit()
    
    # Check version
    cursor = await conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    row = await cursor.fetchone()
    current_version = row[0] if row else 0
    if current_version < 1:
        await conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        await conn.commit()
        logger.info("Database schema initialized at version 1")