from app.mongodb import connect_mongo

async def crear_reserva(data):
    db = await connect_mongo()
    # Guardar los datos de la reserva en la colección 'route'
    result = await db.route.insert_one(data)
    return result.inserted_id  # Devolver el ID del documento insertado

# Función para obtener todas las reservas (opcional, solo para comprobar)
async def obtener_reservas():
    db = await connect_mongo()
    reservas = await db.route.find().to_list(None)
    return reservas
