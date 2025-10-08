import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from database.database import init_db, async_session_maker
from middlewares.i18n import I18nMiddleware
from middlewares.throttling import ThrottlingMiddleware
from handlers import start, survey

# Настройка логирования (только stdout для хостинга)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=settings.TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    
    # Middleware для внедрения сессии БД
    @dp.update.middleware()
    async def db_session_middleware(handler, event, data):
        async with async_session_maker() as session:
            data['session'] = session
            return await handler(event, data)
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(survey.router)
    
    logger.info("Бот запущен")
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
