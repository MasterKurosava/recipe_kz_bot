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
    await message.answer(
        "🔍 <b>Проверка рецепта</b>\n\n"
        "📝 Введите ID рецепта для проверки:",
        reply_markup=get_cancel_button(),
        parse_mode="HTML"
    )
    await state.set_state(CheckRecipeStates.waiting_for_recipe_id)


@router.message(CheckRecipeStates.waiting_for_recipe_id)
async def process_recipe_id_check(
    message: Message, 
    state: FSMContext,
    db_pool: Annotated[asyncpg.Pool, "db_pool"]
):
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

    pool = db_pool
    
    recipe = await get_recipe(recipe_id, pool)

    if recipe:
        created_at = recipe['created_at']
        comment = recipe['comment'] if recipe['comment'] else "Нет комментария"
        username = recipe.get('username')
        user_display = f"@{username}" if username else f"ID: {recipe['user_id']}"
        
        date_str = created_at.strftime("%d.%m.%Y в %H:%M")
        
        response_text = (
            "❌ <b>Рецепт уже зарегистрирован!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID рецепта:</b> <code>{recipe_id}</code>\n"
            f"📅 <b>Дата регистрации:</b> {date_str}\n"
            f"💬 <b>Комментарий:</b> {comment}\n"
            f"👤 <b>Внёс:</b> {user_display}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔒 <b>Повторная выдача запрещена</b>"
        )
        
        await message.answer(
            response_text,
            reply_markup=get_back_to_menu_button(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"✅ <b>Рецепт не найден в базе</b>\n\n"
            f"🆔 <b>ID:</b> <code>{recipe_id}</code>\n\n"
            "✅ <b>Выдача возможна</b>",
            reply_markup=get_back_to_menu_button(),
            parse_mode="HTML"
        )

    await state.clear()
