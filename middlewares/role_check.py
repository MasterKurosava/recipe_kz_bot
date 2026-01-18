from typing import List, Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from services.user_service import get_user_by_telegram_id
import asyncpg


class RoleCheckMiddleware(BaseMiddleware):
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        pool: asyncpg.Pool = data.get("db_pool")
        
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        else:
            return await handler(event, data)

        if not user_id or not pool:
            return await handler(event, data)

        user = await get_user_by_telegram_id(user_id, pool)

        if not user or user['role'] not in self.allowed_roles:
            if isinstance(event, Message):
                await event.answer(
                    "🚫 <b>Доступ запрещён</b>\n\n"
                    "Бот доступен только для авторизованных пользователей.\n"
                    "Свяжитесь с администратором: @admin1 или @admin2",
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещён", show_alert=True)
            return

        data['user'] = user
        return await handler(event, data)
