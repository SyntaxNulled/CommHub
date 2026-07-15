from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "CommHub"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8765
    database_url: str = f"sqlite+aiosqlite:///{Path.home() / '.commhub' / 'commhub.db'}"
    data_dir: Path = Path.home() / ".commhub"
    debug: bool = True

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""

    model_config = {"env_prefix": "COMMHUB_"}


settings = Settings()
