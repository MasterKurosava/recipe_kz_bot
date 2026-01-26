import asyncio
import logging
import sys
import threading
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from db.database import db
from handlers import common, admin, doctor, pharmacist
from middlewares.database import DatabaseMiddleware
from middlewares.logging import LoggingMiddleware
from middlewares.role_check import RoleCheckMiddleware
from middlewares.unregistered import UnregisteredUserMiddleware

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def healthcheck(request):
    return web.Response(text="OK")


def run_health_server():
    async def init():
        app = web.Application()
        app.router.add_get('/', healthcheck)
        app.router.add_get('/health', healthcheck)
        return app
    
    async def run():
        app = await init()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        print("Health check server started on port 8080")
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


health_thread = threading.Thread(target=run_health_server, daemon=True, name="HealthServer")
health_thread.start()


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    logger.info("Подключение к базе данных...")
    pool = await db.connect()
    logger.info("База данных подключена")

    dp.message.middleware(DatabaseMiddleware(pool))
    dp.callback_query.middleware(DatabaseMiddleware(pool))
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(UnregisteredUserMiddleware())
    dp.callback_query.middleware(UnregisteredUserMiddleware())

    common.router.message.middleware(RoleCheckMiddleware(['admin', 'doctor', 'pharmacist']))
    common.router.callback_query.middleware(RoleCheckMiddleware(['admin', 'doctor', 'pharmacist']))
    admin.router.message.middleware(RoleCheckMiddleware(['admin']))
    admin.router.callback_query.middleware(RoleCheckMiddleware(['admin']))
    doctor.router.message.middleware(RoleCheckMiddleware(['admin', 'doctor']))
    doctor.router.callback_query.middleware(RoleCheckMiddleware(['admin', 'doctor']))
    pharmacist.router.message.middleware(RoleCheckMiddleware(['admin', 'pharmacist']))
    pharmacist.router.callback_query.middleware(RoleCheckMiddleware(['admin', 'pharmacist']))

    dp.include_router(common.router)
    dp.include_router(pharmacist.router)
    dp.include_router(doctor.router)
    dp.include_router(admin.router)

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
