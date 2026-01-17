from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Annotated
from keyboards import get_main_menu, get_cancel_button, get_back_to_menu_button
from services.recipe_service import get_recipe_history
import asyncpg

router = Router()


class HistoryStates(StatesGroup):
    waiting_for_recipe_id = State()


@router.message(F.text == "🕓 История по рецепту")
async def cmd_recipe_history(message: Message, state: FSMContext):
    """Начало получения истории по рецепту"""
    await message.answer(
        "🕓 Введите ID рецепта для просмотра истории:",
        reply_markup=get_cancel_button()
    )
    await state.set_state(HistoryStates.waiting_for_recipe_id)


@router.message(HistoryStates.waiting_for_recipe_id)
async def process_recipe_id_history(
    message: Message, 
    state: FSMContext,
    db_pool: Annotated[asyncpg.Pool, "db_pool"]
):
    """Обработка введённого ID рецепта для истории"""
    if message.text == "❌ Отмена" or message.text == "🔙 В меню":
        await state.clear()
        await message.answer(
            "❌ Просмотр истории отменён." if message.text == "❌ Отмена" else "",
            reply_markup=get_main_menu()
        )
        return

    recipe_id = message.text.strip()

    if not recipe_id:
        await message.answer("⚠️ Пожалуйста, введите корректный ID рецепта:")
        return

    # Получаем pool из middleware data
    pool = db_pool

    # Получаем историю рецепта
    history = await get_recipe_history(recipe_id, pool)

    if not history:
        await message.answer(
            f"📭 История по рецепту `{recipe_id}` не найдена.",
            reply_markup=get_back_to_menu_button(),
            parse_mode="Markdown"
        )
    else:
        # Формируем сообщение с историей
        history_text = f"📋 История по рецепту: `{recipe_id}`\n\n"
        
        for i, record in enumerate(history, 1):
            date_str = record['created_at'].strftime("%d.%m.%Y %H:%M")
            comment = record['comment'] if record['comment'] else "Нет комментария"
            user_id = record['user_id']
            
            history_text += f"📌 Запись #{i}\n"
            history_text += f"📅 Дата: {date_str}\n"
            history_text += f"💬 Комментарий: {comment}\n"
            history_text += f"👤 Внёс: {user_id}\n\n"

        # Telegram имеет лимит на длину сообщения (4096 символов)
        if len(history_text) > 4096:
            # Разбиваем на части
            chunks = []
            current_chunk = ""
            for line in history_text.split('\n'):
                if len(current_chunk + line + '\n') > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            if current_chunk:
                chunks.append(current_chunk)
            
            for chunk in chunks:
                await message.answer(
                    chunk,
                    reply_markup=get_back_to_menu_button() if chunk == chunks[-1] else None,
                    parse_mode="Markdown"
                )
        else:
            await message.answer(
                history_text,
                reply_markup=get_back_to_menu_button(),
                parse_mode="Markdown"
            )

    await state.clear()
