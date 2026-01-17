import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update
import asyncpg

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для передачи pool базы данных в handlers"""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Добавляем pool в data для доступа из handlers"""
        data["db_pool"] = self.pool
        return await handler(event, data)
