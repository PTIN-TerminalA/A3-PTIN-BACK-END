from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.user import LoginRequest, UserResponse, RegisterRequest, TokenResponse, UserProfileResponse
from app.models.user import User
from app.models.regular import Regular
from app.schemas.regular import RegisterRegularRequest, RegularResponse
from app.models.gender import Gender
from app.models.admin import Admin
from app.schemas.admin import RegisterAdminRequest, AdminResponse
from app.services.encryption import hash_dni
from app.services.token import create_access_token, decode_access_token
from datetime import timedelta
from app.database import get_db
from argon2 import PasswordHasher
from fastapi import HTTPException

app = FastAPI()


hasher = PasswordHasher()


@app.post("/api/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):

    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email ja enregistrat")
    
    existing_dni = db.query(User).filter(User.dni == hash_dni(request.dni)).first()

    if existing_dni:
        raise HTTPException(status_code=400, detail="DNI ja registrat")

    
  
    hashed_password = hasher.hash(request.password)


    new_user = User(
        name=request.name,
        dni=hash_dni(request.dni),
        email=request.email, 
        password=hashed_password,
        usertype=request.usertype
        )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.id})


    return {"access_token": access_token, "token_type": "bearer"}



@app.post("/api/register-regular", response_model=RegularResponse)
async def register_regular(request: RegisterRegularRequest, db: Session = Depends(get_db)):

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



@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    try:
        hasher.verify(user.password, request.password) 
    except Exception as e:
        raise HTTPException(status_code=401, detail="Contrassenya incorrecta")
    
    access_token = create_access_token(data={"sub": user.id})

    return {"access_token": access_token, "token_type": "bearer"}





@app.get("/api/get_user_id")
async def get_user_id(token: str):
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
        return {"user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token inválido")
    

@app.get("/api/profile", response_model=UserProfileResponse)
async def get_user_profile(token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token invàlid")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    return {
        "name": user.name,
        "email": user.email,
        "phone_num": user.phone_num
    }
