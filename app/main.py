# app/main.py

from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from argon2 import PasswordHasher
from bson import ObjectId
from fastapi import Path
from datetime import datetime


# --- SQL imports ---
from app.database import get_db
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, ProfileUpdateRequest, TokenResponseGoogle, UpdateDniRequest, UserTypeRequest, UserTypeResponse
from app.models.user import User
from app.models.regular import Regular
from app.schemas.regular import RegisterRegularRequest, RegularResponse
from app.models.gender import Gender
from app.models.admin import Admin
from app.schemas.admin import RegisterAdminRequest, AdminResponse
from app.services.encryption import encrypt_dni, decrypt_dni 
from app.services.token import create_access_token, decode_access_token

# --- Mongo imports ---
from app.mongodb import get_db as get_mongo_db
from app.reserves.router import Route

app = FastAPI()

#from app.vehicles import router as vehicle_router
#app.include_router(vehicle_router)




# 🔓 CORS (permitir React en :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost", "http://192.168.10.10:5173", "http://192.168.10.10:3001","http://192.168.10.10", "http://projectevia-a.duckdns.org/"],
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


# document with 10.000 passwords that shouldn't be used

def load_common_passwords(file_path="app/commonPasswords.txt"):
    with open(file_path, "r") as file:
        return set(password.strip() for password in file.readlines())

# --- SQL endpoints ---

