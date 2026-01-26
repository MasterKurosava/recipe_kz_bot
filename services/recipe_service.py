import asyncpg
import json
from typing import Optional, List, Dict


async def is_duplicate(recipe_id: str, pool: asyncpg.Pool) -> bool:
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM recipes WHERE external_id = $1", recipe_id)
            return row is not None
    except Exception:
        return False


async def get_recipe_by_id(recipe_id: int, pool: asyncpg.Pool) -> Optional[Dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT r.id, r.doctor_id, r.created_at, r.duration_days, r.comment, r.status, u.username as doctor_username, u.full_name as doctor_name FROM recipes r JOIN users u ON r.doctor_id = u.id WHERE r.id = $1",
            recipe_id
        )
        if not row:
            return None
        
        items = await conn.fetch("SELECT id, drug_name, quantity FROM recipe_items WHERE recipe_id = $1", recipe_id)
        return {
            'id': row['id'],
            'doctor_id': row['doctor_id'],
            'created_at': row['created_at'],
            'duration_days': row['duration_days'],
            'comment': row['comment'],
            'status': row['status'],
            'doctor_username': row['doctor_username'],
            'doctor_name': row['doctor_name'],
            'items': [{'id': item['id'], 'drug_name': item['drug_name'], 'quantity': item['quantity']} for item in items]
        }


async def get_recipes_by_doctor(doctor_id: int, pool: asyncpg.Pool, limit: int = 50) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT r.id, r.doctor_id, r.created_at, r.duration_days, r.comment, r.status FROM recipes r WHERE r.doctor_id = $1 ORDER BY r.created_at DESC LIMIT $2",
            doctor_id, limit
        )
        recipes = []
        for row in rows:
            items = await conn.fetch("SELECT id, drug_name, quantity FROM recipe_items WHERE recipe_id = $1", row['id'])
            recipes.append({
                'id': row['id'],
                'doctor_id': row['doctor_id'],
                'created_at': row['created_at'],
                'duration_days': row['duration_days'],
                'comment': row['comment'],
                'status': row['status'],
                'items': [{'id': item['id'], 'drug_name': item['drug_name'], 'quantity': item['quantity']} for item in items]
            })
        return recipes


async def mark_recipe_as_used(recipe_id: int, pharmacist_id: int, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE recipes SET status = 'used' WHERE id = $1", recipe_id)
            await conn.execute(
                "INSERT INTO recipe_logs (recipe_id, pharmacist_id, action_type, changes) VALUES ($1, $2, 'used', '{}'::jsonb)",
                recipe_id, pharmacist_id
            )


async def update_recipe_item_quantity(item_id: int, new_quantity: str | int, pharmacist_id: int, recipe_id: int, pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            old_quantity = await conn.fetchval("SELECT quantity FROM recipe_items WHERE id = $1", item_id)
            new_quantity_str = str(new_quantity) if new_quantity is not None else ""
            await conn.execute("UPDATE recipe_items SET quantity = $1 WHERE id = $2", new_quantity_str, item_id)
            
            changes = {"item_id": item_id, "old_quantity": old_quantity, "new_quantity": new_quantity}
            await conn.execute(
                "INSERT INTO recipe_logs (recipe_id, pharmacist_id, action_type, changes) VALUES ($1, $2, 'edited_quantity', $3::jsonb)",
                recipe_id, pharmacist_id, json.dumps(changes)
            )


async def get_recipe_logs(recipe_id: int, pool: asyncpg.Pool) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT rl.id, rl.action_type, rl.changes, rl.created_at, u.username as pharmacist_username, u.full_name as pharmacist_name FROM recipe_logs rl JOIN users u ON rl.pharmacist_id = u.id WHERE rl.recipe_id = $1 ORDER BY rl.created_at DESC",
            recipe_id
        )
        return [{
            'id': row['id'],
            'action_type': row['action_type'],
            'changes': row['changes'],
            'created_at': row['created_at'],
            'pharmacist_username': row['pharmacist_username'],
            'pharmacist_name': row['pharmacist_name']
        } for row in rows]
