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
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import TCPServer

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Простой HTTP handler для health checks"""
    def do_GET(self):
        if self.path in ('/', '/health'):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Отключаем логирование HTTP запросов
        pass

def run_health_server():
    """Запуск простого HTTP сервера для health checks"""
    try:
        # Используем TCPServer с reuse_address=True
        server = TCPServer(("0.0.0.0", 8080), HealthCheckHandler, bind_and_activate=False)
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        server.serve_forever()
    except Exception as e:
        print(f"Health server error: {e}", file=sys.stderr)
        # Не падаем, просто не работаем health checks

# Запускаем health server в отдельном потоке
health_thread = threading.Thread(target=run_health_server, daemon=True, name="HealthServer")
health_thread.start()


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
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}", exc_info=True)
        raise
    finally:
        logger.info("Завершение работы бота...")
        await db.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