@app.post("/api/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(400, "Email ja enregistrat.")
    
    common_passwords = load_common_passwords()
    
    if request.password in common_passwords:
        raise HTTPException(400, "La contrasenya es massa comú, si us plau, empra una altra.")

    new_user = User(
        name=request.name,
        dni=encrypt_dni(request.dni),
        email=request.email,
        password=hasher.hash(request.password),
        usertype=request.usertype
    )
    db.add(new_user); db.commit(); db.refresh(new_user)
    token = create_access_token(data={"sub": new_user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/register-regular", response_model=RegularResponse)
async def register_regular(request: RegisterRegularRequest, db: Session = Depends(get_db)):
    userid = decode_access_token(request.token)
    new = Regular(
        id=int(userid.get("sub")),
        birth_date=request.birth_date,
        phone_num=request.phone_num,
        identity=request.identity
    )
    db.add(new); db.commit(); db.refresh(new)
    return new

@app.post("/api/register-admin", response_model=AdminResponse)
async def register_admin(request: RegisterAdminRequest, db: Session = Depends(get_db)):
    userid = decode_access_token(request.token)
    new = Admin(
        id=int(userid.get("sub")), 
        superadmin=request.superadmin
    )
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




@app.post("/api/register-login-google", response_model=TokenResponseGoogle)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        # Si l'usuari ja ha estat registrat amb el seu email, retornem el seu id en un token

        regular = db.query(Regular).filter(Regular.id == user.id).first()
        admin = db.query(Admin).filter(Admin.id == user.id).first()

        token = create_access_token(data={"sub": user.id})
        if regular or admin:
            return {"access_token": token, 
                    "token_type": "bearer",
                    "needs_regular": False
            }
        
        if not regular:
            return {"access_token": token, 
                    "token_type": "bearer",
                    "needs_regular": True
            }

    new_user = User(
        name=request.name,
        dni=encrypt_dni(request.dni),
        email=request.email,
        password=hasher.hash(request.password),
        usertype=request.usertype
    )
    db.add(new_user); db.commit(); db.refresh(new_user)

    token = create_access_token(data={"sub": new_user.id})

    return {"access_token": token, 
            "token_type": "bearer",
            "needs_regular": True
    }


@app.post("/api/update-dni")
async def update_dni(request: UpdateDniRequest, db: Session = Depends(get_db)):
    decoded = decode_access_token(request.access_token)
    user_id = decoded["sub"]

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    user.dni = encrypt_dni(request.dni)
    db.commit(); db.refresh(user)

    return {"message": "DNI actualitzat correctament"}


@app.get("/api/get-user-type")
async def get_user_type(token: str, db: Session = Depends(get_db)):
    decoded = decode_access_token(token)
    user_id = decoded["sub"]

    regular = db.query(Regular).filter(Regular.id == user_id).first()
    admin = db.query(Admin).filter(Admin.id == user_id).first()

    if regular: 
        return {"user_type": str("regular")}
    elif admin:   
        return {"user_type": str("admin")}
    else:
        return {"user_type": str("non-assigned")}






# --- Mongo endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the API amb SQL i Mongo!"}

# --- GET /reserves ---
@app.get("/reserves")
async def list_reserves(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db_mongo = Depends(get_mongo_db),
    db_sql: Session = Depends(get_db),
    user_email: str = Query(None),
    start_location: str = Query(None),
    end_location: str = Query(None),
    state: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
):
    decode_access_token(creds.credentials)

    # Filtrar por user_email -> user_ids
    user_ids = None
    if user_email:
        user = db_sql.query(User).filter(User.email == user_email).first()
        if not user:
            return {"reserves": []}
        user_ids = [user.id]

    # Construir filtro de Mongo
    filt = {}
    if user_ids is not None:
        filt["user_id"] = {"$in": user_ids}
    if start_location:
        filt["start_location"] = start_location
    if end_location:
        filt["end_location"] = end_location
    if state:
        filt["state"] = state
    if start_date or end_date:
        rng = {}
        if start_date: rng["$gte"] = start_date
        if end_date:   rng["$lte"] = end_date
        filt["scheduled_time"] = rng

    cursor = db_mongo["route"].find(filt)
    routes = [serialize_mongo_doc(doc) async for doc in cursor]

    # Añadir email a cada reserva
    for r in routes:
        usr = db_sql.query(User).filter(User.id == int(r["user_id"])).first()
        r["user_email"] = usr.email if usr else None

    return {"reserves": routes}

# POST /reserves/usuari  (reservacotxe)
@app.post("/reserves/usuari")
async def create_route_user(
    route: Route,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    # 1) Obtener user_id desde token
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # 2) Buscar coche disponible y marcarlo ocupado
    car = await db["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(400, "No hi ha cotxes disponibles ara mateix.")
    await db["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Ocupat"}}
    )

    # 3) Convertir scheduled_time a datetime si viene como string
    sched = route.scheduled_time
    if isinstance(sched, str):
        try:
            sched = datetime.fromisoformat(sched)
        except ValueError:
            raise HTTPException(400, "scheduled_time ha de ser ISODate o ISO string")

    # 4) Construir documento en orden fijo
    doc = {
        "user_id":        user_id,
        "start_location": route.start_location,
        "end_location":   route.end_location,
        "scheduled_time": sched,
        "state":          route.state,
        "car_id":         car["_id"]
    }

    # 5) Insertar en la colección `route`
    result = await db["route"].insert_one(doc)
    inserted = await db["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(500, "No s'ha pogut recuperar la reserva")

    # 6) Upsert en la colección `user` para mantener el historial
    await db["user"].update_one(
        {"id": user_id},
        {
            "$push":      {"route_history": inserted},
            "$setOnInsert": {"id": user_id}
        },
        upsert=True
    )

    return {"message": "Reserva confirmada amb èxit!", "data": serialize_mongo_doc(inserted)}


# --- POST /reserves/programada (gestioReserves) ---
@app.post("/reserves/programada")
async def create_route_admin(
    payload: dict = Body(...),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db_mongo = Depends(get_mongo_db),
    db_sql: Session = Depends(get_db)
):
    # 1) Validar y decodificar token
    decode_access_token(creds.credentials)

    # 2) Resolver user_id a partir de user_email
    email = payload.get("user_email")
    if not email:
        raise HTTPException(400, "Cal el camp user_email")
    user = db_sql.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "Usuari no trobat")
    user_id = user.id

    # 3) Buscar coche disponible y marcarlo
    car = await db_mongo["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(400, "No hi ha cotxes disponibles")
    await db_mongo["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Ocupat"}}
    )

    # 4) Convertir scheduled_time a datetime
    sched_str = payload.get("scheduled_time")
    try:
        sched = datetime.fromisoformat(sched_str)
    except Exception:
        raise HTTPException(400, "scheduled_time ha de ser ISODate o ISO string")

    # 5) Construir documento en orden fijo
    doc = {
        "user_id":        user_id,
        "start_location": payload["start_location"],
        "end_location":   payload["end_location"],
        "scheduled_time": sched,
        "state":          payload.get("state", "Programada"),
        "car_id":         car["_id"]
    }

    # 6) Insertar en la colección `route`
    result = await db_mongo["route"].insert_one(doc)
    inserted = await db_mongo["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(500, "No s'ha pogut recuperar la reserva")

    # 7) Upsert en la colección `user` para historial
    await db_mongo["user"].update_one(
        {"id": user_id},
        {
            "$push":      {"route_history": inserted},
            "$setOnInsert": {"id": user_id}
        },
        upsert=True
    )

    out = serialize_mongo_doc(inserted)
    out["user_email"] = email
    return {"reserves": out}

# --- PATCH /reserves/{reserve_id} ---
@app.patch("/reserves/{reserve_id}")
async def update_route(
    reserve_id: str = Path(...),
    payload: dict = Body(...),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db_mongo = Depends(get_mongo_db),
    db_sql: Session = Depends(get_db)
):
    decode_access_token(creds.credentials)

    # No permitimos cambiar user_email en update
    if "user_email" in payload:
        payload.pop("user_email")

    # Si quieren reasignar usuario, podrían pasar user_email, pero omitimos

    # Ejecutar update
    res = await db_mongo["route"].update_one(
        {"_id": ObjectId(reserve_id)},
        {"$set": payload}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Reserva no trobada")
    return {"message": "Reserva actualitzada"}




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


@app.get("/api/profile")
async def get_profile(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """
    Devuelve el perfil completo del usuario: 
    name, email (tabla User) 
    + birth_date, phone_num, identity (tabla Regular).
    """
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # 1) Datos de User
    user: User = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuari no trobat")

    # 2) Datos de Regular
    regular: Regular = db.query(Regular).filter(Regular.id == user_id).first()
    if not regular:
        raise HTTPException(404, "Dades regular no trobades")

    return {
        "name": user.name,
        "email": user.email,
        "birth_date": regular.birth_date.isoformat(),
        "phone_num": regular.phone_num,
        "identity": regular.identity
    }

@app.patch("/api/profile", response_model=dict)
async def update_profile(
    update: ProfileUpdateRequest,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuari no trobat")
    user.name = update.name

    regular = db.query(Regular).filter(Regular.id == user_id).first()
    if not regular:
        raise HTTPException(404, "Dades de perfil no trobades")
    regular.birth_date = update.birth_date
    regular.phone_num  = update.phone_num
    regular.identity   = update.identity

    db.commit()
    return {"message": "Perfil actualitzat correctament"}




from app.vehicles.router import router as vehicle_router
app.include_router(vehicle_router)

