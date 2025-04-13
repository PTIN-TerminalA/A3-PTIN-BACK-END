from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware #per fer que el backend sigui accessible des del frontend

app = FastAPI()

# Configurar CORS para permitir solicitudes desde el frontend de React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto a ["http://localhost:5173"] en desarrollo si usas Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta de prueba
@app.get("/")
def read_root():
    return {"message": "¡Hola, FastAPI está funcionando!"}

@app.get("/api/hello")
async def say_hello():
    return {"message": "Hola desde FastAPI a React"}

# Modelo de datos con Pydantic
class Item(BaseModel):
    name: str
    price: float

# Endpoint para recibir datos tipo JSON desde React
@app.post("/items/")
def create_item(item: Item):
    return {"name": item.name, "price": item.price, "message": "Item creado correctamente"}




# Per fer que el backend sigui accessible des del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Cambia esto si el frontend está en otro dominio
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],
)