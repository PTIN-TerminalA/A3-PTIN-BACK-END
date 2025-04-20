# app/test_insert_cars.py

import asyncio
from app.mongodb import connect_mongo

async def main():
    db = await connect_mongo()
    # Prepara los 10 coches
    cars = [
        {"_id": f"C{i}", "state": "Disponible", "battery": 100.0}
        for i in range(10)
    ]
    # Inserta muchos documentos a la vez
    result = await db["car"].insert_many(cars)
    print("Inserted car IDs:", result.inserted_ids)

if __name__ == "__main__":
    asyncio.run(main())
