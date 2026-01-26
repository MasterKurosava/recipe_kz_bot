import asyncpg
from typing import Optional, List, Dict


async def get_user_by_telegram_id(telegram_id: int, pool: asyncpg.Pool) -> Optional[Dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, telegram_id, username, full_name, role FROM users WHERE telegram_id = $1", telegram_id)
        return {
            'id': row['id'],
            'telegram_id': row['telegram_id'],
            'username': row['username'],
            'full_name': row['full_name'],
            'role': row['role']
        } if row else None


async def add_user(telegram_id: int, username: Optional[str], full_name: Optional[str], role: str, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (telegram_id, username, full_name, role) VALUES ($1, $2, $3, $4)", telegram_id, username, full_name, role)


async def delete_user(user_id: int, pool: asyncpg.Pool) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        return result == "DELETE 1"


async def get_users_by_role(role: str, pool: asyncpg.Pool) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, telegram_id, username, full_name, role FROM users WHERE role = $1 ORDER BY id", role)
        return [{
            'id': row['id'],
            'telegram_id': row['telegram_id'],
            'username': row['username'],
            'full_name': row['full_name'],
            'role': row['role']
        } for row in rows]


async def get_user_by_id(user_id: int, pool: asyncpg.Pool) -> Optional[Dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, telegram_id, username, full_name, role FROM users WHERE id = $1", user_id)
        return {
            'id': row['id'],
            'telegram_id': row['telegram_id'],
            'username': row['username'],
            'full_name': row['full_name'],
            'role': row['role']
        } if row else None
