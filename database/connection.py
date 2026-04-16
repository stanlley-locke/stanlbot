import aiosqlite
import logging
import asyncio
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or settings.DB_PATH
        self._lock = asyncio.Lock()
        self._conn: aiosqlite.Connection | None = None

    async def init(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA synchronous=NORMAL;")
        await self._conn.execute("PRAGMA cache_size=-2000;")
        await self._conn.execute("PRAGMA temp_store=MEMORY;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.execute("PRAGMA busy_timeout=5000;")
        await self._conn.commit()
        logger.info(f"SQLite initialized: {self.db_path}")

    async def get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            await self.init()
        return self._conn

    async def execute_write(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        async with self._lock:
            conn = await self.get_conn()
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor

    async def execute_read(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        conn = await self.get_conn()
        return await conn.execute(sql, params)

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")

db = DatabaseManager()