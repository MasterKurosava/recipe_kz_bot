import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import db
from handlers import common, check_recipe, add_recipe, recipe_history
from middlewares.logging import LoggingMiddleware
from middlewares.database import DatabaseMiddleware

import threading
from aiohttp import web

async def healthcheck(request):
    return web.Response(text="OK")

def run_health_server():
    app = web.Application()
    app.router.add_get("/", healthcheck)
    web.run_app(app, port=8080)

# Запускаем сервер-заглушку
threading.Thread(target=run_health_server, daemon=True).start()


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция для запуска бота"""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение к базе данных и получение pool
    logger.info("Подключение к базе данных...")
    pool = await db.connect()
    logger.info("База данных подключена")

    # Подключение middleware
    # DatabaseMiddleware должен быть первым, чтобы pool был доступен в других middleware
    dp.message.middleware(DatabaseMiddleware(pool))
    dp.callback_query.middleware(DatabaseMiddleware(pool))
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # Регистрация роутеров (handlers)
    dp.include_router(common.router)
    dp.include_router(check_recipe.router)
    dp.include_router(add_recipe.router)
    dp.include_router(recipe_history.router)

    # Запуск polling
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
