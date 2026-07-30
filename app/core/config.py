from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "FastAPI Users API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    DB_REQUIRED_ON_STARTUP: bool = False

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "redis://127.0.0.1:6379/0"

    RATE_LIMIT_REGISTER: str = "5/hour"
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_FORGOT_PASSWORD: str = "3/hour"

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    FERNET_SECRET_KEY: str
    REPOSITORIES_BASE_PATH: str = "./cloned_repositories"

    REPOSITORY_TEST_DOCKER_IMAGE: str = "python:3.12-slim"
    REPOSITORY_TEST_COMMAND: str = "run-tests"
    REPOSITORY_TEST_INSTALL_COMMAND: str = "install-deps"
    REPOSITORY_UPDATE_INTERVAL_SECONDS: int = 3600
    REPOSITORY_TEST_TIMEOUT_SECONDS: int = 900
    REPOSITORY_TEST_DOCKER_NETWORK_DISABLED: bool = False
    REPOSITORY_TEST_OUTPUT_MAX_CHARS: int = 8000
    # Comando pytest pasado al wrapper run-tests vía variable de entorno
    PYTEST_CMD: str = "python -m pytest -q --tb=short --disable-warnings"

    INFO_MAIL: str 
    INFOBIP_BASE_URL: str 
    INFOBIP_API_KEY: str 
    REPORT_RECIPIENTS: str 
    REPORT_EMAIL_RATE_LIMIT_PER_MINUTE: int 

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        """
        Convierte BACKEND_CORS_ORIGINS desde string separado por comas
        a una lista de URLs.

        Ejemplo:
        BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

        Resultado:
        ["http://localhost:3000",
          "http://localhost:5173"]
        """
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]
    
    def report_recipients_list(self) -> list[str]:
        return [
            email.strip()
            for email in self.REPORT_RECIPIENTS.split(",")
            if email.strip()
        ]


settings = Settings()