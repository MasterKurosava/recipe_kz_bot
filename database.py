import asyncpg
from typing import Optional
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> asyncpg.Pool:
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self._create_tables()
        return self.pool

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    recipe_id TEXT UNIQUE NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    user_id BIGINT NOT NULL,
                    username TEXT
                )
            """)
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_id ON recipes(recipe_id)
            """)
            try:
                await conn.execute("""
                    ALTER TABLE recipes ADD COLUMN IF NOT EXISTS username TEXT
                """)
            except Exception:
                pass


db = Database()
