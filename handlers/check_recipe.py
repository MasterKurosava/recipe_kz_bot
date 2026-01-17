from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Annotated
from keyboards import get_main_menu, get_cancel_button, get_back_to_menu_button
from services.recipe_service import get_recipe
import asyncpg

router = Router()


class CheckRecipeStates(StatesGroup):
    waiting_for_recipe_id = State()


@router.message(F.text == "🔍 Проверить рецепт")
async def cmd_check_recipe(message: Message, state: FSMContext):
    """Начало проверки рецепта"""
    await message.answer(
        "🔍 Введите ID рецепта для проверки:",
        reply_markup=get_cancel_button()
    )
    await state.set_state(CheckRecipeStates.waiting_for_recipe_id)


@router.message(CheckRecipeStates.waiting_for_recipe_id)
async def process_recipe_id_check(
    message: Message, 
    state: FSMContext,
    db_pool: Annotated[asyncpg.Pool, "db_pool"]
):
    """Обработка введённого ID рецепта для проверки"""
    if message.text == "❌ Отмена" or message.text == "🔙 В меню":
        await state.clear()
        await message.answer(
            "❌ Проверка отменена." if message.text == "❌ Отмена" else "",
            reply_markup=get_main_menu()
        )
        return

    recipe_id = message.text.strip()
    
    if not recipe_id:
        await message.answer("⚠️ Пожалуйста, введите корректный ID рецепта:")
        return

    # Получаем pool из middleware data
    pool = db_pool
    
    # Проверяем рецепт в базе
    recipe = await get_recipe(recipe_id, pool)

    if recipe:
        # Рецепт найден - выдача запрещена
        created_at = recipe['created_at']
        comment = recipe['comment'] if recipe['comment'] else "Нет комментария"
        user_id = recipe['user_id']
        
        date_str = created_at.strftime("%d.%m.%Y %H:%M")
        
        await message.answer(
            f"❌ Рецепт уже зарегистрирован.\n\n"
            f"📅 Дата: {date_str}\n"
            f"💬 Комментарий: {comment}\n"
            f"👤 Внёс: {user_id}",
            reply_markup=get_back_to_menu_button()
        )
    else:
        # Рецепт не найден - выдача возможна
        await message.answer(
            "✅ Рецепт не найден. Выдача возможна.",
            reply_markup=get_back_to_menu_button()
        )

    await state.clear()
