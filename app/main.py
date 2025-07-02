from fastapi import APIRouter, Request
import requests

router = APIRouter()

# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Query, Body, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import timedelta
from argon2 import PasswordHasher
from bson import ObjectId
from fastapi import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import websockets
import json
import threading
from fastapi import WebSocket, WebSocketDisconnect
from uuid import uuid4
from app.models.user import User
import smtplib
from email.mime.text import MIMEText
import os
import traceback

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

# --- Carrega de variables d'entorn ---
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

#from app.vehicles import router as vehicle_router
#app.include_router(vehicle_router)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(connect_and_listen())
    asyncio.create_task(connect_and_listen_cars())
    
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
    allow_origins=["https://flysy.software", "http://localhost:5173", "http://localhost", "http://192.168.10.10:5173", "http://192.168.10.10:3001","http://192.168.10.10", "http://projectevia-a.duckdns.org/", "flysy.software", "flysy.software/"],
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

#para seguridad
@app.get("/api/get-user-type")
async def get_user_type(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials  # Aquí ya tienes el token limpio, sin "Bearer "
    decoded = decode_access_token(token)
    user_id = decoded["sub"]

    regular = db.query(Regular).filter(Regular.id == user_id).first()
    admin = db.query(Admin).filter(Admin.id == user_id).first()

    if admin: 
        superadmin = db.query(Admin).filter(Admin.id == user_id, Admin.superadmin == True).first()
        if superadmin:
            return {"user_type": "superadmin"}
        else:
            return {"user_type": "admin"}
    elif regular:   
        return {"user_type": "regular"}
    else:
        return {"user_type": "non-assigned"}


#Aquest endpoint esborra l'admin amb id = admin_id
@app.delete("/api/admins/{admin_id}/full")
async def delete_admin_full(admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    user = db.query(User).filter(User.id == admin_id).first()

    if not admin and not user:
        raise HTTPException(404, "Admin o usuari no trobat")

    if admin:
        db.delete(admin)
    if user:
        db.delete(user)
    
    db.commit()
    return {"message": "Admin i usuari eliminats correctament"}

@app.get("/api/admins")
async def list_admins(db: Session = Depends(get_db)):
    admins = db.query(Admin).all()
    result = []
    for admin in admins:
        user = db.query(User).filter(User.id == admin.id).first()
        result.append({
            "id": admin.id,
            "superadmin": admin.superadmin,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "dni": user.dni
            } if user else None
        })
    return result


#Aquest endpoint ens reotrna la info de l'admin amb id = admin_id
@app.get("/api/admins/{admin_id}")
async def get_admin_details(admin_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == admin_id).first()
    admin = db.query(Admin).filter(Admin.id == admin_id).first()

    if not user or not admin:
        raise HTTPException(404, "Admin no trobat")

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "dni": user.dni,
    }

@app.get("/api/admins/search")
async def search_admins_by_name(apellido: str, db: Session = Depends(get_db)):
    results = (
        db.query(Admin)
        .join(User, Admin.id == User.id)
        .filter(User.name.ilike(f"%{apellido}%"))
        .all()
    )

    data = []
    for admin in results:
        user = db.query(User).filter(User.id == admin.id).first()
        data.append({
            "id": admin.id,
            "user": {
                "name": user.name,
                "email": user.email,
                "dni": user.dni
            }
        })
    return data

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
    ai_url = "http://10.60.0.3:2222/localizeUser" #Hay que canmbiarla en produccion por la que esté alojando la api de la IA

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

    # Preparar el diccionario de serveis per la petició a l'API de routing
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
    try:
        if not live_car_positions_and_state:
            print("❌ No hay coches disponibles (live_car_positions_and_state está vacío)")
            raise HTTPException(status_code=404, detail="No s'han trobat cotxes disponibles")

        car_dict = {}
        for car_id, car_info in live_car_positions_and_state.items():
            try:
                x = car_info[0]
                y = car_info[1]
                car_dict[str(car_id)] = [float(x), float(y)]
            except Exception as e:
                print(f"⚠️ Error al procesar la posición del coche {car_id}: {e}")

        if not car_dict:
            print("❌ No se pudieron extraer coordenadas válidas de los coches")
            raise HTTPException(status_code=404, detail="No s'han pogut obtenir coordenades dels cotxes")

        payload = {
            "position": [userLocation.x, userLocation.y],
            "request": car_dict
        }
        print(f"➡️ Enviando payload a servicio externo: {payload}")

        async with httpx.AsyncClient() as client:
            response = await client.post("http://10.60.0.3:1111/getNearest", json=payload)
            response.raise_for_status()

        nearest_data = response.json()
        print(f"⬅️ Respuesta recibida: {nearest_data}")

        return {"nearest_car_id": nearest_data["_id"]}
    except HTTPException:
        raise
    except Exception as e:
        print("❌ ERROR inesperado en get_nearest_car:")
        traceback.print_exc()
        detalle_error = str(e) or "Error inesperado sin mensaje"
        raise HTTPException(status_code=500, detail=detalle_error)







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




