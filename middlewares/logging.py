import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех апдейтов"""
    
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        """Логирование информации об апдейте"""
        
        # Получаем информацию о пользователе
        user_id = None
        username = None
        update_type = type(event).__name__
        text = ""
        
        # В aiogram 3 event уже является конкретным типом (Message, CallbackQuery и т.д.)
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            username = event.from_user.username if event.from_user else None
            text = event.text or event.caption or ""
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            username = event.from_user.username if event.from_user else None
            text = event.data or ""
        
        # Формируем сообщение для лога
        log_message = (
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"User: {user_id} (@{username}) | "
            f"Type: {update_type} | "
            f"Text: {text[:100]}"  # Ограничиваем длину текста
        )
        
        logger.info(log_message)
        
        # Вызываем следующий handler
        return await handler(event, data)
