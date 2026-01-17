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
    await message.answer(
        "🕓 <b>Просмотр истории рецепта</b>\n\n"
        "📝 Введите ID рецепта для просмотра истории:",
        reply_markup=get_cancel_button(),
        parse_mode="HTML"
    )
    await state.set_state(HistoryStates.waiting_for_recipe_id)


@router.message(HistoryStates.waiting_for_recipe_id)
async def process_recipe_id_history(
    message: Message, 
    state: FSMContext,
    db_pool: Annotated[asyncpg.Pool, "db_pool"]
):
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

    pool = db_pool

    history = await get_recipe_history(recipe_id, pool)

    if not history:
        await message.answer(
            f"📭 <b>История не найдена</b>\n\n"
            f"🆔 <b>ID рецепта:</b> <code>{recipe_id}</code>\n\n"
            "История по этому рецепту отсутствует.",
            reply_markup=get_back_to_menu_button(),
            parse_mode="HTML"
        )
    else:
        history_text = (
            f"📋 <b>История по рецепту</b>\n"
            f"🆔 <b>ID:</b> <code>{recipe_id}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        for i, record in enumerate(history, 1):
            date_str = record['created_at'].strftime("%d.%m.%Y в %H:%M")
            comment = record['comment'] if record['comment'] else "Нет комментария"
            username = record.get('username')
            user_display = f"@{username}" if username else f"ID: {record['user_id']}"
            
            history_text += (
                f"📌 <b>Запись #{i}</b>\n"
                f"📅 <b>Дата:</b> {date_str}\n"
                f"💬 <b>Комментарий:</b> {comment}\n"
                f"👤 <b>Внёс:</b> {user_display}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
            )

        if len(history_text) > 4096:
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
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                history_text,
                reply_markup=get_back_to_menu_button(),
                parse_mode="HTML"
            )

    await state.clear()
