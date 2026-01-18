from typing import List, Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from services.user_service import get_users_by_role
from utils.admin_formatter import format_admin_contacts
from utils.messages import get_access_denied_message, get_user_id_message
from utils.user_extractor import extract_user_id, extract_user_info
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
        user = data.get('user')
        
        if not user or user['role'] not in self.allowed_roles:
            if isinstance(event, Message):
                admins = await get_users_by_role('admin', pool)
                admin_text = format_admin_contacts(admins)
                
                user_full_name, user_username, user_id = extract_user_info(event)
                
                await event.answer(
                    get_access_denied_message(admin_text),
                    parse_mode="HTML"
                )
                
                if user_id:
                    await event.answer(
                        get_user_id_message(user_full_name, user_username, user_id),
                        parse_mode="HTML"
                    )
            elif isinstance(event, CallbackQuery):
                if pool:
                    admins = await get_users_by_role('admin', pool)
                    admin_text = format_admin_contacts(admins)
                    
                    await event.message.answer(
                        get_access_denied_message(admin_text),
                        parse_mode="HTML"
                    )
                    
                    user_full_name = event.from_user.full_name if event.from_user else "Пользователь"
                    user_username = event.from_user.username if event.from_user and event.from_user.username else None
                    user_id = event.from_user.id if event.from_user else None
                    
                    if user_id:
                        await event.message.answer(
                            get_user_id_message(user_full_name, user_username, user_id),
                            parse_mode="HTML"
                        )
                
                await event.answer()
            return

        return await handler(event, data)
