import hashlib
import base64


def hash_dni(dni: str) -> str:

    return hashlib.sha256(dni.encode()).hexdigest()

