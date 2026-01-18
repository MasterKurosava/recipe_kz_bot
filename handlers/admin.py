from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from typing import Annotated
import asyncpg
from services.user_service import add_user, get_users_by_role, delete_user, get_user_by_id, get_user_by_telegram_id
from services.recipe_service import get_recipe_by_id, get_recipe_logs, mark_recipe_as_used, update_recipe_item_quantity
from keyboards.common import get_role_menu, get_recipe_actions_keyboard, get_item_edit_keyboard
from utils.date_formatter import format_datetime
from utils.recipe_formatter import format_recipe_detail, format_recipe_logs

router = Router()


class AddUserStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_username = State()
    waiting_for_role = State()


@router.message(F.text == "➕ Добавить пользователя")
async def cmd_add_user(message: Message, state: FSMContext, user: dict):
    await message.answer(
        "➕ <b>Добавление пользователя</b>\n\n"
        "📝 Введите user_id (число):",
        parse_mode="HTML"
    )
    await state.set_state(AddUserStates.waiting_for_user_id)


@router.message(AddUserStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"], user: dict):
    user_input = message.text.strip()
    
    try:
        telegram_id = int(user_input)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный user_id (число):")
        return
    
    existing = await get_user_by_telegram_id(telegram_id, db_pool)
    if existing:
        await message.answer(f"❌ Пользователь с ID {telegram_id} уже зарегистрирован с ролью: {existing['role']}")
        await state.clear()
        return
    
    await state.update_data(telegram_id=telegram_id)
    
    await message.answer(
        "📝 Введите username пользователя (или отправьте 'пропустить' для пропуска):",
        parse_mode="HTML"
    )
    await state.set_state(AddUserStates.waiting_for_username)


@router.message(AddUserStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext, user: dict):
    user_input = message.text.strip().lower()
    
    username = None
    if user_input not in ['пропустить', 'skip', 'нет']:
        username = message.text.strip().replace('@', '')
    
    await state.update_data(username=username)
    
    data = await state.get_data()
    telegram_id = data['telegram_id']
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨‍⚕️ Врач", callback_data="role_doctor"),
                InlineKeyboardButton(text="💊 Фармацевт", callback_data="role_pharmacist")
            ]
        ]
    )
    
    await message.answer(
        f"✅ Выберите роль для пользователя:\n\n"
        f"User ID: <code>{telegram_id}</code>\n"
        f"Username: @{username if username else 'не указан'}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddUserStates.waiting_for_role)


@router.callback_query(F.data.startswith("role_"), AddUserStates.waiting_for_role)
async def process_role_selection(callback: CallbackQuery, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"], user: dict):
    role = callback.data.split("_")[1]
    data = await state.get_data()
    
    try:
        await add_user(
            data['telegram_id'],
            data.get('username'),
            None,
            role,
            db_pool
        )
        await callback.message.edit_text(
            f"✅ Пользователь успешно добавлен с ролью: {role}\n\n"
            f"User ID: {data['telegram_id']}\n"
            f"Username: @{data.get('username') or 'не указан'}"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    await state.clear()
    await callback.answer()


@router.message(F.text == "👥 Список пользователей")
async def cmd_list_users(message: Message, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    doctors = await get_users_by_role('doctor', db_pool)
    pharmacists = await get_users_by_role('pharmacist', db_pool)
    
    from utils.message_splitter import split_long_message
    
    text = "👥 <b>Список пользователей</b>\n\n"
    
    text += "👨‍⚕️ <b>Врачи:</b>\n"
    if doctors:
        for doc in doctors:
            username = doc.get('username') or 'N/A'
            text += f"• ID: {doc['id']} | User ID: {doc['telegram_id']} | @{username}\n"
    else:
        text += "Нет врачей\n"
    
    text += "\n💊 <b>Фармацевты:</b>\n"
    if pharmacists:
        for pharm in pharmacists:
            username = pharm.get('username') or 'N/A'
            text += f"• ID: {pharm['id']} | User ID: {pharm['telegram_id']} | @{username}\n"
    else:
        text += "Нет фармацевтов\n"
    
    text += "\nДля удаления используйте: /delete_user <user_id>"
    
    chunks = split_long_message(text, max_length=4000)
    for i, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode="HTML" if i == 0 else None
        )


@router.message(Command("delete_user"))
async def cmd_delete_user(message: Message, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /delete_user <user_id>")
        return
    
    try:
        user_id = int(parts[1])
        target_user = await get_user_by_id(user_id, db_pool)
        if not target_user:
            await message.answer("❌ Пользователь не найден")
            return
        
        if target_user['role'] == 'admin':
            await message.answer("❌ Нельзя удалить администратора")
            return
        
        success = await delete_user(user_id, db_pool)
        if success:
            await message.answer(
                f"✅ Пользователь удалён\n\n"
                f"ID: {user_id}\n"
                f"User ID: {target_user['telegram_id']}\n"
                f"Роль: {target_user['role']}"
            )
        else:
            await message.answer("❌ Ошибка при удалении")
    except ValueError:
        await message.answer("❌ Неверный формат user_id")


@router.message(F.text == "🔍 Найти рецепт")
async def cmd_find_recipe(message: Message, state: FSMContext, user: dict):
    await message.answer(
        "🔍 <b>Поиск рецепта</b>\n\n"
        "📝 Введите ID рецепта:",
        parse_mode="HTML"
    )
    await state.set_state(FindRecipeStates.waiting_for_recipe_id)


@router.message(FindRecipeStates.waiting_for_recipe_id)
async def process_find_recipe_id(message: Message, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"], user: dict):
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
    
    recipe_text = format_recipe_detail(recipe, recipe_id)
    
    if recipe['status'] == 'active':
        await message.answer(
            recipe_text,
            reply_markup=get_recipe_actions_keyboard(recipe_id),
            parse_mode="HTML"
        )
    else:
        logs = await get_recipe_logs(recipe_id, db_pool)
        recipe_text += format_recipe_logs(logs)
        await message.answer(recipe_text, parse_mode="HTML")
    
    await state.clear()


@router.callback_query(F.data.startswith("mark_used_"))
async def admin_mark_used_handler(callback: CallbackQuery, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
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
async def admin_edit_quantity_select(callback: CallbackQuery, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"], user: dict):
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


class EditQuantityStates(StatesGroup):
    waiting_for_new_quantity = State()


@router.callback_query(F.data.startswith("edit_item_"))
async def admin_edit_item_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    recipe_id = int(parts[2])
    item_id = int(parts[3])
    
    await state.update_data(recipe_id=recipe_id, item_id=item_id)
    await callback.message.edit_text("✏️ Введите новое количество:")
    await state.set_state(EditQuantityStates.waiting_for_new_quantity)
    await callback.answer()


@router.message(EditQuantityStates.waiting_for_new_quantity)
async def admin_process_new_quantity(message: Message, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
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
        recipe_text = format_recipe_detail(recipe, recipe_id)
        
        await message.answer(
            f"✅ Количество обновлено!\n\n{recipe_text}",
            reply_markup=get_recipe_actions_keyboard(recipe_id) if recipe['status'] == 'active' else None,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data.startswith("back_recipe_"))
async def admin_back_to_recipe(callback: CallbackQuery, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipe_id = int(callback.data.split("_")[-1])
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    
    recipe_text = format_recipe_detail(recipe, recipe_id)
    
    await callback.message.edit_text(
        recipe_text,
        reply_markup=get_recipe_actions_keyboard(recipe_id) if recipe['status'] == 'active' else None,
        parse_mode="HTML"
    )
    await callback.answer()
