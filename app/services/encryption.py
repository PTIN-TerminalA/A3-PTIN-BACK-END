from cryptography.fernet import Fernet
import os

FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY)


def encrypt_dni(dni: str) -> str:
    return fernet.encrypt(dni.encode()).decode()

def decrypt_dni(encrypted_dni: str) -> str:
    return fernet.decrypt(encrypted_dni.encode()).decode()