@app.post("/api/reserves/app-basic")
async def create_basic_route(
    payload: dict = Body(...),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),  # Descomenta cuando quieras usar autenticación
    db_sql: Session = Depends(get_db),
    db_mongo=Depends(get_mongo_db)
):
    """
    Endpoint que recibe:
    - location: { x: float, y: float }
    - end_location: string (nombre del servicio)

    1) Obtiene el servicio más cercano para ubicación del payload.
    2) Recupera sus coordenadas y llama a /controller/demana-cotxe.
    3) Crea la reserva en MongoDB con user_id.
    4) Devuelve estado del controlador y datos de la reserva.
    """
    
    # Autenticación por token (comentado por ahora)
    payload_token = decode_access_token(creds.credentials)
    user_id = int(payload_token.get("sub"))
    
    # 1) Validar y extraer ubicación del usuario
    loc = payload.get("location")
    if not loc or not isinstance(loc, dict):
        raise HTTPException(status_code=400, detail="Debes enviar 'location' amb 'x' i 'y'.")
    try:
        user_location = LocationSchema(x=loc["x"], y=loc["y"])
    except Exception:
        raise HTTPException(status_code=400, detail="Format inválid per a 'location'.")

    # 2) Validar end_location
    end_loc = payload.get("end_location")
    if not end_loc or not isinstance(end_loc, str):
        raise HTTPException(status_code=400, detail="Debes enviar 'end_location' (string).")

    # 3) Servicio más cercano
    nearest_resp = await getNearestService(user_location, db_sql)
    service_id = nearest_resp.get("nearest_service_id")
    if service_id is None:
        raise HTTPException(status_code=500, detail="No se obtuvo servicio cercano.")

    # 4) Buscar coche disponible y obtener su _id
    car = await db_mongo["car"].find_one({"state": "Disponible"})
    if not car:
        raise HTTPException(status_code=400, detail="No hay coches disponibles.")
    car_id = car["_id"]
    
    if not isinstance(car_id, int):
        raise HTTPException (status_code=500, detail =f"El _id del coche no es un entero: {car_id}")

    # 4) Recuperar coordenadas del servicio de SQL
    service_obj = db_sql.query(Service).filter(Service.id == service_id).first()
    if not service_obj:
        raise HTTPException(status_code=404, detail="Servicio no encontrado en base de datos.")
    target_x = float(service_obj.location_x)
    target_y = 1 - float(service_obj.location_y)  # Transformación: 1-y

    # 5) Llamada al controlador externo - CORREGIDO
    payload_ctrl = {
        "id": str(car_id),  # Usar car_id directamente como string
        "desti": {"x": target_x, "y": target_y}
    }
    try:
        async with httpx.AsyncClient() as client:
            controller_resp = await client.post(
                "http://192.168.10.11:8767/controller/demana-cotxe",
                json=payload_ctrl,
                timeout=5.0
            )
        try:
            ctrl_data = controller_resp.json()
        except ValueError:
            ctrl_data = controller_resp.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al llamar al controlador: {e}")

    # 6) Marcar el coche como 'Solicitat' tras la llamada
    await db_mongo["car"].update_one({"_id": car["_id"]}, {"$set": {"state": "Solicitat"}})

    # 7) Crear la reserva en MongoDB
    new_route = {
        "user_id": user_id,  # Ahora usa la variable user_id
        "start_location": service_obj.name,
        "end_location": end_loc,
        "scheduled_time": datetime.utcnow(),
        "state": "En curs",
        "car_id": car_id
    }
    result = await db_mongo["route"].insert_one(new_route)
    inserted = await db_mongo["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(status_code=500, detail="No se pudo crear la ruta en MongoDB.")

    # 8) Actualizar historial del usuario
    await db_mongo["user"].update_one(
        {"id": user_id},  # Ahora usa la variable user_id
        {"$push": {"route_history": inserted}, "$setOnInsert": {"id": user_id}},  # Aquí también
        upsert=True
    )

    # 9) Devolver los resultados
    return {
        "message": "Reserva creada i cotxe sol·licitat correctament.",
        "controller_status": controller_resp.status_code,
        "controller_data": ctrl_data,
        "reservation": serialize_mongo_doc(inserted),
        "car_id": str(car_id)
    }


@app.post("/api/inicia-trajecte")
async def inicia_trajecte(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),  # Descomenta cuando quieras usar autenticación
    db_mongo=Depends(get_mongo_db),
    db_sql: Session = Depends(get_db)
):
    try:
        # Autenticación por token (comentado por ahora)
        payload_token = decode_access_token(creds.credentials)
        user_id = int(payload_token.get("sub"))

        last_route = await db_mongo["route"].find_one(
            {"user_id": user_id},
            sort=[("scheduled_time", -1)]
        )
        if not last_route:
            raise HTTPException(404, "No s'ha trobat cap reserva activa per aquest usuari.")

        car_id = last_route.get("car_id")
        if not car_id:
            raise HTTPException(500, "Reserva sense cotxe assignat.")

        end_location = last_route.get("end_location")
        if not end_location or not isinstance(end_location, str):
            raise HTTPException(500, "La ruta no conté una 'end_location' vàlida.")

        # Limpiar espacios en blanco
        end_location_clean = end_location.strip()
        
        # Debug: mostrar què estem buscant
        print(f"Buscant servei: '{end_location_clean}'")
        
        # Búsqueda exacta (SQLAlchemy ORM maneja automáticamente las comillas)
        service = db_sql.query(Service).filter(Service.name == end_location_clean).first()
        
        if not service:
            # Si no encuentra, mostrar servicios similares para debugging
            all_services = db_sql.query(Service.name).all()
            service_names = [s.name for s in all_services if end_location_clean.lower() in s.name.lower()]
            
            if service_names:
                error_msg = f"No s'ha trobat exactament '{end_location_clean}'. Servicis similars trobats: {service_names[:5]}"
            else:
                # Mostrar algunos servicios para comparar
                sample_services = [s.name for s in all_services[:10]]
                error_msg = f"No s'ha trobat '{end_location_clean}'. Exemples de serveis disponibles: {sample_services}"
            
            raise HTTPException(404, error_msg)

        try:
            x = float(service.location_x)
            y = 1-float(service.location_y)
        except Exception as e:
            raise HTTPException(500, f"Error al convertir coordenades a float: {e}")

        async with httpx.AsyncClient() as client:
            put_response = await client.put(
                f"http://192.168.10.10:8000/api/cotxe/{car_id}/en_curs",
                timeout=5.0
            )
            put_response.raise_for_status()

            payload_ctrl = {
                "id": str(car_id),  # Usar car_id directamente como string
                "desti": {"x": x, "y": y}
            }

            controller_response = await client.post(
                "http://192.168.10.11:8767/controller/demana-cotxe",
                json=payload_ctrl,
                # json={"x": x, "y": y, "desti": {"x": x, "y": y}},
                timeout=5.0
            )
            controller_response.raise_for_status()

        return {
            "message": "Trajecte iniciat correctament.",
            "car_id": str(car_id),
            "destinacio": {"x": x, "y": y}
        }

    except Exception as e:
        # Temporalment, per a veure què passa
        raise HTTPException(status_code=500, detail=f"Error intern: {str(e)}")


