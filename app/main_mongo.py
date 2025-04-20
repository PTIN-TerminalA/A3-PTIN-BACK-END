# app/main_mongo.py

import os
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

from app.mongodb import connect_mongo, get_db  # Conexión a MongoDB
from app.reserves.router import Route     # Tu modelo Pydantic de la reserva

app = FastAPI()

# 🔓 Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Origen del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Función auxiliar para convertir ObjectIds a str
def convert_objectid(o):
    if isinstance(o, ObjectId):
        return str(o)
    return o

def serialize_mongo_doc(doc: dict) -> dict:
    """
    Recorre un documento de Mongo y convierte todos los ObjectId a string.
    """
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, dict):
            out[k] = serialize_mongo_doc(v)
        elif isinstance(v, list):
            out[k] = [convert_objectid(item) if not isinstance(item, dict) else serialize_mongo_doc(item) for item in v]
        else:
            out[k] = v
    return out

# 🟢 Ruta de test
@app.get("/")
async def read_root():
    return {"message": "Welcome to the MongoDB app!"}

# 🚗 Endpoint para crear una reserva programada
@app.post("/reserves/programada")
async def create_route(route: Route, db=Depends(get_db)):
    # Preparamos el documento a insertar
    route_data = {
        "start_location": route.start_location,
        "end_location": route.end_location,
        "vehicle_id": route.vehicle_id,
        "scheduled_time": route.scheduled_time
    }
    # Insertamos en la colección 'route' (asegúrate de que sea 'route' y no 'routes')
    result = await db["route"].insert_one(route_data)

    # Recuperamos el documento completo, incluida la _id
    inserted = await db["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(status_code=500, detail="No s'ha pogut recuperar la reserva insertada")

    # Serializamos para devolver JSON compatible
    salida = serialize_mongo_doc(inserted)
    return {
        "message": f"Reserva programada de {route.start_location} a {route.end_location} guardada!",
        "data": salida
    }

# Si quieres probar la conexión desde CLI
if __name__ == "__main__":
    async def main():
        db = await connect_mongo()
        print("Coleccions disponibles:", await db.list_collection_names())
    asyncio.run(main())
