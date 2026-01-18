from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Annotated
import asyncpg
from services.recipe_service import get_recipe_by_id, mark_recipe_as_used, update_recipe_item_quantity, get_recipe_logs
from services.user_service import get_user_by_id
from keyboards.common import get_recipe_actions_keyboard, get_item_edit_keyboard
import json

router = Router()


class CheckRecipeStates(StatesGroup):
    waiting_for_recipe_id = State()


class EditQuantityStates(StatesGroup):
    waiting_for_new_quantity = State()


@router.message(F.text == "🔍 Проверить рецепт")
async def cmd_check_recipe(message: Message, state: FSMContext, user: dict):
    await message.answer(
        "🔍 <b>Проверка рецепта</b>\n\n"
        "📝 Введите ID рецепта:",
        parse_mode="HTML"
    )
    await state.set_state(CheckRecipeStates.waiting_for_recipe_id)


@router.message(CheckRecipeStates.waiting_for_recipe_id)
async def process_recipe_id(message: Message, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    try:
        recipe_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число")
        return
    
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    
    if not recipe:
        await message.answer(f"❌ Рецепт с ID <code>{recipe_id}</code> не найден", parse_mode="HTML")
        await state.clear()
        return
    
    from datetime import datetime, timedelta
    created_at = recipe['created_at']
    expires_at = created_at + timedelta(days=recipe['duration_days'])
    is_expired = datetime.now() > expires_at
    
    status_emoji = "✅" if recipe['status'] == 'used' else "📝"
    status_text = "Списан" if recipe['status'] == 'used' else "Активен"
    
    items_text = "\n".join([
        f"• {item['drug_name']} - {item['quantity']} шт."
        for item in recipe['items']
    ])
    
    recipe_text = (
        f"{status_emoji} <b>Рецепт #{recipe_id}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👨‍⚕️ <b>Врач:</b> {recipe.get('doctor_name') or recipe.get('doctor_username')}\n"
        f"📅 <b>Дата создания:</b> {created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"⏱ <b>Срок действия:</b> {recipe['duration_days']} дней (до {expires_at.strftime('%d.%m.%Y')})\n"
        f"📊 <b>Статус:</b> {status_text}\n"
    )
    
    if is_expired and recipe['status'] == 'active':
        recipe_text += "⚠️ <b>Рецепт просрочен!</b>\n"
    
    recipe_text += (
        f"\n💊 <b>Препараты:</b>\n{items_text}\n"
    )
    
    if recipe.get('comment'):
        recipe_text += f"\n💬 <b>Комментарий:</b> {recipe['comment']}\n"
    
    recipe_text += "━━━━━━━━━━━━━━━━━━━━"
    
    if recipe['status'] == 'active':
        await message.answer(
            recipe_text,
            reply_markup=get_recipe_actions_keyboard(recipe_id),
            parse_mode="HTML"
        )
    else:
        logs = await get_recipe_logs(recipe_id, db_pool)
        if logs:
            recipe_text += "\n\n📝 <b>История изменений:</b>\n"
            for log in logs:
                pharmacist_name = log.get('pharmacist_username') or log.get('pharmacist_name') or 'Unknown'
                action_text = "Списан" if log['action_type'] == 'used' else "Изменено количество"
                recipe_text += f"• {action_text} - {pharmacist_name} ({log['created_at'].strftime('%d.%m.%Y %H:%M')})\n"
        
        await message.answer(recipe_text, parse_mode="HTML")
    
    await state.clear()


@router.callback_query(F.data.startswith("mark_used_"))
async def mark_used_handler(callback: CallbackQuery, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipe_id = int(callback.data.split("_")[-1])
    
    try:
        await mark_recipe_as_used(recipe_id, user['id'], db_pool)
        await callback.message.edit_text(
            f"✅ <b>Рецепт #{recipe_id} отмечен как списанный</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    await callback.answer()


@router.callback_query(F.data.startswith("edit_quantity_"))
async def edit_quantity_select(callback: CallbackQuery, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipe_id = int(callback.data.split("_")[-1])
    
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    
    await state.update_data(recipe_id=recipe_id)
    
    await callback.message.edit_text(
        "✏️ <b>Выберите препарат для изменения количества:</b>",
        reply_markup=get_item_edit_keyboard(recipe_id, recipe['items']),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_item_"))
async def edit_item_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    recipe_id = int(parts[2])
    item_id = int(parts[3])
    
    await state.update_data(recipe_id=recipe_id, item_id=item_id)
    await callback.message.edit_text("✏️ Введите новое количество:")
    await state.set_state(EditQuantityStates.waiting_for_new_quantity)
    await callback.answer()


@router.message(EditQuantityStates.waiting_for_new_quantity)
async def process_new_quantity(message: Message, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    try:
        new_quantity = int(message.text.strip())
        if new_quantity <= 0:
            await message.answer("❌ Количество должно быть положительным числом")
            return
    except ValueError:
        await message.answer("❌ Введите число")
        return
    
    data = await state.get_data()
    recipe_id = data['recipe_id']
    item_id = data['item_id']
    
    try:
        await update_recipe_item_quantity(item_id, new_quantity, user['id'], recipe_id, db_pool)
        
        recipe = await get_recipe_by_id(recipe_id, db_pool)
        items_text = "\n".join([
            f"• {item['drug_name']} - {item['quantity']} шт."
            for item in recipe['items']
        ])
        
        await message.answer(
            f"✅ <b>Количество обновлено!</b>\n\n"
            f"💊 <b>Текущие препараты:</b>\n{items_text}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data.startswith("back_recipe_"))
async def back_to_recipe(callback: CallbackQuery, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipe_id = int(callback.data.split("_")[-1])
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    
    items_text = "\n".join([
        f"• {item['drug_name']} - {item['quantity']} шт."
        for item in recipe['items']
    ])
    
    recipe_text = (
        f"📝 <b>Рецепт #{recipe_id}</b>\n\n"
        f"💊 <b>Препараты:</b>\n{items_text}\n\n"
    )
    
    await callback.message.edit_text(
        recipe_text,
        reply_markup=get_recipe_actions_keyboard(recipe_id),
        parse_mode="HTML"
    )
    await callback.answer()
