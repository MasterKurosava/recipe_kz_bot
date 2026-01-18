import asyncpg
from typing import Optional
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> asyncpg.Pool:
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self._run_migrations()
        return self.pool

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def _run_migrations(self):
        import os
        async with self.pool.acquire() as conn:
            migration_path = os.path.join('migrations', '001_initial_schema.sql')
            if os.path.exists(migration_path):
                with open(migration_path, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                await conn.execute(migration_sql)


db = Database()
