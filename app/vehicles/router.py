from fastapi import APIRouter, Depends, HTTPException
from app.mongodb import get_db

router = APIRouter()

def serialize(doc):
    return {
        "_id": doc["_id"],        # así tu React sigue encontrando cotxe._id
        "state": doc["state"],
        "battery": doc["battery"],
    }

@router.get("/vehicles")
async def get_all_cars(db=Depends(get_db)):
    cars = []
    async for car in db["car"].find():
        cars.append(serialize(car))
    return cars

@router.patch("/vehicles/{car_id}")
async def update_car_state(car_id: str, data: dict, db=Depends(get_db)):
    result = await db["car"].update_one(
        {"_id": car_id},
        {"$set": {"state": data["state"]}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cotxe no trobat")
    return {"message": "Estat actualitzat"}
