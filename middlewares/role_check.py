from typing import List, Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
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
        user = data.get('user')
        
        if not user or user['role'] not in self.allowed_roles:
            if isinstance(event, Message):
                await event.answer("🚫 Доступ запрещён", parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.message.answer("🚫 Доступ запрещён", parse_mode="HTML")
                await event.answer()
            return

        return await handler(event, data)
