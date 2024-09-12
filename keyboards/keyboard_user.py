from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import logging


def keyboard_product():
    logging.info("product_markup")
    builder = ReplyKeyboardBuilder()
    products = [
        "Тетрадь Пиши-стирай",
        "Лепим из пластилина тетрадь",
        "Вырезалки",
        "Раскраску",
        "Игру на липучках",
        "Прописи"
    ]
    for product in products:
        builder.button(text=product)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def keyboard_agree() -> InlineKeyboardMarkup:
    logging.info("keyboard_agree")
    button_1 = InlineKeyboardButton(text='Да', callback_data=f'agree_yes')
    button_2 = InlineKeyboardButton(text='Нет', callback_data=f'agree_no')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_1], [button_2]],)
    return keyboard


def keyboards_get_contact() -> ReplyKeyboardMarkup:
    logging.info("keyboards_get_contact")
    button_1 = KeyboardButton(text='Отправить свой контакт ☎️',
                              request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button_1]],
        resize_keyboard=True
    )
    return keyboard