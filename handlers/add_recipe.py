from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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
    """Начало добавления рецепта"""
    await message.answer(
        "➕ Введите ID рецепта для регистрации:",
        reply_markup=get_cancel_button()
    )
    await state.set_state(AddRecipeStates.waiting_for_recipe_id)


@router.message(AddRecipeStates.waiting_for_recipe_id)
async def process_recipe_id_add(message: Message, state: FSMContext):
    """Обработка введённого ID рецепта для добавления"""
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

    # Получаем pool из bot data
    pool: asyncpg.Pool = message.bot["db_pool"]

    # Проверяем, не существует ли уже такой рецепт
    if await is_duplicate(recipe_id, pool):
        await state.clear()
        await message.answer(
            "❌ Ошибка: рецепт с таким ID уже зарегистрирован в базе.",
            reply_markup=get_back_to_menu_button()
        )
        return

    # Сохраняем ID и переходим к комментарию
    await state.update_data(recipe_id=recipe_id)
    await message.answer(
        "💬 Добавить комментарий?\n(Или нажмите «Пропустить комментарий»):",
        reply_markup=get_skip_button()
    )
    await state.set_state(AddRecipeStates.waiting_for_comment)


@router.message(AddRecipeStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработка комментария или пропуска"""
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

    # Сохраняем комментарий в состояние и показываем предпросмотр
    await state.update_data(comment=comment)
    
    # Формируем предпросмотр
    preview_text = f"📋 Предпросмотр рецепта:\n\n"
    preview_text += f"ID: {recipe_id}\n"
    preview_text += f"Комментарий: {comment if comment else 'Нет комментария'}\n\n"
    preview_text += f"Подтвердите сохранение:"
    
    await message.answer(
        preview_text,
        reply_markup=get_confirm_buttons()
    )
    await state.set_state(AddRecipeStates.waiting_for_confirmation)


@router.message(AddRecipeStates.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения сохранения"""
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

        # Получаем pool из bot data
        pool: asyncpg.Pool = message.bot.get("db_pool")

        try:
            # Сохраняем рецепт в базу
            await add_recipe(recipe_id, user_id, comment, pool)
            await message.answer(
                "✅ Рецепт сохранён, повторная выдача запрещена.",
                reply_markup=get_back_to_menu_button()
            )
        except Exception as e:
            # Обработка ошибок (например, если рецепт был добавлен между проверкой и сохранением)
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
