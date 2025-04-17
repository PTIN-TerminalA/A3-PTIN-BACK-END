import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

# Cargar claves al iniciar el módulo
with open("./app/keys/public_key.pem", "rb") as f:
    PUBLIC_KEY = serialization.load_pem_public_key(f.read())

with open("./app/keys/private_key.pem", "rb") as f:
    PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)


def encrypt_dni(dni: str) -> str:
    encrypted = PUBLIC_KEY.encrypt(
        dni.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode()


def decrypt_dni(encrypted_dni_b64: str) -> str:
    decrypted = PRIVATE_KEY.decrypt(
        base64.b64decode(encrypted_dni_b64),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted.decode()
