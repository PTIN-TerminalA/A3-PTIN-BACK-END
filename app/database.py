from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde un archivo .env
load_dotenv()

# Cadena de conexión a la base de datos (será configurada en el archivo .env)
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el engine de SQLAlchemy con la URL de la base de datos
engine = create_engine(DATABASE_URL)

# Configuración de la sesión para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base para los modelos
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()