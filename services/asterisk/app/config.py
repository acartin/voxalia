from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOXALIA_ASTERISK_API_")

    database_url: str
    service_name: str = "voxalia-asterisk"
    render_output_dir: str = "/var/lib/voxalia/asterisk/rendered"
    reload_command: str = ""
    ami_host: str = "voxalia-asterisk-runtime"
    ami_port: int = 5038
    ami_username: str = "voxalia_provisioner"
    ami_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
