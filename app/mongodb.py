import os
import asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from typing import AsyncGenerator

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# URI de MongoDB desde .env
MONGO_URI = os.getenv("MONGO_URI")

# Conexión a la base de datos de MongoDB
async def connect_mongo():
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.get_default_database()
        return db
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión a MongoDB: {str(e)}")

# Función de dependencia para FastAPI
async def get_db() -> AsyncGenerator:
    db = await connect_mongo()
    try:
        yield db
    finally:
        # Cerrar la conexión al finalizar la petición
        db.client.close()

# Ejemplo de cómo acceder a colecciones
async def main():
    db = await connect_mongo()
    print("Colecciones disponibles:", await db.list_collection_names())

if __name__ == "__main__":
    asyncio.run(main())
