from database.models import User
from database.models import async_session
from sqlalchemy import select
import logging


"""USER"""


async def add_user(tg_id: int, data: dict) -> None:
    """
    Добавляем нового пользователя если его еще нет в БД
    :param tg_id:
    :param data:
    :return:
    """
    logging.info(f'add_user')
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        # если пользователя нет в базе
        if not user:
            session.add(User(**data))
            await session.commit()


async def get_all_users() -> list[User]:
    """
    Получаем список всех пользователей зарегистрированных в боте
    :return:
    """
    logging.info(f'get_all_users')
    async with async_session() as session:
        users = await session.scalars(select(User))
        return users