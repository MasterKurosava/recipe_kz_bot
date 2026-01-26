from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Annotated
import asyncpg
import re
import logging
from services.recipe_service import create_recipe, add_recipe_item, get_recipe_by_id, get_recipes_by_doctor, update_recipe_item_quantity, is_duplicate
from keyboards.common import get_duration_keyboard, get_recipe_items_actions_keyboard, get_confirm_keyboard, get_item_delete_keyboard, get_doctor_recipe_actions_keyboard, get_item_edit_keyboard
from utils.recipe_formatter import format_recipe_detail, format_recipe_logs
from utils.message_splitter import split_long_message

router = Router()


class AddRecipeStates(StatesGroup):
    waiting_for_recipe_id = State()
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
        "📝 Введите ID рецепта:",
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_recipe_id)


@router.message(AddRecipeStates.waiting_for_recipe_id)
async def process_recipe_id(message: Message, state: FSMContext, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    # Обрабатываем команды отмены
    if message.text and message.text.strip() in ["/cancel", "❌ Отмена", "🔙 В меню", "/start"]:
        await state.clear()
        from keyboards.common import get_role_menu
        await message.answer("❌ Добавление рецепта отменено.", reply_markup=get_role_menu("doctor"))
        return
    
    if not message.text:
        await message.answer("⚠️ Пожалуйста, введите ID рецепта текстом:")
        return
    
    recipe_id = message.text.strip()
    
    if not recipe_id:
        await message.answer("⚠️ Пожалуйста, введите корректный ID рецепта:")
        return
    
    try:
        is_dup = await is_duplicate(recipe_id, db_pool)
        if is_dup:
            await message.answer(
                f"❌ <b>Ошибка!</b>\n\n"
                f"Рецепт с ID <code>{recipe_id}</code> уже зарегистрирован в базе.\n\n"
                "🔒 Повторная выдача запрещена.",
                parse_mode="HTML"
            )
            await state.clear()
            return
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке ID рецепта: {str(e)}")
        return
    
    await state.update_data(recipe_id=recipe_id)
    await message.answer(
        "📝 Введите название первого препарата:",
        parse_mode="HTML"
    )
    await state.set_state(AddRecipeStates.waiting_for_drug_name)


@router.message(AddRecipeStates.waiting_for_drug_name)
async def process_drug_name(message: Message, state: FSMContext, user: dict):
    # Обрабатываем команды отмены
    if message.text and message.text.strip() in ["/cancel", "❌ Отмена", "🔙 В меню", "/start", "Отменить рецепт"]:
        await state.clear()
        from keyboards.common import get_role_menu
        await message.answer("❌ Создание рецепта отменено.", reply_markup=get_role_menu(user['role']))
        return
    
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
async def process_quantity(message: Message, state: FSMContext, user: dict):
    # Обрабатываем команды отмены
    if message.text and message.text.strip() in ["/cancel", "❌ Отмена", "🔙 В меню", "/start", "Отменить рецепт"]:
        await state.clear()
        from keyboards.common import get_role_menu
        await message.answer("❌ Создание рецепта отменено.", reply_markup=get_role_menu(user['role']))
        return
    
    if not message.text:
        await message.answer("⚠️ Пожалуйста, введите количество:")
        return
    
    text = message.text.strip()
    
    if not text:
        await message.answer("⚠️ Пожалуйста, введите количество:")
        return
    
    # Позволяем вводить любой текст, включая буквы
    quantity = text
    
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


@router.callback_query(F.data == "cancel_recipe_creation", AddRecipeStates.waiting_for_more_items)
async def cancel_recipe_creation(callback: CallbackQuery, state: FSMContext, user: dict):
    from keyboards.common import get_role_menu
    await callback.message.delete()
    await callback.message.answer(
        "❌ Создание рецепта отменено",
        reply_markup=get_role_menu(user['role'])
    )
    await state.clear()
    await callback.answer()


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
    
    from utils.date_formatter import format_duration_days
    duration_days = data.get('duration_days', 0)
    duration_text = format_duration_days(duration_days)
    
    confirmation_text = (
        "📋 <b>Предпросмотр рецепта</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💊 <b>Препараты:</b>\n{items_text}\n\n"
        f"⏱ <b>Длительность:</b> {duration_text}\n"
    )
    
    if data.get('comment'):
        confirmation_text += f"💬 <b>Комментарий:</b> {data['comment']}\n"
    
    confirmation_text += "━━━━━━━━━━━━━━━━━━━━\n\nПодтвердите создание рецепта:"
    
    # Устанавливаем состояние перед показом подтверждения
    await state.set_state(AddRecipeStates.waiting_for_confirmation)
    
    if isinstance(message, Message):
        await message.answer(confirmation_text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text(confirmation_text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_recipe", AddRecipeStates.waiting_for_confirmation)
async def confirm_recipe(callback: CallbackQuery, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    logger = logging.getLogger(__name__)
    
    # Сразу отвечаем на callback, чтобы убрать индикатор загрузки
    await callback.answer()
    
    # Показываем сообщение о сохранении
    await callback.message.edit_text("⏳ Сохранение рецепта...")
    
    data = await state.get_data()
    
    try:
        external_recipe_id = data.get('recipe_id', '')
        comment = data.get('comment', '')
        items = data.get('items', [])
        duration_days = data.get('duration_days')
        
        if not items:
            await callback.message.edit_text("❌ Ошибка: нет препаратов для сохранения")
            await state.clear()
            return
        
        if not duration_days:
            await callback.message.edit_text("❌ Ошибка: не указана длительность рецепта")
            await state.clear()
            return
        
        # Добавляем внешний ID рецепта в начало комментария, если он есть
        if external_recipe_id:
            if comment:
                comment = f"ID: {external_recipe_id}\n{comment}"
            else:
                comment = f"ID: {external_recipe_id}"
        
        # Преобразуем comment в строку или None (не пустую строку)
        comment_value = comment if comment else None
        
        # Используем одну транзакцию для всех операций
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Создаем рецепт
                # Явно указываем типы: user['id'] (int), duration_days (int), comment (str или None)
                recipe_id = await conn.fetchval(
                    """
                    INSERT INTO recipes (doctor_id, duration_days, comment, status)
                    VALUES ($1::integer, $2::integer, $3::text, 'active')
                    RETURNING id
                    """,
                    int(user['id']), int(duration_days), comment_value
                )
                
                # Добавляем все элементы рецепта в одной транзакции
                for item in items:
                    drug_name = item.get('drug_name', '')
                    quantity = item.get('quantity', '')
                    
                    if not drug_name:
                        continue
                    
                    # Пытаемся преобразовать quantity в число, если не получается - используем 0
                    # Это нужно, так как в БД поле quantity имеет тип INTEGER
                    try:
                        if quantity is None or quantity == '':
                            quantity_value = 0
                        elif isinstance(quantity, (int, float)):
                            quantity_value = int(quantity)
                        elif isinstance(quantity, str):
                            # Пытаемся извлечь число из строки
                            numbers = re.findall(r'\d+', str(quantity))
                            quantity_value = int(numbers[0]) if numbers else 0
                        else:
                            quantity_value = 0
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Не удалось преобразовать quantity '{quantity}' в число: {e}")
                        quantity_value = 0
                    
                    try:
                        await conn.execute(
                            "INSERT INTO recipe_items (recipe_id, drug_name, quantity) VALUES ($1::integer, $2::text, $3::integer)",
                            int(recipe_id), str(drug_name), int(quantity_value)
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении элемента рецепта: {e}")
                        raise
        
        message_text = f"✅ <b>Рецепт успешно создан!</b>\n\n"
        if external_recipe_id:
            message_text += f"🆔 <b>Внешний ID рецепта:</b> <code>{external_recipe_id}</code>\n"
        message_text += f"🆔 <b>ID в базе:</b> <code>{recipe_id}</code>\n\n"
        message_text += "Рецепт сохранён в базу данных."
        
        await callback.message.edit_text(message_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при создании рецепта: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при создании рецепта: {str(e)}\n\n"
            "Попробуйте создать рецепт заново."
        )
    
    await state.clear()


@router.callback_query(F.data == "cancel_recipe", AddRecipeStates.waiting_for_confirmation)
async def cancel_recipe(callback: CallbackQuery, state: FSMContext, user: dict):
    from keyboards.common import get_role_menu
    await callback.message.delete()
    await callback.message.answer(
        "❌ Создание рецепта отменено",
        reply_markup=get_role_menu(user['role'])
    )
    await state.clear()
    await callback.answer()


class DoctorRecipeStates(StatesGroup):
    waiting_for_recipe_id = State()
    waiting_for_edit_quantity = State()


@router.message(F.text == "📋 Мои рецепты")
async def cmd_my_recipes(message: Message, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipes = await get_recipes_by_doctor(user['id'], db_pool)
    
    if not recipes:
        await message.answer("📭 У вас пока нет рецептов", parse_mode="HTML")
        return
    
    text = f"📋 <b>Мои рецепты (всего {len(recipes)})</b>\n\n"
    
    from utils.date_formatter import format_datetime, format_duration_days
    from utils.recipe_formatter import format_recipe_status
    
    for recipe in recipes[:20]:
        status_emoji, status_text = format_recipe_status(recipe)
        duration_text = format_duration_days(recipe['duration_days'])
        
        text += f"{status_emoji} <b>Рецепт #{recipe['id']}</b>\n"
        text += f"📅 Дата: {format_datetime(recipe['created_at'])}\n"
        text += f"⏱ Длительность: {duration_text}\n"
        text += f"📊 Статус: {status_text}\n"
        text += f"💊 Препараты: {len(recipe['items'])}\n\n"
    
    if len(recipes) > 20:
        text += f"... и ещё {len(recipes) - 20} рецептов\n\n"
    
    text += "📝 Введите ID рецепта для просмотра и редактирования:"
    
    chunks = split_long_message(text, max_length=4000)
    for i, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode="HTML" if i == 0 else None
        )
    
    await message.answer("📝 Введите ID рецепта для просмотра и редактирования:", parse_mode="HTML")
    await state.set_state(DoctorRecipeStates.waiting_for_recipe_id)


@router.message(DoctorRecipeStates.waiting_for_recipe_id)
async def process_doctor_recipe_id(message: Message, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
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
    
    if recipe['doctor_id'] != user['id']:
        await message.answer("❌ Вы можете просматривать и редактировать только свои рецепты", parse_mode="HTML")
        await state.clear()
        return
    
    recipe_text = format_recipe_detail(recipe, recipe_id)
    
    if recipe['status'] == 'active':
        await message.answer(
            recipe_text,
            reply_markup=get_doctor_recipe_actions_keyboard(recipe_id),
            parse_mode="HTML"
        )
    else:
        from services.recipe_service import get_recipe_logs
        logs = await get_recipe_logs(recipe_id, db_pool)
        recipe_text += format_recipe_logs(logs)
        await message.answer(recipe_text, parse_mode="HTML")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_quantity_"))
async def doctor_edit_quantity_select(callback: CallbackQuery, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipe_id = int(callback.data.split("_")[-1])
    
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    
    if recipe['doctor_id'] != user['id']:
        await callback.answer("❌ Вы можете редактировать только свои рецепты", show_alert=True)
        return
    
    if recipe['status'] != 'active':
        await callback.answer("❌ Нельзя редактировать списанный рецепт", show_alert=True)
        return
    
    await state.update_data(recipe_id=recipe_id)
    
    await callback.message.edit_text(
        "✏️ <b>Выберите препарат для изменения количества:</b>",
        reply_markup=get_item_edit_keyboard(recipe_id, recipe['items']),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_item_"))
async def doctor_edit_item_start(callback: CallbackQuery, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    parts = callback.data.split("_")
    recipe_id = int(parts[2])
    item_id = int(parts[3])
    
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    if not recipe or recipe['doctor_id'] != user['id']:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    if recipe['status'] != 'active':
        await callback.answer("❌ Нельзя редактировать списанный рецепт", show_alert=True)
        return
    
    await state.update_data(recipe_id=recipe_id, item_id=item_id)
    await callback.message.edit_text("✏️ Введите новое количество:")
    await state.set_state(DoctorRecipeStates.waiting_for_edit_quantity)
    await callback.answer()


@router.message(DoctorRecipeStates.waiting_for_edit_quantity)
async def doctor_process_new_quantity(message: Message, state: FSMContext, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    if not message.text:
        await message.answer("⚠️ Пожалуйста, введите количество:")
        return
    
    # Позволяем вводить любой текст, включая буквы
    new_quantity = message.text.strip()
    
    data = await state.get_data()
    recipe_id = data['recipe_id']
    item_id = data['item_id']
    
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    if not recipe or recipe['doctor_id'] != user['id']:
        await message.answer("❌ Вы можете редактировать только свои рецепты")
        await state.clear()
        return
    
    if recipe['status'] != 'active':
        await message.answer("❌ Нельзя редактировать списанный рецепт")
        await state.clear()
        return
    
    try:
        await update_recipe_item_quantity(item_id, new_quantity, user['id'], recipe_id, db_pool)
        
        recipe = await get_recipe_by_id(recipe_id, db_pool)
        recipe_text = format_recipe_detail(recipe, recipe_id)
        
        await message.answer(
            f"✅ <b>Количество обновлено!</b>\n\n{recipe_text}",
            reply_markup=get_doctor_recipe_actions_keyboard(recipe_id) if recipe['status'] == 'active' else None,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data.startswith("back_recipe_"))
async def doctor_back_to_recipe(callback: CallbackQuery, user: dict, db_pool: Annotated[asyncpg.Pool, "db_pool"]):
    recipe_id = int(callback.data.split("_")[-1])
    recipe = await get_recipe_by_id(recipe_id, db_pool)
    
    if not recipe:
        await callback.answer("Рецепт не найден", show_alert=True)
        return
    
    if recipe['doctor_id'] != user['id']:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    recipe_text = format_recipe_detail(recipe, recipe_id)
    
    await callback.message.edit_text(
        recipe_text,
        reply_markup=get_doctor_recipe_actions_keyboard(recipe_id) if recipe['status'] == 'active' else None,
        parse_mode="HTML"
    )
    await callback.answer()
