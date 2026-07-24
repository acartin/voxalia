from functools import lru_cache
from os import getenv


class Settings:
    database_url: str
    bootstrap_admin_username: str
    bootstrap_admin_email: str
    bootstrap_admin_password: str

    def __init__(self) -> None:
        self.database_url = getenv("VOXALIA_DATABASE_URL", "")
        self.bootstrap_admin_username = getenv("VOXALIA_BOOTSTRAP_ADMIN_USERNAME", "").strip()
        self.bootstrap_admin_email = getenv("VOXALIA_BOOTSTRAP_ADMIN_EMAIL", "").strip()
        self.bootstrap_admin_password = getenv("VOXALIA_BOOTSTRAP_ADMIN_PASSWORD", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
