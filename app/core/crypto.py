from cryptography.fernet import Fernet

from app.core.config import settings


fernet = Fernet(settings.FERNET_SECRET_KEY.encode())


def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")