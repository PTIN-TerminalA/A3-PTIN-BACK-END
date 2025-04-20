# app/main_mongo.py

import asyncio
from bson import ObjectId
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.mongodb import get_db
from app.reserves.router import Route

app = FastAPI()

# 🔓 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
async def read_root():
    return {"message": "Welcome to the MongoDB app!"}

@app.post("/reserves/programada")
async def create_route(route: Route, db=Depends(get_db)):
    # convertimos todo el Pydantic model a dict
    doc = route.dict()
    result = await db["route"].insert_one(doc)
    inserted = await db["route"].find_one({"_id": result.inserted_id})
    if not inserted:
        raise HTTPException(status_code=500, detail="No s'ha pogut recuperar la reserva")
    salida = serialize_mongo_doc(inserted)
    return {
        "message": "Reserva confirmada amb èxit!",
        "data": salida
    }

# Para probar conexión desde CLI
if __name__ == "__main__":
    import os
    from app.mongodb import connect_mongo
    async def main():
        db = await connect_mongo()
        print("Coleccions disponibles:", await db.list_collection_names())
    asyncio.run(main())
