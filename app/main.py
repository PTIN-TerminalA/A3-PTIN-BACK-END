# app/main.py

from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import timedelta
from argon2 import PasswordHasher
from bson import ObjectId
from fastapi import Path
from datetime import datetime
from typing import List
import httpx
import asyncio
import websockets
import json


# --- SQL imports ---
from app.database import get_db
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, TokenRequest, ProfileUpdateRequest, TokenResponseGoogle, UpdateDniRequest, UserTypeRequest, UserTypeResponse
from app.models.user import User
from app.models.regular import Regular
from app.schemas.regular import RegisterRegularRequest, RegularResponse
from app.models.gender import Gender
from app.models.admin import Admin
from app.schemas.admin import RegisterAdminRequest, AdminResponse
from app.services.encryption import encrypt_dni, decrypt_dni 
from app.services.token import create_access_token, decode_access_token
from app.models.service import Service, Price, Schedule, Valoration, Tag, ServiceTag
from app.schemas.service import ServiceSchema, PriceSchema, ScheduleSchema, ServiceTagSchema
from app.schemas.location import LocationSchema, WifiMeasuresList


# --- Mongo imports ---
from app.mongodb import get_db as get_mongo_db
from app.reserves.router import Route

app = FastAPI()

#from app.vehicles import router as vehicle_router
#app.include_router(vehicle_router)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(connect_and_listen())


# 🔓 CORS (permitir React en :5173)
#ho permetem de moment a tot arreu
"""app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost", "http://192.168.10.10:5173", "http://192.168.10.10:3001","http://192.168.10.10", "http://projectevia-a.duckdns.org/", "flysy.software", "flysy.software/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)"""

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost", "http://192.168.10.10:5173", "http://192.168.10.10:3001","http://192.168.10.10", "http://projectevia-a.duckdns.org/", "flysy.software", "flysy.software/"],
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
    

    if admin: 
        superadmin = db.query(Admin).filter(Admin.id == user_id, Admin.superadmin == True).first()
        if superadmin:
            return {"user_type": str("superadmin")}
        else:
            return {"user_type": str("admin")}
    elif regular:   
        return {"user_type": str("regular")}
    else:
        return {"user_type": str("non-assigned")}


#Aquest endpoint ens reotrna la llista de serveis disponibles
@app.get("/api/getServices",response_model=List[ServiceSchema])
async def getServices(db: Session = Depends(get_db)):
    services = db.query(Service).all()

    return services


#Aquest endpoint ens retorna la llista de preus disponibles pels serveis
@app.get("/api/getPrices",response_model=List[PriceSchema])
async def getPrices(db: Session = Depends(get_db)):
    prices = db.query(Price).all()

    return prices

#Donat l'ID d'un servei concret, aquest endpoint ens retorna els schedules disponibles
@app.post("/api/getSchedules", response_model=List[ScheduleSchema])
async def getSchedules(service_id: int, db: Session = Depends(get_db)):
    schedules = db.query(Schedule).filter(Schedule.service_id == service_id).all()
    if not schedules:
        raise HTTPException(status_code=404, detail="No s'han trobat horaris per aquest servei")
    return schedules


#Aquest endpoint ens retorna la llista de tags disponibles
@app.get("/api/getTags")
async def getTags(db: Session = Depends(get_db)):
    tags = db.query(Tag).all()
    if not tags:
        raise HTTPException(status_code=404, detail="No s'han trobat tags")
    return tags


