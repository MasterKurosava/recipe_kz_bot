from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from keyboards.common import get_role_menu

router = Router()

ROLE_NAMES = {
    'admin': '👑 Администратор',
    'doctor': '👨‍⚕️ Врач',
    'pharmacist': '💊 Фармацевт'
}


@router.message(Command("start"))
async def cmd_start(message: Message, user: dict):
    role_name = ROLE_NAMES.get(user['role'], 'Пользователь')
    await message.answer(
        f"👋 <b>Добро пожаловать, {role_name}!</b>\n\nВыберите действие из меню:",
        reply_markup=get_role_menu(user['role']),
        parse_mode="HTML"
    )
