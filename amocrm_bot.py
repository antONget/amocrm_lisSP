from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from handlers import handler_user
from config_data.config import Config, load_config

import asyncio
import logging
import traceback
from amocrm.v2 import tokens, Lead, Contact
from amocrm.v2.exceptions import AmoApiException

logger = logging.getLogger(__name__)


# Функция конфигурирования и запуска бота
async def main():
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        # filename="py_log.log",
        # filemode='w',
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info('Бот запущен...')

    # Загружаем конфиг в переменную config
    config: Config = load_config()

    def amocrm_authorize():
        tokens.default_token_manager(
            client_id=config.tg_bot.amocrm_client_id,
            client_secret=config.tg_bot.amocrm_client_secret,
            subdomain=config.tg_bot.amocrm_subdomain,
            redirect_url=config.tg_bot.amocrm_redirect_irl,
            storage=tokens.FileTokensStorage(),  # Использование хранения токенов в файле
        )

    # Вызываем функцию авторизации при запуске
    amocrm_authorize()
    # Инициализируем бот и диспетчер
    bot = Bot(token=config.tg_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрируем router в диспетчере
    dp.include_router(handler_user.router)

    @dp.error()
    async def error_handler(event: ErrorEvent):
        logger.critical("Критическая ошибка: %s", event.exception, exc_info=True)
        await bot.send_message(chat_id=config.tg_bot.support_id,
                               text=f'{event.exception}')
        formatted_lines = traceback.format_exc()
        text_file = open('error.txt', 'w')
        text_file.write(str(formatted_lines))
        text_file.close()
        await bot.send_document(chat_id=config.tg_bot.support_id,
                                document=FSInputFile('error.txt'))
    # Пропускаем накопившиеся update и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())