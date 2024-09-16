from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    admin_ids: str
    support_id: int
    support_username: str

    amocrm_client_id: str
    amocrm_client_secret: str
    amocrm_redirect_irl: str
    amocrm_subdomain: str
    # amocrm_access_token: str
    # amocrm_refresh_token: str


@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(tg_bot=TgBot(token=env('BOT_TOKEN'),
                               admin_ids=env('ADMIN_IDS'),
                               support_id=env('SUPPORT_ID'),
                               support_username=env('SUPPORT_USERNAME'),
                               amocrm_client_id=env('AMOCRM_CLIENT_ID'),
                               amocrm_client_secret=env('AMOCRM_CLIENT_SECRET'),
                               amocrm_redirect_irl=env('AMOCRM_REDIRECT_URL'),
                               amocrm_subdomain=env('AMOCRM_SUBDOMAIN'))
                  )
