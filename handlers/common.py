from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Добро пожаловать в бот для управления рецептами!\n\n"
        "Выберите действие из меню:",
        reply_markup=get_main_menu()
    )


@router.message(Command("menu"))
@router.message(F.text == "🔙 В меню")
async def cmd_menu(message: Message, state: FSMContext):
    """Показать главное меню и сбросить FSM"""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия и возврат в главное меню"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=get_main_menu()
    )
