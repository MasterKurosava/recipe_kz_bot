import asyncpg
from typing import Optional


async def is_duplicate(recipe_id: str, pool: asyncpg.Pool) -> bool:
    """
    Проверка на дубликат рецепта через EXISTS
    
    Args:
        recipe_id: ID рецепта для проверки
        pool: Пул соединений asyncpg
        
    Returns:
        True если рецепт уже существует, False иначе
    """
    query = "SELECT EXISTS (SELECT 1 FROM recipes WHERE recipe_id = $1)"
    return await pool.fetchval(query, recipe_id)


async def add_recipe(recipe_id: str, user_id: int, comment: str | None, pool: asyncpg.Pool) -> None:
    """
    Добавление записи рецепта в базу данных
    
    Args:
        recipe_id: ID рецепта
        user_id: Telegram user ID
        comment: Комментарий (может быть None)
        pool: Пул соединений asyncpg
        
    Raises:
        asyncpg.UniqueViolationError: если рецепт уже существует
    """
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO recipes (recipe_id, user_id, comment) VALUES ($1, $2, $3)",
            recipe_id, user_id, comment
        )


async def get_recipe(recipe_id: str, pool: asyncpg.Pool) -> Optional[dict]:
    """
    Получение одной записи рецепта по ID
    
    Args:
        recipe_id: ID рецепта
        pool: Пул соединений asyncpg
        
    Returns:
        Словарь с данными рецепта или None если не найден
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT recipe_id, comment, created_at, user_id 
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
                'user_id': row['user_id']
            }
        return None


async def get_recipe_history(recipe_id: str, pool: asyncpg.Pool) -> list[dict]:
    """
    Получение истории по рецепту (все записи с этим ID)
    
    Args:
        recipe_id: ID рецепта
        pool: Пул соединений asyncpg
        
    Returns:
        Список словарей с данными записей
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT recipe_id, comment, created_at, user_id 
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
                'user_id': row['user_id']
            }
            for row in rows
        ]
