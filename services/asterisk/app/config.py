from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOXALIA_ASTERISK_")

    database_url: str
    service_name: str = "voxalia-asterisk"


@lru_cache
def get_settings() -> Settings:
    return Settings()
