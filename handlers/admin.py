from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from typing import Annotated
import asyncpg
from services.user_service import add_user, get_users_by_role, delete_user, get_user_by_id, get_user_by_telegram_id
from services.recipe_service import get_all_recipes
from keyboards.common import get_role_menu

router = Router()


class AddUserStates(StatesGroup):
    waiting_for_user_identifier = State()
    waiting_for_role = State()


@router.message(F.text == "➕ Добавить пользователя")
async def cmd_add_user(message: Message, state: FSMContext, user: dict):
    await message.answer(
        "➕ <b>Добавление пользователя</b>\n\n"
        "Введите user_id (число) или username пользователя:",
        parse_mode="HTML"
    )
    await state.set_state(AddUserStates.waiting_for_user_identifier)


@router.message(AddUserStates.waiting_for_user_identifier)
async def process_user_identifier(message: Message, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"], user: dict):
    identifier = message.text.strip().replace('@', '')
    
    telegram_id = None
    username = None
    
    if identifier.isdigit():
        telegram_id = int(identifier)
    else:
        username = identifier
    
    if not telegram_id:
        await message.answer(
            "⚠️ Для добавления пользователя необходимо указать user_id (число).\n"
            "Username можно указать дополнительно, но user_id обязателен."
        )
        return
    
    existing = await get_user_by_telegram_id(telegram_id, db_pool)
    if existing:
        await message.answer(f"❌ Пользователь с ID {telegram_id} уже зарегистрирован с ролью: {existing['role']}")
        await state.clear()
        return
    
    await state.update_data(
        telegram_id=telegram_id,
        username=username
    )
    
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
        f"Выберите роль для пользователя:\n"
        f"User ID: {telegram_id}\n"
        f"Username: @{username if username else 'не указан'}",
        reply_markup=keyboard
    )
    await state.set_state(AddUserStates.waiting_for_role)


@router.callback_query(F.data.startswith("role_"), AddUserStates.waiting_for_role)
async def process_role_selection(callback: CallbackQuery, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
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
    
    text = "👥 <b>Список пользователей</b>\n\n"
    
    text += "👨‍⚕️ <b>Врачи:</b>\n"
    if doctors:
        for doc in doctors:
            text += f"• ID: {doc['id']} | User ID: {doc['telegram_id']} | @{doc.get('username') or 'N/A'}\n"
    else:
        text += "Нет врачей\n"
    
    text += "\n💊 <b>Фармацевты:</b>\n"
    if pharmacists:
        for pharm in pharmacists:
            text += f"• ID: {pharm['id']} | User ID: {pharm['telegram_id']} | @{pharm.get('username') or 'N/A'}\n"
    else:
        text += "Нет фармацевтов\n"
    
    text += "\nДля удаления используйте: /delete_user <user_id>"
    
    await message.answer(text, parse_mode="HTML")


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


@router.message(F.text == "📋 Все рецепты")
async def cmd_all_recipes(message: Message, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipes = await get_all_recipes(db_pool)
    
    if not recipes:
        await message.answer("📭 Рецепты не найдены")
        return
    
    text = f"📋 <b>Все рецепты (последние {len(recipes)})</b>\n\n"
    
    for recipe in recipes[:20]:
        status_emoji = "✅" if recipe['status'] == 'used' else "📝"
        text += f"{status_emoji} <b>Рецепт #{recipe['id']}</b>\n"
        text += f"👨‍⚕️ Врач: {recipe.get('doctor_name') or recipe.get('doctor_username') or 'N/A'}\n"
        text += f"📅 Дата: {recipe['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
        text += f"⏱ Длительность: {recipe['duration_days']} дней\n"
        text += f"💊 Препараты: {len(recipe['items'])}\n\n"
    
    if len(recipes) > 20:
        text += f"... и ещё {len(recipes) - 20} рецептов"
    
    await message.answer(text, parse_mode="HTML")
