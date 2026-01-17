import asyncpg
from typing import Optional
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> asyncpg.Pool:
        """Подключение к базе данных и создание таблицы"""
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self._create_tables()
        return self.pool

    async def disconnect(self):
        """Закрытие соединения с базой данных"""
        if self.pool:
            await self.pool.close()

    async def _create_tables(self):
        """Создание таблицы recipes и индекса если их нет"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    recipe_id TEXT UNIQUE NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    user_id BIGINT NOT NULL
                )
            """)
            # Создаём индекс для быстрого поиска по recipe_id
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_id ON recipes(recipe_id)
            """)


# Глобальный экземпляр базы данных
db = Database()
