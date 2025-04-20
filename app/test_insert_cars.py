# test_insert_cars.py

from app.mongodb import get_db
from reserves.crud import create_initial_cars

def main():
    car_collection = db["car"]
    create_initial_cars(car_collection)
    print("🚗 Flota de coches inicial insertada (si no existía).")

if __name__ == "__main__":
    main()
