from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from services.user_service import get_user_by_telegram_id, get_users_by_role
from utils.admin_formatter import format_admin_contacts
from utils.messages import get_access_denied_message, get_user_id_message
from utils.user_extractor import extract_user_id, extract_user_info
import asyncpg


class UnregisteredUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        pool: asyncpg.Pool = data.get("db_pool")
        user_id = extract_user_id(event)
        
        if not user_id or not pool:
            return await handler(event, data)
        
        user = await get_user_by_telegram_id(user_id, pool)
        
        if not user:
            if isinstance(event, Message):
                admins = await get_users_by_role('admin', pool)
                admin_text = format_admin_contacts(admins)
                
                user_full_name, user_username, _ = extract_user_info(event)
                
                await event.answer(
                    get_access_denied_message(admin_text),
                    parse_mode="HTML"
                )
                
                await event.answer(
                    get_user_id_message(user_full_name, user_username, user_id),
                    parse_mode="HTML"
                )
                return
            elif isinstance(event, CallbackQuery):
                admins = await get_users_by_role('admin', pool)
                admin_text = format_admin_contacts(admins)
                
                user_full_name, user_username, _ = extract_user_info(event)
                
                await event.message.answer(
                    get_access_denied_message(admin_text),
                    parse_mode="HTML"
                )
                
                await event.message.answer(
                    get_user_id_message(user_full_name, user_username, user_id),
                    parse_mode="HTML"
                )
                await event.answer()
                return
        
        data['user'] = user
        return await handler(event, data)
