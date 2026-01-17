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
    """Запуск health check сервера в отдельном потоке"""
    async def init_app():
        app = web.Application()
        app.router.add_get("/", healthcheck)
        app.router.add_get("/health", healthcheck)
        return app
    
    async def run_server():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        print("Health check server started on port 8080")
        # Держим сервер запущенным
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
    
    # Создаём новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

# Запускаем сервер-заглушку для health checks
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
