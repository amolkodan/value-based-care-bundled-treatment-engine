from __future__ import annotations

import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg2://vbc:vbc@localhost:5432/vbc_claims"
    log_json: bool = False
    require_db_on_startup: bool = False

    aws_region: str = "us-east-1"
    db_secret_arn: str | None = None
    db_secret_json_key: str = "database_url"

    def resolved_database_url(self) -> str:
        """
        Resolve DB URL. In cloud envs, DB URL can be supplied via secret payload
        injected as DB_SECRET_JSON environment variable.
        """
        secret_json = os.getenv("DB_SECRET_JSON")
        if secret_json:
            try:
                payload = json.loads(secret_json)
                value = payload.get(self.db_secret_json_key)
                if isinstance(value, str) and value:
                    return value
            except json.JSONDecodeError:
                pass
        return self.database_url


settings = AppSettings()
