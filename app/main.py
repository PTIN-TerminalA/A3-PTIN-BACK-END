from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.user import LoginRequest, UserResponse, RegisterRequest
from app.models.user import User
from app.models.regular import Regular
from app.schemas.regular import RegisterRegularRequest, RegularResponse
from app.models.gender import Gender
from app.models.admin import Admin
from app.schemas.admin import RegisterAdminRequest, AdminResponse
from app.services.encryption import encrypt_dni

from app.database import get_db
from argon2 import PasswordHasher

app = FastAPI()

# Inicializar el hasher de contraseñas
hasher = PasswordHasher()


@app.post("/api/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Verificar si el email ya está registrado
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email ja enregistrat")
    
    # Encriptar la contraseña
    hashed_password = hasher.hash(request.password)

    # Crear el nuevo usuario
    new_user = User(
        name=request.name,
        dni=encrypt_dni(request.dni),
        email=request.email, 
        password=hashed_password,
        usertype=request.usertype
        )

    # Guardar el usuario en la base de datos
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Devolver el usuario con el esquema `UserResponse`
    return new_user


@app.post("/api/register-regular", response_model=RegularResponse)
async def register_regular(request: RegisterRegularRequest, db: Session = Depends(get_db)):
    # Verificar que el user_id existe
    '''
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Error")

    # Verificar que el identity existe en la tabla gender
    gender = db.query(Gender).filter(Gender.identity == request.identity).first()
    if not gender:
        raise HTTPException(status_code=400, detail="Género no válido")

    # Verificar que ese user no tenga ya un regular asociado
    existing = db.query(Regular).filter(Regular.id == request.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Este usuario ya está registrado como regular")
    '''
    # Crear el regular
    new_regular = Regular(
        id=request.user_id,
        birth_date=request.birth_date,
        phone_num=request.phone_num,
        identity=request.identity
    )

    db.add(new_regular)
    db.commit()
    db.refresh(new_regular)

    return new_regular


@app.post("/api/register-admin", response_model=AdminResponse)
async def register_regular(request: RegisterAdminRequest, db: Session = Depends(get_db)):
    new_admin = Admin(
        id = request.user_id,
        superadmin = request.superadmin
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return new_admin



@app.post("/api/login", response_model=UserResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Buscar el usuario en la base de datos por su email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")
    
    # Verificar la contraseña
    try:
        hasher.verify(user.password, request.password)  # Verificar el hash de la contraseña
    except Exception as e:
        raise HTTPException(status_code=401, detail="Contrassenya incorrecta")
    
    # Si la contraseña es correcta, devolver los datos del usuario
    return user  # Esto usa el esquema `UserResponse` automáticamente