@app.post("/api/finalitza-trajecte")
async def finalitza_trajecte(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),  # Descomenta cuando quieras usar autenticación
    db_mongo=Depends(get_mongo_db),
    db_sql: Session = Depends(get_db)
):
    """
    Finalitza el trajecte actual del usuario:
    1) Troba la ruta més recent del usuario
    2) Canvia l'estat del cotxe a "Disponible"
    3) Canvia l'estat de la ruta a "Finalitzada"
    """
    try:
        # Autenticación por token (comentado por ahora)
        payload_token = decode_access_token(creds.credentials)
        user_id = int(payload_token.get("sub"))

        # 1) Buscar la ruta más reciente del usuario que esté "En curs"
        last_route = await db_mongo["route"].find_one(
            {"user_id": user_id, "state": "En curs"},
            sort=[("scheduled_time", -1)]
        )
        
        if not last_route:
            raise HTTPException(404, "No s'ha trobat cap trajecte actiu per finalitzar.")

        car_id = last_route.get("car_id")
        if not car_id:
            raise HTTPException(500, "El trajecte no té un cotxe assignat.")

        # 2) Cambiar estado del coche a "Disponible"
        car_update_result = await db_mongo["car"].update_one(
            {"_id": car_id},
            {"$set": {"state": "Disponible"}}
        )
        
        if car_update_result.matched_count == 0:
            raise HTTPException(404, f"No s'ha trobat el cotxe amb ID {car_id}.")

        # 3) Cambiar estado de la ruta a "Finalitzada"
        route_update_result = await db_mongo["route"].update_one(
            {"_id": last_route["_id"]},
            {"$set": {"state": "Finalitzada"}}
        )
        
        if route_update_result.matched_count == 0:
            raise HTTPException(500, "No s'ha pogut actualitzar l'estat de la ruta.")

        # 4) Actualizar también el historial del usuario
        await db_mongo["user"].update_one(
            {"id": user_id, "route_history._id": last_route["_id"]},
            {"$set": {"route_history.$.state": "Finalitzada"}}
        )

        return {
            "message": "Trajecte finalitzat correctament.",
            "car_id": str(car_id),
            "route_id": str(last_route["_id"]),
            "end_location": last_route.get("end_location", "Desconegut")
        }

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Error intern: {str(e)}")