#Aquest endpoint ens retorna el tag d'un servei concret donat el seu ID
@app.post("/api/getServiceTag")
async def getServiceTag(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Servei no trobat")
    tag = db.query(ServiceTag).filter(ServiceTag.service_id == service_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no trobat")
    return tag


#Aquest endpoint ens retorna les valoracions d'un servei concret donat el seu ID
@app.post("/api/getValoration")
async def getValoration(service_id: int, db: Session = Depends(get_db)):
    valoration = db.query(Valoration).filter(Valoration.service_id == service_id).all()
    if not valoration:
        raise HTTPException(status_code=404, detail="Valoracions no trobades")
    return valoration





#Aquest endpoint ens retorna la posició d'un usuari donat un payload de mesures wifi
@app.post("/api/getUserPosition")
async def getUserPosition(payload: WifiMeasuresList):
    ai_url = "http://10.60.0.3:2222/localize" #Hay que canmbiarla en produccion por la que esté alojando la api de la IA

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(ai_url, json=payload.model_dump())
            response.raise_for_status()  # lanza excepción si status != 200
            data = response.json()
            return {
                "x": data["x"],
                "y": data["y"]
            }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error al comunicar con la IA: {str(e)}")
    

#Aquest endpoint ens retorna el servei més proper a una posició donada

@app.post("/api/getNearestService")

async def getNearestService(userLocation: LocationSchema, db: Session = Depends(get_db)):
    services = db.query(Service.id, Service.location_x, Service.location_y).all()
    if not services:
        raise HTTPException(status_code=404, detail="No s'han trobat serveis")

    # Preparar el diccionario de servicios para la petición a la API de routing
    service_dict = {
        s.id: (float(s.location_x), float(s.location_y))
        for s in services
    }

    payload = {
        "position": (userLocation.x, userLocation.y),
        "request": service_dict
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://10.60.0.3:1111/getNearest", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    nearest_data = response.json()  # Ejemplo: {"id": 42}

    # Aquí puedes devolver el ID, o buscar info extra en la base de datos y devolver más detalles
    return {"nearest_service_id": nearest_data["id"]}


# 🚗 Endpoint para obtener el coche más cercano
@app.post("/api/getNearestCar")
async def get_nearest_car(userLocation: LocationSchema):
    if not live_car_positions:
        raise HTTPException(status_code=404, detail="No s'han trobat cotxes disponibles")

    # Preparar el diccionario de coches para la petición a la API de routing
    car_dict = {
        c._id: (float(c.location_x), float(c.location_y))
        for c in live_car_positions
    }

    payload = {
        "position": (userLocation.x, userLocation.y),
        "request": live_car_positions
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://10.60.0.3:1111/getNearest", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    nearest_data = response.json()  # Ejemplo: {"_id": C1}
    return {"nearest_car_id": nearest_data["_id"]}


#Aquest endpoint ens retorna tota la informació d'un user donat el seu ID
 
@app.post ("/api/getUserInfo")
async def getUserInfo(data: TokenRequest, db: Session = Depends(get_db)):
    user_id = decode_access_token(data.token)
    user_id = int(user_id["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")
    
    return user
    



# ------------------------------------ Mongo endpoints ------------------------------------------

@app.get("/")
async def read_root():
    return {"message": "Welcome to the API amb SQL i Mongo!"}

# --- GET /reserves ---
@app.get("/api/reserves")
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



# --- POST /reserves/app (reservas desde app móvil, con scheduled_time automático y estado fijo) ---
@app.post("/api/reserves/app")
async def create_route_app(
    payload: dict = Body(...),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db_mongo=Depends(get_mongo_db),
    db_sql: Session = Depends(get_db)
):
    """
    Crea una reserva desde la app:
    1) Decodifica token → user_id.
    2) Obtiene servicio más cercano vía getNearestService(location).
    3) Usa el nombre de ese servicio como start_location.
    4) end_location lo indica el usuario en payload.
    5) scheduled_time = ahora (); state = "En curs".
    6) Marca el coche como "Solicitat".
    7) Inserta en Mongo y en historial de user.
    8) Devuelve {"message", "data": reserva, "car_id": "<ObjectId>"}
    """
    # 1) Decodificar token y extraer user_id
    payload_token = decode_access_token(creds.credentials)
    user_id = int(payload_token.get("sub"))

    # 2) Validar y extraer ubicación actual de payload
    loc = payload.get("location")
    if not loc or not isinstance(loc, dict):
        raise HTTPException(status_code=400, detail="Debes enviar `location` con x e y.")
    try:
        user_location = LocationSchema(x=loc["x"], y=loc["y"])
    except Exception:
        raise HTTPException(status_code=400, detail="Formato inválido para `location`.")

    # 3) Llamar a getNearestService(...) para obtener servicio más cercano
    nearest_resp = await getNearestService(user_location, db_sql)
    service_id = nearest_resp.get("nearest_service_id")
    if service_id is None:
        raise HTTPException(status_code=500, detail="No se pudo determinar servicio cercano.")
    service_obj = db_sql.query(Service).filter(Service.id == service_id).first()
    if not service_obj:
        raise HTTPException(status_code=404, detail="Servicio no encontrado en SQL.")
    start_location_name = service_obj.name

    # 4) Validar end_location en payload
    end_loc = payload.get("end_location")
    if not end_loc or not isinstance(end_loc, str):
        raise HTTPException(status_code=400, detail="Debes indicar `end_location` (destino).")

    # 5) scheduled_time = ahora(); state fijo "En curs"
    scheduled_dt = datetime.utcnow()
    state = "En curs"

    # 6) Buscar coche disponible y marcarlo "Solicitat"
    car = await db_mongo["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(status_code=400, detail="No hay coches disponibles.")
    await db_mongo["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Solicitat"}}
    )
    car_id = car["_id"]

    # 7) Construir documento y guardarlo en "route"
    new_route_doc = {
        "user_id":        user_id,
        "start_location": start_location_name,
        "end_location":   end_loc,
        "scheduled_time": scheduled_dt,
        "state":          state,
        "car_id":         car_id
    }
    result = await db_mongo["route"].insert_one(new_route_doc)
    inserted = await db_mongo["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(status_code=500, detail="No se pudo recuperar la reserva.")

    # 8) Upsert en colección "user" para historial
    await db_mongo["user"].update_one(
        {"id": user_id},
        {
            "$push":       {"route_history": inserted},
            "$setOnInsert": {"id": user_id}
        },
        upsert=True
    )

    # 9) Devolver respuesta con car_id
    return {
        "message": "Reserva (desde app) confirmada con éxito.",
        "data": serialize_mongo_doc(inserted),
        "car_id": str(car_id)
    }



@app.post("/api/inicia-trajecte")
async def inicia_trajecte(
    destination: dict,  # debe contener {"x": float, "y": float}
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    # 1) Obtener user_id desde el token
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # 2) Obtener la última reserva del usuario (la más reciente)
    last_route = await db["route"].find_one(
        {"user_id": user_id},
        sort=[("scheduled_time", -1)]  # orden descendente
    )
    if not last_route:
        raise HTTPException(404, "No s'ha trobat cap reserva activa per aquest usuari.")

    car_id = last_route.get("car_id")
    if not car_id:
        raise HTTPException(500, "Reserva sense cotxe assignat.")

    # 3) Llamar al endpoint PUT /cotxe/{cotxe_id}/en_curs para actualizar el estado del cotxe
    try:
        async with httpx.AsyncClient() as client:
            put_response = await client.put(
                f"http://192.168.10.10:8000/cotxe/{car_id}/en_curs",  # Ajusta host/puerto si es necesario
                timeout=5.0
            )
            put_response.raise_for_status()
    except Exception as e:
        raise HTTPException(500, f"No s'ha pogut posar el cotxe en estat 'En curs': {str(e)}")

    # 4) Llamar al controller para enviar el cotxe a la destinación
    try:
        x = destination.get("x")
        y = destination.get("y")
        if x is None or y is None:
            raise HTTPException(400, "Cal proporcionar les coordenades 'x' i 'y' de la destinació.")

        async with httpx.AsyncClient() as client:
            controller_response = await client.post(
                "http://192.168.10.11:8767/controller/demana-cotxe",
                json={"x": x, "y": y},
                timeout=5.0
            )
            controller_response.raise_for_status()
    except Exception as e:
        raise HTTPException(500, f"Error en contactar amb el controlador: {str(e)}")

    return {
        "message": "Trajecte iniciat correctament.",
        "car_id": str(car_id),
        "destinacio": {"x": x, "y": y}
    }





# --- POST /reserves/usuari (reservacotxe) ---
@app.post("/api/reserves/usuari")
async def create_route_user(
    route: Route,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    # 1) Obtener user_id desde token
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # 2) Obtener coordenadas del punto de recogida
    establishment = await db["establishment"].find_one(
        {"name": route.start_location},
        {"location_x": 1, "location_y": 1}
    )
    if not establishment:
        raise HTTPException(400, f"No s'ha trobat l'establiment {route.start_location}")
    
    x_coord = establishment["location_x"]
    y_coord = establishment["location_y"]

    # 3) Buscar coche disponible y marcarlo ocupado
    car = await db["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(400, "No hi ha cotxes disponibles ara mateix.")
    await db["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Ocupat"}}
    )
    car_id = car["_id"]  # guardamos el id del coche

    # 4) Convertir scheduled_time a datetime si viene como string
    sched = route.scheduled_time
    if isinstance(sched, str):
        try:
            sched = datetime.fromisoformat(sched)
        except ValueError:
            raise HTTPException(400, "scheduled_time ha de ser ISODate o ISO string")

    # 5) Construir documento en orden fijo
    doc = {
        "user_id":        user_id,
        "start_location": route.start_location,
        "end_location":   route.end_location,
        "scheduled_time": sched,
        "state":          route.state,
        "car_id":         car_id
    }

    # 6) Insertar en la colección `route`
    result = await db["route"].insert_one(doc)
    inserted = await db["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(500, "No s'ha pogut recuperar la reserva")

    # 7) Upsert en la colección `user` para mantener el historial
    await db["user"].update_one(
        {"id": user_id},
        {
            "$push":      {"route_history": inserted},
            "$setOnInsert": {"id": user_id}
        },
        upsert=True
    )

    # 8) Llamar al controlador para mover el coche
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://192.168.10.11:8767/controller/demana-cotxe",  # Ajusta esta URL según tu configuración
                json={"x": x_coord, "y": y_coord},
                timeout=5.0
            )
            response.raise_for_status()
    except Exception as e:
        # No fallamos la reserva si hay error con el controlador, solo lo registramos
        print(f"Error al contactar con el controlador: {str(e)}")

    # 9) Devolver response, incluyendo el car_id asignado
    return {
        "message": "Reserva confirmada amb èxit!",
        "data": serialize_mongo_doc(inserted),
        "car_id": str(car_id)
    }



# --- POST /reserves/programada (gestioReserves) ---
@app.post("/api/reserves/programada")
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

    # 3) Buscar coche disponible y marcarlo ocupado
    car = await db_mongo["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(400, "No hi ha cotxes disponibles")
    await db_mongo["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Ocupat"}}
    )
    car_id = car["_id"]  # guardamos el id del coche

    # 4) Convertir scheduled_time a datetime
    sched_str = payload.get("scheduled_time")
    try:
        sched = datetime.fromisoformat(sched_str)
    except Exception:
        raise HTTPException(400, "scheduled_time ha de ser ISODate o ISO string")

    # 5) Construir documento en orden fijo
    doc = {api/
        "user_id":        user_id,
        "start_location": payload["start_location"],
        "end_location":   payload["end_location"],
        "scheduled_time": sched,
        "state":          payload.get("state", "Programada"),
        "car_id":         car_id
    }

    # 6) Insertar en la colección `route`
    result = await db_mongo["route"].insert_one(doc)
    inserted = await db_mongo["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(500, "No s'ha pogut recuperar la reserva")

    # 7) Upsert en la colección `user` para histórico
    await db_mongo["user"].update_one(
        {"id": user_id},
        {
            "$push":      {"route_history": inserted},
            "$setOnInsert": {"id": user_id}
        },
        upsert=True
    )

    # 8) Serializar y añadir user_email en la respuesta
    out = serialize_mongo_doc(inserted)
    out["user_email"] = email

    # 9) Devolver response incluyendo el car_id asignado
    return {
        "reserves": out,
        "car_id": str(car_id)
    }

# --- PATCH /reserves/{reserve_id} ---
@app.patch("/api/reserves/{reserve_id}")
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




@app.delete("/api/reserves/{reserve_id}")
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

# --- Peticion ruta ---
# Primero cogemos la posicion de los establecimientos de la base de datos
# luego se hace la peticion a la API externa y se devuelve el resultado


#Endpoint que modifica l'estat d'un cotxe a "Esperant" donat el seu ID.
#Ús: curl -X PUT http://localhost:8000/cotxe/{cotxe_id}/esperant
#Post: L'estat del car amb _id = {cotxe_id} passa a ser "Esperant"
@app.put("/cotxe/{cotxe_id}/esperant")
async def state_car_waiting(cotxe_id: str, db=Depends(get_mongo_db)):
   
    # Busquem el cotxe a la base de dades
    car = await db["car"].find_one({"_id": cotxe_id})
    if not car:
        raise HTTPException(status_code=404, detail="Cotxe no trobat.")

# Peticion para obtener la posicion del establecimiento pasado por parametro 
# Uso: /api/establishment-position?name="nombredelestablecimiento"
# Devuelve: {name: "nombredelestablecimiento", location_x: 0.5, location_y: 0.5}
@app.get("/api/establishment-position")
async def get_establishment_position(
    name: str = Query(..., description="Nombre del establecimiento"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener la posición de un establecimiento por su nombre.
    Devuelve las coordenadas (location_x, location_y).
    """
    try:
        print(f"Buscando establecimiento con nombre: {name}")

        # Consultar la base de datos para obtener las coordenadas del establecimiento
        establishment = db.execute(
            text("SELECT location_x, location_y FROM service WHERE LOWER(name) = LOWER(:name)"),
            {"name": name}
        ).fetchone()

        print(f"Resultado de la consulta: {establishment}")

        if not establishment:
            print("Establecimiento no encontrado")
            raise HTTPException(status_code=404, detail="Establecimiento no encontrado")

        print(f"Coordenadas encontradas: location_x={establishment[0]}, location_y={establishment[1]}")

        return {
            "name": name,
            "location_x": establishment[0],
            "location_y": establishment[1]
        }

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP para que sean manejadas correctamente
        raise http_exc
    except Exception as e:
        # Manejar errores generales
        print(f"Error al consultar la base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al consultar la base de datos")

# Peticion a la API externa
# (En caso de no estar listo el controller, se puede usar ejecutando el backend del A5, en 
# la rama de routingImprovment+modelPredictiu i estando en la carpeta de /routing/pathfinng, 
# i ejecutando uvicorn api:app --reload --port 9000)
# Espera un JSON amb les coordenades normalitzades dels punts d'inici i final:
#
#json
#{
#  "start": [x_start, y_start],
#  "goal": [x_goal, y_goal]
#}
#
#- start: Coordenades normalitzades del punt d'inici (valors entre 0 i 1).
#- goal: Coordenades normalitzades del punt de destí (valors entre 0 i 1).
# ------------------------------------------------------------------------
# Si es troba un camí, la resposta serà un JSON amb:
#- length: Nombre total de passos en el camí.
#- path: Llista de punts del camí, cadascun amb coordenades normalitzades.

#json
#{
#  "length": 273,
#  "path": [
#    [0.501, 0.398],
#    [0.502, 0.397],
#    ...
#  ]
#}
@app.post("/api/shortest-path")
async def get_shortest_path(payload: dict = Body(...)):
    """
    Endpoint para calcular el camino más corto entre dos puntos.
    """
    try:
        # Realizar la petición a la API externa
        response = requests.post(
            "http://10.60.0.3:1111/path",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Manejar la respuesta de la API externa
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise HTTPException(status_code=400, detail="Bad Request: Puntos fuera de los límites o no transitables.")
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="Not Found: No se encontró un camino entre los puntos especificados.")
        else:
            raise HTTPException(status_code=response.status_code, detail="Error desconocido en la API externa.")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar con la API externa: {str(e)}")

# Peticion para obtener todos los nombres de servicios
# Devuelve: [{name: "nombredelservicio"}, ...]
@app.get("/api/services")
async def get_all_services(db: Session = Depends(get_db)):
    """
    Endpoint para obtener todos los nombres de los servicios en la base de datos.
    Devuelve una lista de objetos con los nombres de los servicios.
    """
    try:
        print("Obteniendo todos los nombres de los servicios")

        # Consultar la base de datos para obtener los nombres de los servicios
        services = db.execute(
            text("SELECT name FROM service")
        ).fetchall()

        print(f"Servicios encontrados: {services}")

        if not services:
            print("No se encontraron servicios")
            raise HTTPException(status_code=404, detail="No se encontraron servicios")

        # Formatear los resultados como una lista de objetos con 'name'
        service_list = [{"name": service[0]} for service in services]

        return service_list

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP para que sean manejadas correctamente
        raise http_exc
    except Exception as e:
        # Manejar errores generales
        print(f"Error al consultar la base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al consultar la base de datos")


#Endpoint que modifica l'estat d'un cotxe a "Esperant" donat el seu ID.
#Ús: curl -X PUT http://localhost:8000/cotxe/{cotxe_id}/esperant
#Post: L'estat del car amb _id = {cotxe_id} passa a ser "Esperant"
@app.put("/cotxe/{cotxe_id}/esperant")
async def state_car_available(cotxe_id: str, db=Depends(get_mongo_db)):
   
    # Busquem el cotxe a la base de dades
    car = await db["car"].find_one({"_id": cotxe_id})
    if not car:
        raise HTTPException(status_code=404, detail="Cotxe no trobat.")

    # Actualitzem l'estat a 'Esperant'
    await db["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Esperant"}}
    )

    return {"missatge": "Cotxe actualitzat correctament a 'Esperant'."}


#Endpoint que modifica l'estat d'un cotxe a "En curs" donat el seu ID.
#Ús: curl -X PUT http://localhost:8000/cotxe/{cotxe_id}/en_curs
#Post: L'estat del car amb _id = {cotxe_id} passa a ser "En curs"
@app.put("/cotxe/{cotxe_id}/en_curs")
async def state_car_in_progress(cotxe_id: str, db=Depends(get_mongo_db)):
   
    # Busquem el cotxe a la base de dades
    car = await db["car"].find_one({"_id": cotxe_id})
    if not car:
        raise HTTPException(status_code=404, detail="Cotxe no trobat.")

    # Actualitzem l'estat a 'En curs'
    await db["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "En curs"}}
    )

    return {"missatge": "Cotxe actualitzat correctament a 'En curs'."}


#Endpoint que modifica l'estat d'un cotxe a "Solicitat" donat el seu ID.
#Ús: curl -X PUT http://localhost:8000/cotxe/{cotxe_id}/solicitat
#Post: L'estat del car amb _id = {cotxe_id} passa a ser "Solicitat"
@app.put("/cotxe/{cotxe_id}/solicitat")
async def state_car_requested(cotxe_id: str, db=Depends(get_mongo_db)):
   
    # Busquem el cotxe a la base de dades
    car = await db["car"].find_one({"_id": cotxe_id})
    if not car:
        raise HTTPException(status_code=404, detail="Cotxe no trobat.")

    # Actualitzem l'estat a 'Solicitat'
    await db["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Solicitat"}}
    )

    return {"missatge": "Cotxe actualitzat correctament a 'Solicitat'."}


#Endpoint que modifica l'estat d'un cotxe a "Disponible" donat el seu ID.
#Ús: curl -X PUT http://localhost:8000/cotxe/{cotxe_id}/disponible
#Post: L'estat del car amb _id = {cotxe_id} passa a ser "Disponible"
@app.put("/cotxe/{cotxe_id}/disponible")
async def state_car_available(cotxe_id: str, db=Depends(get_mongo_db)):
   
    # Busquem el cotxe a la base de dades
    car = await db["car"].find_one({"_id": cotxe_id})
    if not car:
        raise HTTPException(status_code=404, detail="Cotxe no trobat.")

    # Actualitzem l'estat a 'Disponible'
    await db["car"].update_one(
        {"_id": car["_id"]},
        {"$set": {"state": "Disponible"}}
    )

    return {"missatge": "Cotxe actualitzat correctament a 'Disponible'."}

from app.vehicles.router import router as vehicle_router
app.include_router(vehicle_router)


# 👂 Cliente que se conecta al WebSocket remoto y escucha mensajes
async def connect_and_listen():
    uri = "ws://192.168.10.11:8766"
    print(f"Intentando conectar a WebSocket en {uri}")
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Conectado al WebSocket remoto")
                async for message in websocket:
                    data = json.loads(message)
                    print("📨 Mensaje recibido:", data)
                    # Aquí puedes procesar el mensaje, guardarlo en base de datos, emitirlo, etc.
                    
                    #codi provisional per rebre dades del cotxe i introduïrles al array live_car_positions
                    #car_id = data.get("id")
                    #x = data.get("x")
                    #y = data.get("y")
                    #if car_id is not None and x is not None and y is not None:
                    #    live_car_positions[car_id] = (float(x), float(y))

        except Exception as e:
            print(f"⚠️ Error de conexión: {e} — Reintentando en 5 segundos...")
            await asyncio.sleep(5)
            
            
#-------------------------Endpoints localizacion e IA-----------------------------------

#para la app

@app.get("/cotxe/{cotxe_id}/status")
async def get_car_status(
    cotxe_id: str,
    db=Depends(get_mongo_db)
):
    # 1) Obtener posición desde el diccionario global
    pos = live_car_positions.get(cotxe_id)
    if pos is None:
        raise HTTPException(status_code=404, detail=f"No s'ha trobat la posició del cotxe {cotxe_id}")

    # 2) Obtener estado desde MongoDB
    car_doc = await db["car"].find_one({"_id": ObjectId(cotxe_id)}, {"state": 1})
    if not car_doc:
        raise HTTPException(status_code=404, detail=f"No s'ha trobat el cotxe {cotxe_id} a la BDD")

    # 3) Devolver resultado
    return {
        "car_id": cotxe_id,
        "position": {
            "x": pos[0],
            "y": pos[1]
        },
        "state": car_doc["state"]
    }


# app/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List
from jose import jwt, JWTError
from sqlalchemy.orm import Session

# --- IMPORTS DELS TEUS MODELS (segons on els tinguis definits) ---
from app.models.flight    import Flight
from app.models.airline   import Airline
from app.models.ticket    import Ticket
from app.database         import get_db



# --- AUTENTICACIÓ BÀSICA JWT per generar el current_user ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "la_teva_clau_secreta"
ALGORITHM  = "HS256"

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(401, "Token invàlid")
        return {"id": int(user_id)}
    except JWTError:
        raise HTTPException(401, "Token invàlid")

# --- SCHEMAS Pydantic ---
class AirlineImage(BaseModel):
    uri: str

class RouteInfo(BaseModel):
    origin: str
    originName: str
    destination: str
    destinationName: str
    departureTime: str
    arrivalTime: str

class PassengerInfo(BaseModel):
    seat: str
    ticketNumber: str

class FlightResponse(BaseModel):
    id: str
    airline: str
    airlineImage: AirlineImage
    flightNumber: str
    route: RouteInfo
    passenger: PassengerInfo
    boardingTime: str
    qrCode: str

class CreateFlightRequest(BaseModel):
    flight_id: int
    seat: str
    ticket_number: str
    qr_code_link: str

# --- ENDPOINT C (Create) ---
@app.post("/api/flights", status_code=201)
def create_flight(
    req: CreateFlightRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1) Comprova que el vol existeix
    flight = db.query(Flight).filter(Flight.id == req.flight_id).first()
    if not flight:
        raise HTTPException(404, "Vol no trobat.")

    # 2) Crea el ticket
    ticket = Ticket(
        flight_id    = req.flight_id,
        user_id      = current_user["id"],
        seat         = req.seat,
        number       = req.ticket_number,
        qr_code_link = req.qr_code_link
    )
    db.add(ticket)
    db.commit()
    return {"message": "Vol afegit correctament al teu compte"}

# --- ENDPOINT R (Read) ---
@app.get("/api/flights", response_model=List[FlightResponse])
def get_flights(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    rows = (
        db.query(Flight, Airline, Ticket)
          .join(Ticket,  Ticket.flight_id  == Flight.id)
          .join(Airline, Airline.id         == Flight.airline_id)
          .filter(Ticket.user_id == current_user["id"])
          .all()
    )

    out = []
    for flight, airline, ticket in rows:
        out.append(FlightResponse(
            id            = str(flight.id),
            airline       = airline.name,
            airlineImage  = AirlineImage(uri=f"https://ruta-teva.com/{airline.image}"),
            flightNumber  = flight.flight_number,
            route         = RouteInfo(
                origin           = flight.origin_code,
                originName       = flight.origin_name,
                destination      = flight.destination_code,
                destinationName  = flight.destination_name,
                departureTime    = f"{flight.date}T{flight.departure_time}",
                arrivalTime      = f"{flight.date}T{flight.arrival_time}"
            ),
            passenger     = PassengerInfo(
                seat         = ticket.seat,
                ticketNumber = ticket.number
            ),
            boardingTime  = f"{flight.date}T{flight.boarding_time}",
            qrCode        = ticket.qr_code_link
        ))

    return out

# --- ENDPOINT D (Delete) ---
@app.delete("/api/flights/{flight_id}")
def delete_flight(
    flight_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ticket = (
        db.query(Ticket)
          .filter(Ticket.flight_id == flight_id,
                  Ticket.user_id   == current_user["id"])
          .first()
    )
    if not ticket:
        raise HTTPException(404, "No tens aquest vol reservat")
    db.delete(ticket)
    db.commit()
    return {"message": "Vol eliminat correctament"}
