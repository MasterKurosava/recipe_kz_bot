import asyncpg
from typing import Optional, List, Dict
from datetime import datetime, timedelta


async def create_recipe(doctor_id: int, duration_days: int, comment: Optional[str], pool: asyncpg.Pool) -> int:
    async with pool.acquire() as conn:
        recipe_id = await conn.fetchval(
            """
            INSERT INTO recipes (doctor_id, duration_days, comment, status)
            VALUES ($1, $2, $3, 'active')
            RETURNING id
            """,
            doctor_id, duration_days, comment
        )
        return recipe_id


async def add_recipe_item(recipe_id: int, drug_name: str, quantity: int, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO recipe_items (recipe_id, drug_name, quantity) VALUES ($1, $2, $3)",
            recipe_id, drug_name, quantity
        )


async def get_recipe_by_id(recipe_id: int, pool: asyncpg.Pool) -> Optional[Dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT r.id, r.doctor_id, r.created_at, r.duration_days, r.comment, r.status,
                   u.username as doctor_username, u.full_name as doctor_name
            FROM recipes r
            JOIN users u ON r.doctor_id = u.id
            WHERE r.id = $1
            """,
            recipe_id
        )
        if row:
            items = await conn.fetch(
                "SELECT id, drug_name, quantity FROM recipe_items WHERE recipe_id = $1",
                recipe_id
            )
            return {
                'id': row['id'],
                'doctor_id': row['doctor_id'],
                'created_at': row['created_at'],
                'duration_days': row['duration_days'],
                'comment': row['comment'],
                'status': row['status'],
                'doctor_username': row['doctor_username'],
                'doctor_name': row['doctor_name'],
                'items': [
                    {'id': item['id'], 'drug_name': item['drug_name'], 'quantity': item['quantity']}
                    for item in items
                ]
            }
        return None


async def mark_recipe_as_used(recipe_id: int, pharmacist_id: int, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE recipes SET status = 'used' WHERE id = $1",
                recipe_id
            )
            await conn.execute(
                """
                INSERT INTO recipe_logs (recipe_id, pharmacist_id, action_type, changes)
                VALUES ($1, $2, 'used', '{}'::jsonb)
                """,
                recipe_id, pharmacist_id
            )


async def update_recipe_item_quantity(item_id: int, new_quantity: int, pharmacist_id: int, recipe_id: int, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            old_quantity_row = await conn.fetchrow(
                "SELECT quantity FROM recipe_items WHERE id = $1",
                item_id
            )
            old_quantity = old_quantity_row['quantity'] if old_quantity_row else None
            
            await conn.execute(
                "UPDATE recipe_items SET quantity = $1 WHERE id = $2",
                new_quantity, item_id
            )
            
            changes = {
                'item_id': item_id,
                'old_quantity': old_quantity,
                'new_quantity': new_quantity
            }
            
            await conn.execute(
                """
                INSERT INTO recipe_logs (recipe_id, pharmacist_id, action_type, changes)
                VALUES ($1, $2, 'edited_quantity', $3::jsonb)
                """,
                recipe_id, pharmacist_id, str(changes).replace("'", '"')
            )


async def get_all_recipes(pool: asyncpg.Pool, limit: int = 100) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT r.id, r.doctor_id, r.created_at, r.duration_days, r.comment, r.status,
                   u.username as doctor_username, u.full_name as doctor_name
            FROM recipes r
            JOIN users u ON r.doctor_id = u.id
            ORDER BY r.created_at DESC
            LIMIT $1
            """,
            limit
        )
        recipes = []
        for row in rows:
            items = await conn.fetch(
                "SELECT id, drug_name, quantity FROM recipe_items WHERE recipe_id = $1",
                row['id']
            )
            recipes.append({
                'id': row['id'],
                'doctor_id': row['doctor_id'],
                'created_at': row['created_at'],
                'duration_days': row['duration_days'],
                'comment': row['comment'],
                'status': row['status'],
                'doctor_username': row['doctor_username'],
                'doctor_name': row['doctor_name'],
                'items': [
                    {'id': item['id'], 'drug_name': item['drug_name'], 'quantity': item['quantity']}
                    for item in items
                ]
            })
        return recipes


async def get_recipe_logs(recipe_id: int, pool: asyncpg.Pool) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT rl.id, rl.action_type, rl.changes, rl.created_at,
                   u.username as pharmacist_username, u.full_name as pharmacist_name
            FROM recipe_logs rl
            JOIN users u ON rl.pharmacist_id = u.id
            WHERE rl.recipe_id = $1
            ORDER BY rl.created_at DESC
            """,
            recipe_id
        )
        return [
            {
                'id': row['id'],
                'action_type': row['action_type'],
                'changes': row['changes'],
                'created_at': row['created_at'],
                'pharmacist_username': row['pharmacist_username'],
                'pharmacist_name': row['pharmacist_name']
            }
            for row in rows
        ]
