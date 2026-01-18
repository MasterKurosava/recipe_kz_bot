from typing import Optional
from aiogram.types import Message, CallbackQuery


def extract_user_id(event: Message | CallbackQuery) -> Optional[int]:
    if isinstance(event, Message):
        return event.from_user.id if event.from_user else None
    elif isinstance(event, CallbackQuery):
        return event.from_user.id if event.from_user else None
    return None


def extract_user_info(event: Message | CallbackQuery) -> tuple[str, Optional[str], Optional[int]]:
    user_full_name = event.from_user.full_name if event.from_user else "Пользователь"
    user_username = event.from_user.username if event.from_user and event.from_user.username else None
    user_id = event.from_user.id if event.from_user else None
    return user_full_name, user_username, user_id
