from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

hasher = PasswordHasher()

contrasenya = "contrasenya"

# Quan un usuari crei un compte, haureu de fer hash de la seva contrasenya de la forma seguent:
print(f'Utilitzant argon2 amb random salt per fer hash de "{contrasenya}":')
hashed = hasher.hash(contrasenya)
print(f"{hashed}\n")
# MAI guardeu `contrasenya` a la base de dades!!! Heu de guardar només `hashed`.

# Si us fixeu, cada vegada que feu hash surt un valor diferent. Aixó és a propòsit, gracies al random salt.
print(f'Utilitzant argon2 amb random salt per fer hash de "{contrasenya}" una segona vegada:')
hashed = hasher.hash(contrasenya)
print(f"{hashed}\n")
# Això vol dir que el hash només s'ha de fer una vegada i guardar-lo a la base de dades.

print(f'Utilitzant argon2 amb random salt per fer hash de "{contrasenya}" una tercera vegada:')
hashed = hasher.hash(contrasenya)
print(f"{hashed}\n")

# Per comprovar si una contrasenya és correcta, es fa de la manera següent:
hash_obtinguda_de_bdd = "$argon2id$v=19$m=65536,t=3,p=4$fgtyna+tWyR+i7rrOl/xUg$XjauJU11pMHOd/fnHO8/EDI4VHi6FByuKvC4qfmVTMw"
contrasenya_enviada_per_usuari = "12345678"

try:
    if hasher.verify(hash_obtinguda_de_bdd, contrasenya_enviada_per_usuari):
        print("La contrasenya és correcta.")
except VerifyMismatchError:
    print("La contrasenya és incorrecta.")
except InvalidHashError:
    print("Error intern! La hash rebuda del servidor no és vàlida!")
except VerificationError as e:
    print(f"Alguna cosa ha anat malament: {e}")