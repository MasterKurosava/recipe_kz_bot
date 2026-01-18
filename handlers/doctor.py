from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Annotated
import asyncpg
from services.recipe_service import create_recipe, add_recipe_item, get_recipe_by_id
from keyboards.common import get_duration_keyboard, get_recipe_items_actions_keyboard, get_confirm_keyboard, get_item_delete_keyboard
import json

router = Router()


class AddRecipeStates(StatesGroup):
    waiting_for_drug_name = State()
    waiting_for_quantity = State()
    waiting_for_more_items = State()
    waiting_for_comment = State()
    waiting_for_duration = State()
    waiting_for_custom_duration = State()
    waiting_for_confirmation = State()


@router.message(F.text == "➕ Добавить рецепт")
async def cmd_add_recipe(message: Message, state: FSMContext, user: dict):
    await state.update_data(items=[])
    await message.answer(
        "➕ <b>Добавление нового рецепта</b>\n\n"
        "📝 Введите название первого препарата:",
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_drug_name)


@router.message(AddRecipeStates.waiting_for_drug_name)
async def process_drug_name(message: Message, state: FSMContext):
    drug_name = message.text.strip()
    data = await state.get_data()
    data.setdefault('items', []).append({'drug_name': drug_name, 'quantity': None})
    await state.update_data(items=data['items'])
    
    await message.answer(
        f"💊 <b>{drug_name}</b>\n\n"
        "Введите количество:",
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_quantity)


@router.message(AddRecipeStates.waiting_for_quantity)
async def process_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            await message.answer("❌ Количество должно быть положительным числом")
            return
    except ValueError:
        await message.answer("❌ Введите число")
        return
    
    data = await state.get_data()
    if data['items']:
        data['items'][-1]['quantity'] = quantity
    
    items_text = "\n".join([
        f"• {item['drug_name']} - {item['quantity']}" if item['quantity'] else f"• {item['drug_name']} - ?"
        for item in data['items']
    ])
    
    await message.answer(
        f"📋 <b>Текущий список препаратов:</b>\n\n{items_text}\n\n"
        "Выберите действие:",
        reply_markup=get_recipe_items_actions_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_more_items)


@router.callback_query(F.data == "add_more_item", AddRecipeStates.waiting_for_more_items)
async def add_more_item(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Введите название следующего препарата:")
    await state.set_state(AddRecipeStates.waiting_for_drug_name)
    await callback.answer()


@router.callback_query(F.data == "delete_item", AddRecipeStates.waiting_for_more_items)
async def delete_item_select(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get('items'):
        await callback.answer("Нет препаратов для удаления", show_alert=True)
        return
    
    await callback.message.edit_text(
        "❌ Выберите препарат для удаления:",
        reply_markup=get_item_delete_keyboard(data['items'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_item_"), AddRecipeStates.waiting_for_more_items)
async def delete_item_confirm(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    
    if 0 <= idx < len(data['items']):
        deleted = data['items'].pop(idx)
        await state.update_data(items=data['items'])
        
        items_text = "\n".join([
            f"• {item['drug_name']} - {item['quantity']}"
            for item in data['items']
        ]) if data['items'] else "Список пуст"
        
        await callback.message.edit_text(
            f"✅ <b>{deleted['drug_name']}</b> удалён\n\n"
            f"📋 <b>Текущий список:</b>\n\n{items_text}\n\n"
            "Выберите действие:",
            reply_markup=get_recipe_items_actions_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "done_delete", AddRecipeStates.waiting_for_more_items)
async def done_delete(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    items_text = "\n".join([
        f"• {item['drug_name']} - {item['quantity']}"
        for item in data['items']
    ]) if data['items'] else "Список пуст"
    
    await callback.message.edit_text(
        f"📋 <b>Текущий список препаратов:</b>\n\n{items_text}\n\n"
        "Выберите действие:",
        reply_markup=get_recipe_items_actions_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "continue_recipe", AddRecipeStates.waiting_for_more_items)
async def continue_recipe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get('items') or any(not item.get('quantity') for item in data['items']):
        await callback.answer("Добавьте хотя бы один препарат с количеством", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💬 Введите комментарий к рецепту (или отправьте /skip для пропуска):"
    )
    await state.set_state(AddRecipeStates.waiting_for_comment)
    await callback.answer()


@router.message(AddRecipeStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    comment = None
    if message.text != "/skip":
        comment = message.text.strip()
    
    await state.update_data(comment=comment)
    
    await message.answer(
        "⏱ <b>Укажите длительность действия рецепта:</b>",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_duration)


@router.callback_query(F.data.startswith("duration_"), AddRecipeStates.waiting_for_duration)
async def process_duration(callback: CallbackQuery, state: FSMContext):
    duration_type = callback.data.split("_")[1]
    
    if duration_type == "custom":
        await callback.message.edit_text("Введите длительность в днях:")
        await state.set_state(AddRecipeStates.waiting_for_custom_duration)
    else:
        duration_days = int(duration_type)
        await state.update_data(duration_days=duration_days)
        await show_confirmation(callback.message, state, callback)
    
    await callback.answer()


@router.message(AddRecipeStates.waiting_for_custom_duration)
async def process_custom_duration(message: Message, state: FSMContext):
    try:
        duration_days = int(message.text.strip())
        if duration_days <= 0:
            await message.answer("❌ Длительность должна быть положительным числом")
            return
        await state.update_data(duration_days=duration_days)
        await show_confirmation(message, state)
    except ValueError:
        await message.answer("❌ Введите число")


async def show_confirmation(message: Message | CallbackQuery, state: FSMContext, callback: CallbackQuery = None):
    data = await state.get_data()
    
    items_text = "\n".join([
        f"• {item['drug_name']} - {item['quantity']}"
        for item in data['items']
    ])
    
    duration_days = data.get('duration_days', 0)
    duration_text = f"{duration_days} дней"
    if duration_days == 30:
        duration_text = "1 месяц"
    elif duration_days == 90:
        duration_text = "3 месяца"
    elif duration_days == 180:
        duration_text = "6 месяцев"
    elif duration_days == 365:
        duration_text = "1 год"
    
    confirmation_text = (
        "📋 <b>Предпросмотр рецепта</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💊 <b>Препараты:</b>\n{items_text}\n\n"
        f"⏱ <b>Длительность:</b> {duration_text}\n"
    )
    
    if data.get('comment'):
        confirmation_text += f"💬 <b>Комментарий:</b> {data['comment']}\n"
    
    confirmation_text += "━━━━━━━━━━━━━━━━━━━━\n\nПодтвердите создание рецепта:"
    
    if isinstance(message, Message):
        await message.answer(confirmation_text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text(confirmation_text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_recipe", AddRecipeStates.waiting_for_confirmation)
async def confirm_recipe(callback: CallbackQuery, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    data = await state.get_data()
    
    try:
        recipe_id = await create_recipe(
            user['id'],
            data['duration_days'],
            data.get('comment'),
            db_pool
        )
        
        for item in data['items']:
            await add_recipe_item(recipe_id, item['drug_name'], item['quantity'], db_pool)
        
        await callback.message.edit_text(
            f"✅ <b>Рецепт успешно создан!</b>\n\n"
            f"🆔 <b>ID рецепта:</b> <code>{recipe_id}</code>\n\n"
            "Рецепт сохранён в базу данных.",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при создании рецепта: {str(e)}")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_recipe", AddRecipeStates.waiting_for_confirmation)
async def cancel_recipe(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Создание рецепта отменено")
    await state.clear()
    await callback.answer()
