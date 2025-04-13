from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.user import LoginRequest, UserResponse, RegisterRequest
from app.models.user import User
from app.models.regular import Regular
from app.schemas.regular import RegularCreate
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
        raise HTTPException(status_code=400, detail="Email ja registrat")
    
    # Encriptar la contraseña
    hashed_password = hasher.hash(request.password)

    # Crear el nuevo usuario
    new_user = User(email=request.email, password=hashed_password)

    # Guardar el usuario en la base de datos
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Devolver el usuario con el esquema `UserResponse`
    return new_user


@app.post("/api/regular/register", response_model=RegularCreate)
async def register_regular(request: RegularCreate, db: Session = Depends(get_db)):
    # Verificar si el usuario existe (esto debe ser un usuario que ya está registrado en la tabla "user")
    existing_user = db.query(User).filter(User.email == request.email).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="L'usuari no existeix")

    # Crear un nuevo registro en la tabla "regular"
    new_regular = Regular(
        user_id=existing_user.id,
        name=request.name,
        birth_date=request.birth_date,
        phone_num=request.phone_num,  # Cambié a 'phone_num'
        identity=request.identity
    )
    db.add(new_regular)
    db.commit()
    db.refresh(new_regular)

    return new_regular



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
