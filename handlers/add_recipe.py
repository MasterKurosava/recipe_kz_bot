from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Annotated
from keyboards import (
    get_main_menu, get_skip_button, get_cancel_button, 
    get_back_to_menu_button, get_confirm_buttons
)
from services.recipe_service import is_duplicate, add_recipe
import asyncpg

router = Router()


class AddRecipeStates(StatesGroup):
    waiting_for_recipe_id = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


@router.message(F.text == "➕ Добавить рецепт")
async def cmd_add_recipe(message: Message, state: FSMContext):
    await message.answer(
        "➕ <b>Добавление нового рецепта</b>\n\n"
        "📝 Введите ID рецепта для регистрации:",
        reply_markup=get_cancel_button(),
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_recipe_id)


@router.message(AddRecipeStates.waiting_for_recipe_id)
async def process_recipe_id_add(
    message: Message, 
    state: FSMContext,
    db_pool: Annotated[asyncpg.Pool, "db_pool"]
):
    if message.text == "❌ Отмена" or message.text == "🔙 В меню":
        await state.clear()
        await message.answer(
            "❌ Добавление отменено." if message.text == "❌ Отмена" else "",
            reply_markup=get_main_menu()
        )
        return

    recipe_id = message.text.strip()

    if not recipe_id:
        await message.answer("⚠️ Пожалуйста, введите корректный ID рецепта:")
        return

    pool = db_pool

    if await is_duplicate(recipe_id, pool):
        await state.clear()
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            f"Рецепт с ID <code>{recipe_id}</code> уже зарегистрирован в базе.\n\n"
            "🔒 Повторная выдача запрещена.",
            reply_markup=get_back_to_menu_button(),
            parse_mode="HTML"
        )
        return

    await state.update_data(recipe_id=recipe_id)
    await message.answer(
        "💬 <b>Добавить комментарий?</b>\n\n"
        "Напишите комментарий или нажмите «Пропустить комментарий»:",
        reply_markup=get_skip_button(),
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_comment)


@router.message(AddRecipeStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    if message.text == "❌ Отмена" or message.text == "🔙 В меню":
        await state.clear()
        await message.answer(
            "❌ Добавление отменено." if message.text == "❌ Отмена" else "",
            reply_markup=get_main_menu()
        )
        return

    data = await state.get_data()
    recipe_id = data.get('recipe_id')

    comment = None
    if message.text and message.text != "⏭️ Пропустить комментарий":
        comment = message.text.strip()

    await state.update_data(comment=comment)
    
    preview_text = (
        "📋 <b>Предпросмотр рецепта</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID рецепта:</b> <code>{recipe_id}</code>\n"
        f"💬 <b>Комментарий:</b> {comment if comment else '<i>Нет комментария</i>'}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ <b>Подтвердите сохранение:</b>"
    )
    
    await message.answer(
        preview_text,
        reply_markup=get_confirm_buttons(),
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_confirmation)


@router.message(AddRecipeStates.waiting_for_confirmation)
async def process_confirmation(
    message: Message, 
    state: FSMContext,
    db_pool: Annotated[asyncpg.Pool, "db_pool"]
):
    if message.text == "🔙 В меню" or message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "❌ Добавление отменено.",
            reply_markup=get_main_menu()
        )
        return

    if message.text == "✅ Сохранить":
        data = await state.get_data()
        recipe_id = data.get('recipe_id')
        comment = data.get('comment')
        user_id = message.from_user.id
        username = message.from_user.username

        pool = db_pool

        try:
            await add_recipe(recipe_id, user_id, comment, username, pool)
            await message.answer(
                "✅ <b>Рецепт успешно сохранён!</b>\n\n"
                "🔒 Повторная выдача по этому рецепту запрещена.",
                reply_markup=get_back_to_menu_button(),
                parse_mode="HTML"
            )
        except Exception as e:
            await message.answer(
                f"❌ Ошибка: не удалось сохранить рецепт.\n"
                f"Возможно, он уже существует или произошла ошибка базы данных.",
                reply_markup=get_back_to_menu_button()
            )
    else:
        await message.answer(
            "⚠️ Пожалуйста, выберите действие:",
            reply_markup=get_confirm_buttons()
        )
        return

    await state.clear()
