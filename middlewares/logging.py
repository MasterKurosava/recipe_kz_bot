import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, Update

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех апдейтов"""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Логирование информации об апдейте"""
        
        # Получаем информацию о пользователе
        user_id = None
        username = None
        update_type = event.event_type if hasattr(event, 'event_type') else type(event).__name__
        
        if event.message:
            user_id = event.message.from_user.id if event.message.from_user else None
            username = event.message.from_user.username if event.message.from_user else None
            text = event.message.text or event.message.caption or ""
        elif event.callback_query:
            user_id = event.callback_query.from_user.id if event.callback_query.from_user else None
            username = event.callback_query.from_user.username if event.callback_query.from_user else None
            text = event.callback_query.data or ""
        else:
            text = ""
        
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
