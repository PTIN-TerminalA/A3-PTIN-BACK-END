# app/main.py

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from argon2 import PasswordHasher
from bson import ObjectId
from fastapi import Path


# --- SQL imports ---
from app.database import get_db
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse
from app.models.user import User
from app.models.regular import Regular
from app.schemas.regular import RegisterRegularRequest, RegularResponse
from app.models.gender import Gender
from app.models.admin import Admin
from app.schemas.admin import RegisterAdminRequest, AdminResponse
from app.services.encryption import hash_dni
from app.services.token import create_access_token, decode_access_token

# --- Mongo imports ---
from app.mongodb import get_db as get_mongo_db
from app.reserves.router import Route

app = FastAPI()

# 🔓 CORS (permitir React en :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# seguridad bearer para extraer token
bearer_scheme = HTTPBearer()
hasher = PasswordHasher()

def serialize_mongo_doc(doc: dict) -> dict:
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, dict):
            out[k] = serialize_mongo_doc(v)
        elif isinstance(v, list):
            out[k] = [
                str(item) if isinstance(item, ObjectId)
                else serialize_mongo_doc(item) if isinstance(item, dict)
                else item
                for item in v
            ]
        else:
            out[k] = v
    return out

# --- SQL endpoints ---

@app.post("/api/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(400, "Email ja enregistrat")
    if db.query(User).filter(User.dni == hash_dni(request.dni)).first():
        raise HTTPException(400, "DNI ja registrat")
    new_user = User(
        name=request.name,
        dni=hash_dni(request.dni),
        email=request.email,
        password=hasher.hash(request.password),
        usertype=request.usertype
    )
    db.add(new_user); db.commit(); db.refresh(new_user)
    token = create_access_token(data={"sub": new_user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/register-regular", response_model=RegularResponse)
async def register_regular(request: RegisterRegularRequest, db: Session = Depends(get_db)):
    new = Regular(
        id=request.user_id,
        birth_date=request.birth_date,
        phone_num=request.phone_num,
        identity=request.identity
    )
    db.add(new); db.commit(); db.refresh(new)
    return new

@app.post("/api/register-admin", response_model=AdminResponse)
async def register_admin(request: RegisterAdminRequest, db: Session = Depends(get_db)):
    new = Admin(id=request.user_id, superadmin=request.superadmin)
    db.add(new); db.commit(); db.refresh(new)
    return new

@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(404, "Usuari no trobat")
    try:
        hasher.verify(user.password, request.password)
    except:
        raise HTTPException(401, "Contrassenya incorrecta")
    token = create_access_token(data={"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/get_user_id")
async def get_user_id(token: str):
    payload = decode_access_token(token)
    return {"user_id": int(payload.get("sub"))}

# --- Mongo endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the API amb SQL i Mongo!"}

@app.get("/reserves")
async def list_reserves(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    # opcional: validar token
    decode_access_token(creds.credentials)
    cursor = db["route"].find()
    reserves = [serialize_mongo_doc(doc) async for doc in cursor]
    return {"reserves": reserves}

@app.post("/reserves/programada")
async def create_route(
    route: Route,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    payload = decode_access_token(creds.credentials)
    user_id = payload.get("sub")
    car = await db["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(400, "No hi ha cotxes disponibles ara mateix.")
    await db["car"].update_one({"_id": car["_id"]}, {"$set": {"state": "Ocupat"}})
    doc = route.dict()
    doc["car_id"] = car["_id"]
    doc["user_id"] = user_id
    result = await db["route"].insert_one(doc)
    inserted = await db["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(500, "No s'ha pogut recuperar la reserva")
    return {"message": "Reserva confirmada amb èxit!", "data": serialize_mongo_doc(inserted)}




@app.delete("/reserves/{reserve_id}")
async def delete_reserve(
    reserve_id: str = Path(..., description="ID de la reserva a eliminar"),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    decode_access_token(creds.credentials)  # validem el token
    result = await db["route"].delete_one({"_id": ObjectId(reserve_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, detail="Reserva no trobada")
    return {"message": "Reserva eliminada correctament"}


@app.get("/check-user")
async def check_user(email: str = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User exists"}
