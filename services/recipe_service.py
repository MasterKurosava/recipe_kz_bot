import asyncpg
from typing import Optional


async def is_duplicate(recipe_id: str, pool: asyncpg.Pool) -> bool:
    query = "SELECT EXISTS (SELECT 1 FROM recipes WHERE recipe_id = $1)"
    return await pool.fetchval(query, recipe_id)


async def add_recipe(recipe_id: str, user_id: int, comment: str | None, username: str | None, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO recipes (recipe_id, user_id, comment, username) VALUES ($1, $2, $3, $4)",
            recipe_id, user_id, comment, username
        )


async def get_recipe(recipe_id: str, pool: asyncpg.Pool) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT recipe_id, comment, created_at, user_id, username 
            FROM recipes 
            WHERE recipe_id = $1
            """,
            recipe_id
        )
        if row:
            return {
                'recipe_id': row['recipe_id'],
                'comment': row['comment'],
                'created_at': row['created_at'],
                'user_id': row['user_id'],
                'username': row['username']
            }
        return None


async def get_recipe_history(recipe_id: str, pool: asyncpg.Pool) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT recipe_id, comment, created_at, user_id, username 
            FROM recipes 
            WHERE recipe_id = $1 
            ORDER BY created_at DESC
            """,
            recipe_id
        )
        return [
            {
                'recipe_id': row['recipe_id'],
                'comment': row['comment'],
                'created_at': row['created_at'],
                'user_id': row['user_id'],
                'username': row['username']
            }
            for row in rows
        ]
