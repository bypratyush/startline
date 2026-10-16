"""Runtime configuration, read from environment variables.

In Kubernetes the non-secret values come from a ConfigMap and DB_PASSWORD from a
Secret, so nothing environment-specific is baked into the image.
"""

import os
from datetime import date
from urllib.parse import quote_plus


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "StartLine")
        self.app_env = os.getenv("APP_ENV", "local")
        self.app_version = os.getenv("APP_VERSION", "dev")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", "startline")
        self.db_user = os.getenv("DB_USER", "startline")
        self.db_password = os.getenv("DB_PASSWORD", "")
        # DATABASE_URL wins if set (tests use SQLite through it)
        self._database_url = os.getenv("DATABASE_URL", "")

        # The React app is served from the same origin in Docker and Kubernetes;
        # CORS only matters for the Vite dev server.
        self.cors_origins = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o]

        # Pin "today" for demos and tests; empty means the real date.
        self._today = os.getenv("STARTLINE_TODAY", "")

    @property
    def database_url(self) -> str:
        if self._database_url:
            return self._database_url
        return (
            f"postgresql+psycopg://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def today(self) -> date:
        if self._today:
            return date.fromisoformat(self._today)
        return date.today()


settings = Settings()
