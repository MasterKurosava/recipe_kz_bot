import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update
import asyncpg

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        data["db_pool"] = self.pool
        return await handler(event, data)
