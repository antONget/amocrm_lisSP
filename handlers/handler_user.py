from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from amocrm.v2 import tokens, Lead, Contact
from amocrm.v2.exceptions import AmoApiException
from config_data.config import Config, load_config
import keyboards.keyboard_user as kb
from filter.filter import validate_russian_phone_number
import logging


router = Router()
config: Config = load_config()


class Stage(StatesGroup):
    name = State()
    phone = State()


# def amocrm_authorize():
#     tokens.default_token_manager(
#         client_id=config.tg_bot.amocrm_client_id,
#         client_secret=config.tg_bot.amocrm_client_secret,
#         subdomain=config.tg_bot.amocrm_subdomain,
#         redirect_url=config.tg_bot.amocrm_redirect_irl,
#         storage=tokens.FileTokensStorage(),  # Использование хранения токенов в файле
#     )
#
# # Вызываем функцию авторизации при запуске
# amocrm_authorize()
async def create_lead_in_amocrm(name, phone, product):
    logging.info("create_lead_in_amocrm")
    try:
        # Создание контакта
        contact = Contact.objects.create(
            first_name=name,
            custom_fields_values=[
                {
                    "field_code": "PHONE",
                    "values": [{"value": phone}]
                }
            ]
        )

        # Создание лида
        lead = Lead.objects.create(
            name=f"Лид от {name}",
            contacts=[contact],
            custom_fields_values=[
                {
                    "field_code": "PRODUCT",
                    "values": [{"value": product}]
                }
            ]
        )

        logging.info(f"Создан новый лид: {lead.id} для контакта: {contact.id}")
        return True

    except AmoApiException as e:
        logging.error(f"Ошибка API amoCRM при создании лида: {e}")
        return False
    except Exception as e:
        logging.error(f"Неожиданная ошибка при создании лида: {e}")
        return False


@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Запуск бота - нажата кнопка "Начать" или введена команда "/start"
    :param message:
    :param state:
    :param bot:
    :return:
    """
    logging.info(f"process_start_command {message.chat.id}")
    await state.set_state(default_state)
    await message.answer(text=f'Давайте познакомимся. Скажите, как Вас зовут?')
    await state.set_state(Stage.name)


@router.message(F.text, Stage.name)
async def get_username(message: Message, state: FSMContext):
    """
    Получаем имя пользователя. Запрашиваем номер телефона
    :param message:
    :param state:
    :return:
    """
    logging.info(f'anketa_get_username: {message.from_user.id}')
    name = message.text
    await state.update_data(name=name)
    await message.answer(text=f'Рад вас приветствовать {name}. Какой товар у нас приобрели?',
                         reply_markup=kb.keyboard_product())
    await state.set_state(default_state)


@router.message(lambda message: message.text in ["Тетрадь Пиши-стирай", "Лепим из пластилина тетрадь", "Вырезалки",
                                                 "Раскраску", "Игру на липучках", "Прописи"])
async def process_select_product(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Выбор продукта
    :param message:
    :param state:
    :param bot:
    :return:
    """
    logging.info("process_select_product")
    await state.update_data(product=message.text)
    if message.text == 'Игру на липучках':
        await message.answer_video(video='BAACAgIAAxkBAAMlZuGlVM-cyHUF95jPTGeYiJYufkoAAm1WAAK6nAlLWOty_-bYzzA2BA')
    await message.answer(text=f'Согласны на отправку персональных данных?',
                         reply_markup=kb.keyboard_agree())


@router.callback_query(F.data.startswith('agree_'))
async def process_select_product(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.message.answer(text=f'Поделитесь вашим номером телефона ☎️',
                                  reply_markup=kb.keyboards_get_contact())
    await state.set_state(Stage.phone)
    await callback.answer()


@router.message(or_f(F.text, F.contact), StateFilter(Stage.phone))
async def process_validate_russian_phone_number(message: Message, state: FSMContext, bot: Bot) -> None:
    """Получаем номер телефона пользователя (проводим его валидацию). Подтверждаем введенные данные"""
    logging.info("process_start_command_user")
    if message.contact:
        phone = str(message.contact.phone_number)
    else:
        phone = message.text
        if not validate_russian_phone_number(phone):
            await message.answer(text="Неверный формат номера. Повторите ввод, например 89991112222:")
            return
    await state.update_data(phone=phone)
    await state.set_state(default_state)
    data = await state.get_data()
    for admin in config.tg_bot.admin_ids.split(','):
        try:
            await bot.send_message(chat_id=admin,
                                   text=f'Пользователь @{message.from_user.username} отправил данные:\n\n'
                                        f'<b>Имя</b>: {data["name"]}\n'
                                        f'<b>Телефон</b>: {data["phone"]}\n'
                                        f'<b>Продукт</b>: {data["product"]}\n')
        except:
            pass
    await create_lead_in_amocrm(name=data['name'], phone=data['phone'], product=data['product'])
    await message.answer(text='Данные успешно отправлены',
                         reply_markup=ReplyKeyboardRemove())
