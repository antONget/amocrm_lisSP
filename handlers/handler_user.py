from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from amocrm.v2 import Lead, Contact
from amocrm.v2.exceptions import AmoApiException
from config_data.config import Config, load_config
import keyboards.keyboard_user as kb
from filter.filter import validate_russian_phone_number
from filter.admin_filter import IsSuperAdmin
import logging
from database import requests as rq

router = Router()
config: Config = load_config()


class Stage(StatesGroup):
    name = State()
    phone = State()
    content = State()


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
                },
            ]
        )
        # Создание лида
        lead = Lead.objects.create(
            name=f"Лид от {name}",
            contacts=[contact.id],
            custom_fields_values=[
                {
                    "field_id": 1117555,
                    "values": [{"value": str(product)}]
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


@router.message(F.text == '/send_content', IsSuperAdmin())
async def send_content(message: Message, state: FSMContext):
    await message.answer(text='Пришлите контент для рассылки')
    await state.set_state(Stage.content)


@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext) -> None:
    """
    Запуск бота - нажата кнопка "Начать" или введена команда "/start"
    :param message:
    :param state:
    :return:
    """
    logging.info(f"process_start_command {message.chat.id}")
    await rq.add_user(tg_id=message.chat.id, data={"tg_id": message.chat.id,
                                                   "username": message.from_user.username})
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
    await message.answer(text=f'Рад вас приветствовать, {name}. Какой товар у нас приобрели?',
                         reply_markup=kb.keyboard_product())
    await state.set_state(default_state)


@router.message(lambda message: message.text in [
                                                    "Пиши-стирай",
                                                    "Пальчиковая раскраска",
                                                    "Прописи",
                                                    "Игру на липучках",
                                                    "Тактильная книга",
                                                    "Вырезалки",
                                                    "Книга с окошками",
                                                    "Развитие речи"
                                                ])
async def process_select_product(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Выбор продукта
    :param message:
    :param state:
    :return:
    """
    logging.info("process_select_product")
    await state.update_data(product=message.text)
    await message.answer(text='Хотите получать бесплатные материалы от нас?',
                         reply_markup=ReplyKeyboardRemove())
    await bot.delete_message(chat_id=message.chat.id,
                             message_id=message.message_id+1)
    if message.text == 'Игру на липучках':
        await message.answer_video(video='BAACAgIAAxkBAAMlZuGlVM-cyHUF95jPTGeYiJYufkoAAm1WAAK6nAlLWOty_-bYzzA2BA')
    await message.answer(text=f'Супер🎉\n'
                              f'Хотите получать бесплатные материалы от нас?',
                         reply_markup=kb.keyboard_agree())


@router.callback_query(F.data.startswith('agree_'))
async def process_select_product(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    answer = callback.data.split('_')[1]
    if answer == 'yes':
        await bot.delete_message(chat_id=callback.message.chat.id,
                                 message_id=callback.message.message_id)
        await callback.message.answer(text=f'Поделитесь вашим номером телефона ☎️',
                                      reply_markup=kb.keyboards_get_contact())
        await state.set_state(Stage.phone)
    else:
        try:
            await callback.message.edit_text(text='К сожалению, без Вашего согласия мы не сможем отправить'
                                                  ' бесплатные материалы\n\n'
                                                  'Согласны на отправку персональных данных?',
                                             reply_markup=kb.keyboard_agree())
        except:
            await callback.message.edit_text(text='К сожалению, без Вашего согласия мы не сможем отправить'
                                                  ' бесплатные материалы\n\n'
                                                  'Согласны на отправку персональных данных?',
                                             reply_markup=kb.keyboard_agree())
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
    await message.answer(text='Связаться с нами и задать свой вопрос можно здесь',
                         reply_markup=kb.keyboard_manager())


@router.message(StateFilter(Stage.content))
async def get_content(message: Message, state: FSMContext):
    if message.photo:
        id_photo = message.photo[-1].file_id
        caption = message.caption
        await state.update_data(id_photo=id_photo)
        await state.update_data(caption=caption)
        await state.update_data(send_content='send_content')
    else:
        send_content = message.html_text
        await state.update_data(id_photo='id_photo')
        await state.update_data(caption='caption')
        await state.update_data(send_content=send_content)
    await state.set_state(default_state)
    await message.answer(text='Разослать контент?',
                         reply_markup=kb.keyboard_content())


@router.callback_query(F.data.startswith('content'))
async def send_content(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    list_users = await rq.get_all_users()
    answer = callback.data.split('_')[1]
    if answer == 'yes':
        data = await state.get_data()
        id_photo = data['id_photo']
        caption = data['caption']
        send_content = data['send_content']
        await bot.delete_message(chat_id=callback.message.chat.id,
                                 message_id=callback.message.message_id)
        await callback.message.answer(text=f'Запущена рассылка')
        for user in list_users:
            print(user.tg_id)
            try:
                await bot.send_photo(chat_id=user.tg_id,
                                     photo=id_photo,
                                     caption=caption)
            except:
                print('error')

        for user in list_users:
            try:
                await bot.send_message(chat_id=user.tg_id,
                                       text=send_content)
            except:
                print('error')
    else:
        await bot.delete_message(chat_id=callback.message.chat.id,
                                 message_id=callback.message.message_id)
        await callback.message.answer(text='Рассылка отменена')