# --- POST /reserves/usuari (reservacotxe) ---
@app.post("/api/reserves/usuari")
async def create_route_user(
    route: Route,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db),
    db_sql: Session = Depends(get_db)
):
    # 1) Obtener user_id desde token
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # 2) Obtener coordenadas del punto de recogida usando el endpoint existente
    print(f"🔍 Buscando coordenadas para el punto de recogida: {route.start_location}")
    start_location_resp = await get_establishment_position(route.start_location, db_sql)
    print(f"📍 Coordenadas obtenidas: {start_location_resp}")
    x_coord = start_location_resp["location_x"]
    y_coord = start_location_resp["location_y"]
    print(f"✅ Coordenadas asignadas: x={x_coord}, y={y_coord}")

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
    doc = { api/
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
    + birth_date, phone_num, identity (tabla Regular) si existe.
    """
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # 1) Datos de User
    user: User = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuari no trobat")

    # 2) Datos de Regular (puede ser None si es admin)
    regular: Regular = db.query(Regular).filter(Regular.id == user_id).first()

    profile = {
        "name": user.name,
        "email": user.email
    }
    if regular:
        profile.update({
            "birth_date": regular.birth_date.isoformat(),
            "phone_num": regular.phone_num,
            "identity": regular.identity
        })
    return profile

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
@app.put("/api/cotxe/{cotxe_id}/esperant")
async def state_car_waiting(cotxe_id: str, db=Depends(get_mongo_db)):
    
    query_id = cotxe_id

    car = await db["car"].find_one({"_id": query_id})

    # 2) Si no el troba i cotxe_id era tot dígits, prova com a número
    if not car and cotxe_id.isdigit():
        query_id = int(cotxe_id)
        car = await db["car"].find_one({"_id": query_id})

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
@app.put("/api/cotxe/{cotxe_id}/en_curs")
async def state_car_in_progress(cotxe_id: str, db=Depends(get_mongo_db)):
   
    query_id = cotxe_id

    car = await db["car"].find_one({"_id": query_id})

    # 2) Si no el troba i cotxe_id era tot dígits, prova com a número
    if not car and cotxe_id.isdigit():
        query_id = int(cotxe_id)
        car = await db["car"].find_one({"_id": query_id})

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
@app.put("/api/cotxe/{cotxe_id}/solicitat")
async def state_car_requested(cotxe_id: str, db=Depends(get_mongo_db)):
   
    query_id = cotxe_id

    car = await db["car"].find_one({"_id": query_id})

    # 2) Si no el troba i cotxe_id era tot dígits, prova com a número
    if not car and cotxe_id.isdigit():
        query_id = int(cotxe_id)
        car = await db["car"].find_one({"_id": query_id})

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
@app.put("/api/cotxe/{cotxe_id}/disponible")
async def state_car_available(cotxe_id: str, db=Depends(get_mongo_db)):
   
    query_id = cotxe_id

    car = await db["car"].find_one({"_id": query_id})

    # 2) Si no el troba i cotxe_id era tot dígits, prova com a número
    if not car and cotxe_id.isdigit():
        query_id = int(cotxe_id)
        car = await db["car"].find_one({"_id": query_id})

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





live_car_positions_and_state = {}

async def connect_and_listen():
    uri = "ws://192.168.10.11:8766"
    print(f"Intentando conectar a WebSocket en {uri}")
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Conectado al WebSocket remoto")
                async for message in websocket:
                    data = json.loads(message)
                    # Nuevo parsing acorde al mensaje real:
                    car_id  = str(data.get("id"))
                    state   = data.get("state")
                    coords  = data.get("coordinates", {})
                    x       = coords.get("x")
                    y       = coords.get("y")
                    
                    if car_id and x is not None and y is not None and state is not None:
                        live_car_positions_and_state[car_id] = (float(x), float(y), str(state))
                        print(f"🚗 Posición guardada: {car_id} -> ({x}, {y}, {state})")
                    else:
                        print(f"⚠️ Datos incompletos en mensaje: {data}")

        except Exception as e:
            print(f"⚠️ Error de conexión: {e} — Reintentando en 5 segundos...")
            await asyncio.sleep(5)
#-------------------------Endpoints localizacion e IA-----------------------------------

#para comprobar si se llena el diccionario
@app.get("/api/debug/live-car-positions")
async def debug_live_car_positions():
    """
    Devuelve el estado interno de live_car_positions_and_state
    para que puedas ver si está vacío o qué contiene.
    """
    # Convierte las claves a string para JSON
    return {
        "count": len(live_car_positions_and_state),
        "cars": {
            str(k): {
                "x": v[0],
                "y": v[1],
                "state": v[2]
            }
            for k, v in live_car_positions_and_state.items()
        }
    }




#para la app

@app.get("/api/cotxe/{cotxe_id}/status")
async def get_car_status(
    cotxe_id: str,
    db=Depends(get_mongo_db)
):
    # 1) Intentar obtener la posición con la clave string
    pos = live_car_positions_and_state.get(cotxe_id)
    if pos is None:
        # 1b) Si no existe, probar con entero
        try:
            pos = live_car_positions_and_state.get(int(cotxe_id))
        except ValueError:
            pos = None

    if pos is None:
        raise HTTPException(status_code=404, detail=f"No s'ha trobat la posició del cotxe {cotxe_id}")

    # 2) Obtener estado desde MongoDB (si lo necesitas)
    # car_doc = await db["car"].find_one({"_id": cotxe_id}, {"state": 1})
    # state = car_doc.get("state") if car_doc else None

    # 3) Devolver resultado
    return {
        "car_id": cotxe_id,
        "position": {
            "x": pos[0],
            "y": pos[1]
        },
        "state": pos[2]
    }

# Endpoint para obtener el id de un servicio dado su nombre
# Uso: /api/service-id?name="nombredelservicio"
# Devuelve: {id: 123}
# Ej: curl "http://localhost:8000/api/service-id?name=ZARA"
# {"detail":"Servicio no encontrado"}
# curl "http://localhost:8000/api/service-id?name=Haribo"
# {"id":1}
@app.get("/api/service-id")
async def get_service_id(name: str, db: Session = Depends(get_db)):
    """
    Endpoint para obtener el ID de un servicio dado su nombre.
    Devuelve un objeto con el ID del servicio.
    """
    try:
        print(f"Buscando ID del servicio con nombre: {name}")

        # Consultar la base de datos para obtener el ID del servicio
        service = db.execute(
            text("SELECT id FROM service WHERE LOWER(name) = LOWER(:name)"),
            {"name": name}
        ).fetchone()

        print(f"Resultado de la consulta: {service}")

        if not service:
            print("Servicio no encontrado")
            raise HTTPException(status_code=404, detail="Servicio no encontrado")

        print(f"ID encontrado: {service[0]}")

        return {"id": service[0]}

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP para que sean manejadas correctamente
        raise http_exc
    except Exception as e:
        # Manejar errores generales
        print(f"Error al consultar la base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al consultar la base de datos")

# Endpoint para obtener todas las valoraciones de un servicio
# Uso: /api/service-ratings?service_id=1
# Devuelve: { "service_id": 1, "ratings": [{"rating": 5, "comment": "Excelente servicio."}, ...] }
@app.get("/api/service-ratings")
async def get_service_ratings(service_id: int, db: Session = Depends(get_db)):
    """
    Endpoint para obtener todas las valoraciones de un servicio dado su ID.
    Devuelve una lista de valoraciones con puntuación y comentario.
    """
    # Comprobar si el servicio existe
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        print(f"Servicio con ID {service_id} no encontrado.")
        raise HTTPException(status_code=404, detail="Servei no trobat.")

    # Obtener las valoraciones del servicio
    ratings = db.query(Valoration).filter(Valoration.service_id == service_id).all()
    if not ratings:
        print(f"No se encontraron valoraciones para el servicio con ID {service_id}.")
        raise HTTPException(status_code=404, detail="No s'han trobat valoracions per aquest servei.")

    # Formatear las valoraciones
    response = [
        {"rating": rating.value, "comment": rating.description}
        for rating in ratings
    ]
    return {"service_id": service_id, "ratings": response}

# Endoint para hacer una valoracion de un servicio
# Uso: 
""" 
  const _uri = "http://localhost:8000";
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const token = Cookies.get("token");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('service_id', serviceId);
      formData.append('rating', rating);
      formData.append('comment', comment);
      const res = await fetch(`${_uri}/api/rate-service`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      if (!res.ok) throw new Error("Error enviant la valoració");
      setLoading(false);
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };
"""
@app.post("/api/rate-service")
async def rate_service(
    service_id: int = Form(...),
    rating: float = Form(...),
    comment: str = Form(None),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """
    Endpoint para valorar un servicio.
    - service_id: ID del servicio a valorar.
    - rating: Valoración del servicio (0.01 - 5).
    - comment: Comentario opcional sobre el servicio.
    """
    # Validar rango de rating - Error 422 (Unprocessable Entity)
    if rating < 0.01 or rating > 5:
        raise HTTPException(
            status_code=422, 
            detail="La valoració ha de ser entre 0.01 i 5.00."
        )

    # Decodificar el token para obtener el user_id
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    # Comprobar si el servicio existe
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Servei no trobat.")

    # Comprobar si el usuario ya ha valorado este servicio - Error 409 (Conflict)
    existing_rating = db.query(Valoration).filter(
        Valoration.service_id == service_id,
        Valoration.user_id == user_id
    ).first()
    if existing_rating:
        raise HTTPException(
            status_code=409, 
            detail="Ja has valorat aquest servei."
        )

    # Crear la valoración
    new_rating = Valoration(
        service_id=service_id,
        user_id=user_id,
        value=rating,
        description=comment
    )
    db.add(new_rating)
    db.commit()

    return {
        "message": "Valoració afegida correctament",
        "service_id": service_id,
        "user_id": user_id,
        "rating": rating,
        "comment": comment
    }

# Endpoint para añadir una valoración y comentario a una ruta.
# Uso: 
"""
  const _uri = "http://localhost:8000";
  const handleEnviarValoracion = async (idx, reserva) => {
    const token = Cookies.get("token");
    const { rating, comment } = valoracions[idx] || {};
    if (!rating || !comment) {
      alert("Por favor, introduce una valoración y un comentario.");
      return;
    }
    try {
      const res = await fetch(`${_apiUrl}/api/route-rate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          scheduled_time: reserva.scheduled_time,
          rating: parseInt(rating),
          comment
        })
      });
      if (res.ok) {
        alert("Valoración añadida correctamente");
      } else {
        const err = await res.json();
        alert("Error al enviar valoración: " + (err.detail || res.statusText));
      }
    } catch (err) {
      alert("Error en el servidor: " + err.message);
    }
"""
@app.post("/api/route-rate")
async def rate_route(
    scheduled_time: str = Body(...),  # formato ISO
    rating: int = Body(...),
    comment: str = Body(...),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db = Depends(get_mongo_db)
):
    """
    Añade una valoración y comentario a una ruta de MongoDB.
    """
    # Obtener user_id desde el token
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))

    try:
        # Convertir la fecha a datetime
        sched_dt = datetime.fromisoformat(scheduled_time)
    except Exception:
        raise HTTPException(400, "scheduled_time debe ser un string ISO válido")

    # Buscar la ruta
    route = await db["route"].find_one({
        "user_id": user_id,
        "scheduled_time": sched_dt
    })
    if not route:
        raise HTTPException(404, "Ruta no encontrada")

    # Actualizar la ruta con los nuevos campos
    result = await db["route"].update_one(
        {"_id": route["_id"]},
        {"$set": {"valoracion": rating, "comentario": comment}}
    )
    if result.modified_count == 0:
        raise HTTPException(500, "No se pudo actualizar la ruta")

    return {"message": "Valoración añadida correctamente"}

# Endpoint para obtener las reservas de un usuario
@app.get("/api/user-reserves")
async def get_user_reserves(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_mongo_db)
):
    """
    Devuelve todas las reservas (rutas) de un usuario autenticado (por su token).
    """
    payload = decode_access_token(creds.credentials)
    user_id = int(payload.get("sub"))
    cursor = db["route"].find({"user_id": user_id})
    reservas = [serialize_mongo_doc(doc) async for doc in cursor]
    return {"reserves": reservas}

# WebSocket para recibir actualizaciones de posición de coches
# Lista de websockets conectados
connected_websockets = set()

# Uso:
# 1. Conectar al WebSocket: ws://localhost:8000/ws/cars
# 2. Procesar mensaje con formato JSON:
# {
# 'id': 879467412, 
# 'state': 'moving', 
# 'checkup': {'collision': 'false', 'motherboard': 'TODO'},
# 'coordinates': {'x': 0.4202597402597403, 'y': 0.10962767957878902}
# }

@app.websocket("/ws/cars")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            # Espera mensajes del cliente (opcional, aquí solo hacemos broadcast)
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)

# 👂 Cliente que se conecta al WebSocket remoto y escucha mensajes
async def connect_and_listen_cars():
    print("🔗 Conectando al WebSocket remoto para recibir posiciones de coches...")
    uri = "ws://192.168.10.11:8766"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Conectado al WebSocket remoto")
                async for message in websocket:
                    data = json.loads(message)
                    print("📨 Mensaje recibido:", data)
                    # Broadcast a todos los clientes conectados
                    to_remove = set()
                    for ws in connected_websockets:
                        try:
                            await ws.send_json(data)
                        except Exception:
                            to_remove.add(ws)
                    connected_websockets.difference_update(to_remove)
        except Exception as e:
            await asyncio.sleep(5)
            
            
# Diccionario en memoria para los tokens de recuperación (idealmente en BBDD)
recovery_tokens = {}  # token: (email, expiración)

@app.post("/api/recovery/request")
async def request_password_recovery(
    email: str = Form(...),
    dni: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, detail="Usuari no trobat")

    try:
        decrypted_dni = decrypt_dni(user.dni)
    except:
        raise HTTPException(500, detail="Error desencriptant el DNI")

    if decrypted_dni != dni:
        raise HTTPException(400, detail="DNI incorrecte")

    # Generar token i guardar temporalment
    token = str(uuid4())
    recovery_tokens[token] = {
        "email": email,
        "expires": datetime.utcnow() + timedelta(hours=1)
    }

    link = f"https://flysy.software/recovery/{token}"  # URL frontend
    await send_recovery_email(email, link)

    return {"message": "Correu enviat amb l'enllaç de recuperació"}


async def send_recovery_email(to_email: str, link: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.getenv("SMTP_USER")  # Exemple: el_teu_email@gmail.com
    smtp_pass = os.getenv("SMTP_PASS")  # Contrasenya d'aplicació generada

    if not smtp_user or not smtp_pass:
        raise ValueError("Falten credencials SMTP. Comprova les variables d'entorn SMTP_USER i SMTP_PASS.")

    msg = MIMEText(f"""
    Hola,

    Has sol·licitat recuperar la teva contrasenya. Clica al següent enllaç per establir-ne una de nova:

    {link}

    Si no has sol·licitat aquest canvi, ignora aquest correu.

    Salutacions,
    L'equip de Flysy
    """.strip())

    msg["Subject"] = "Recuperació de contrasenya"
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"No s'ha pogut enviar el correu: {str(e)}")
        
@app.post("/api/recovery/reset")
async def reset_password(
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if not token:
        raise HTTPException(status_code=400, detail="ERROR: token faltant")
    if not new_password:
        raise HTTPException(status_code=400, detail="ERROR: nova contrasenya faltant")

    token_info = recovery_tokens.get(token)
    if not token_info:
        raise HTTPException(status_code=400, detail="ERROR: token invàlid o no trobat")

    if token_info["expires"] < datetime.utcnow():
        del recovery_tokens[token]
        raise HTTPException(status_code=400, detail="ERROR: token caducat")

    user = db.query(User).filter(User.email == token_info.get("email")).first()
    if not user:
        raise HTTPException(status_code=404, detail="ERROR: usuari no trobat per email")

    common_passwords = load_common_passwords()
    if new_password in common_passwords:
        raise HTTPException(status_code=400, detail="ERROR: contrasenya massa comuna")

    try:
        user.password = hasher.hash(new_password)
        db.commit()
        del recovery_tokens[token]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ERROR: problema al guardar la nova contrasenya ({str(e)})")

    return {"message": "Contrasenya canviada correctament"}

            
            
#-------------------------Endpoints localizacion e IA-----------------------------------


#-------------------------Endpoints Users-----------------------------------------------



@app.delete("/api/users/{user_id}/full")
async def delete_user_full(user_id: int, db: Session = Depends(get_db)):
    # 1) Esborra directament les prefències a la taula 'preferences'
    db.execute(
        text("DELETE FROM preferences WHERE id = :id"),
        {"id": user_id}
    )

    # 2) Esborra la fila de Regular (dades addicionals)
    reg = db.query(Regular).filter(Regular.id == user_id).first()
    if reg:
        db.delete(reg)

    # 3) Esborra la fila de User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")
    db.delete(user)

    # 4) Commit unificat
    db.commit()

async def verify_admin_access(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de autorización requerido")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido")
    
    token = authorization.split(" ")[1]
    
    try:
        decoded = decode_access_token(token)
        user_id = decoded["sub"]
        
        admin = db.query(Admin).filter(Admin.id == user_id).first()
        if not admin:
            raise HTTPException(status_code=403, detail="Acceso denegado: se requieren permisos de administrador")
        
        return admin  # Retornamos el objeto admin por si lo necesitas
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

@app.get("/api/users")
async def list_users(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Admin = Depends(verify_admin_access),  # Esto verifica automáticamente los permisos
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    total = db.query(User).filter(User.usertype == 1).count()
    
    users_q = (
        db.query(User)
        .filter(User.usertype == 1)
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    result = []
    for u in users_q:
        reg = db.query(Regular).filter(Regular.id == u.id).first()
        plain_dni = u.dni
        
        result.append({
            "id": u.id,
            "name": u.name,
            "dni": plain_dni,
            "email": u.email,
            "birth_date": reg.birth_date.isoformat() if (reg and reg.birth_date) else None,
            "phone_num": reg.phone_num if reg else None,
            "identity": reg.identity if reg else None,
            "gender": reg.identity if reg else None,
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "users": result
    }

@app.get("/api/users/{user_id}")
async def get_user_details(user_id: int, db: Session = Depends(get_db)):
    """
    Retorna la informació completa d’un usuari:
      - name, email, dni              (de la taula User)
      - birth_date, phone_num, identity (de la taula Regular, si existeix)
    """
    # 1) Busquem l’usuari
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    # 2) Si té fila a Regular, l’agafem
    reg = db.query(Regular).filter(Regular.id == user_id).first()
    
    #decrypted_dni = decrypt_dni(user.dni)


    # 3) Retornem tots els camps
    return {
        "id":          user.id,
        "name":        user.name,
        "email":       user.email,
        "dni":         user.dni,
        "birth_date":  reg.birth_date.isoformat() if reg and reg.birth_date else None,
        "phone_num":   reg.phone_num if reg else None,
        "identity":    reg.identity  if reg else None,
        "gender":    reg.identity  if reg else None,
    }

@app.get("/api/users/search")
async def search_users_by_email(
    email: str = Query(..., description="Fragment a cercar dins l'email"),
    db: Session = Depends(get_db)
):
    users = (
        db.query(User)
          .filter(User.usertype == 1)
          .filter(User.email.ilike(f"%{email}%"))
          .all()
    )

    result = []
    for u in users:
        reg = db.query(Regular).filter(Regular.id == u.id).first()
        result.append({
            "id":         u.id,
            "name":       u.name,
            "dni":        u.dni,  # o plain_dni com abans
            "email":      u.email,
            "birth_date": reg.birth_date.isoformat() if (reg and reg.birth_date) else None,
            "phone_num":  reg.phone_num  if reg else None,
            "identity":   reg.identity   if reg else None,
            "gender":     reg.identity   if reg else None,
        })
    return result

@app.patch("/api/users/{editingId}/full")
async def update_user_full(
    editingId: int = Path(..., ge=1),
    name: Optional[str] = Body(None),
    birth_date: Optional[date] = Body(None),
    phone_num: Optional[str] = Body(None),
    gender: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    """
    Actualitza name (User) i birth_date, phone_num, identity (Regular).
    Cualsevol camp que vingui a null no es modifica.
    """
    # 1) Busquem l’usuari bàsic
    user = db.query(User).filter(User.id == editingId).first()
    if not user:
        raise HTTPException(404, "Usuari no trobat")

    # 2) Si ens arriba name, l’actualitzem
    if name is not None:
        user.name = name
        db.add(user)

    # 3) Busquem l’entrada Regular
    reg = db.query(Regular).filter(Regular.id == editingId).first()
    if not reg:
        raise HTTPException(404, "Dades addicionals no trobades")

    # 4) Actualitzem només els camps no nuls
    if birth_date is not None:
        reg.birth_date = birth_date
    if phone_num is not None:
        reg.phone_num = phone_num
    if gender is not None:
        reg.identity = gender

    db.add(reg)
    db.commit()

    return {
        "name":       user.name,
        "birth_date": reg.birth_date,
        "phone_num":  reg.phone_num,
        "gender":     reg.identity,
    }

@app.get("/api/cars", response_model=List[Dict[str, Any]])
async def list_cars(
    admin = Depends(verify_admin_access),   # ← Sólo admins pueden llegar aquí
    db=Depends(get_mongo_db)
):
    """
    Retorna tots els documents de la col·lecció `car`,
    amb els camps:
      - _id
      - state
      - battery_level  (el camp a Mongo és `battery`)
    """

    # Fem la consulta a Mongo
    cursor = db["car"].find({})
    carros = await cursor.to_list(length=None)

    # Construeix la resposta
    resultat = []
    for c in carros:
        resultat.append({
            "_id": str(c.get("_id")),
            "state": c.get("state"),
            "battery_level": c.get("battery"),
        })

    return resultat
    
@app.post("/api/chat-with-ia")
async def chat_with_ia(
    user_id: int = Form(...),
    user_message: str = Form(...),
    user_location_x: float = Form(...),
    user_location_y: float = Form(...)
):
    """
    Endpoint del nostre backend que fa de pont cap al servei d'IA.
    Rep les dades de l'usuari i les envia al microservei IA.
    """
    ia_url = "http://10.60.0.3:3333/ask_agent/"

    payload = {
        "user_id": user_id,
        "user_message": user_message,
        "user_location_x": user_location_x,
        "user_location_y": user_location_y
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ia_url,
                json=payload,
                timeout=httpx.Timeout(300.0)
            )
            response.raise_for_status()
            ia_reply = response.text.strip()
            if not ia_reply:
                raise HTTPException(status_code=500, detail="Resposta buida de la IA")
            return {"response": ia_reply}

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connectant amb la IA: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


#-------------------------Endpoints localizacion e IA-----------------------------------


@app.post("/api/chat_agent")
async def chat_agent_proxy(request: Request):
    data = await request.json()

    # Aquí haces la llamada a la API externa
    try:
        response = requests.post(
            "http://10.60.0.3:3333/ask_agent/",
            json=data,
            timeout=10000
        )
        return response.text
    except requests.RequestException as e:
        return {"error": "Error al contactar amb el agent extern."}
