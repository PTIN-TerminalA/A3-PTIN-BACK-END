## API de Reserves i Serveis amb FastAPI

---

## 📦 Dependències

Assegura't de tenir instal·lades les següents dependències:

* fastapi
* uvicorn
* sqlalchemy
* pydantic
* argon2-cffi
* motor
* requests
* httpx
* websockets

Pots instal·lar-les amb:

```bash
pip install -r requirements.txt
```

---

## 🚀 Execució de l'API

Pots arrencar el servidor amb:

```bash
uvicorn app.main:app --reload
```

La documentació interactiva està disponible a:
➡️ `http://127.0.0.1:8000/docs`

---

## 🔐 Autenticació i Usuaris

### `POST /api/register`

Registra un nou usuari.

#### Exemple

```json
{
  "name": "Joan",
  "dni": "12345678A",
  "email": "joan@example.com",
  "password": "segura123",
  "usertype": "regular"
}
```

### `POST /api/login`

Autentica un usuari registrat.

#### Exemple

```json
{
  "email": "joan@example.com",
  "password": "segura123"
}
```

### `POST /api/register-login-google`

Login o registre mitjançant Google.

### `GET /api/get_user_id`

Retorna l'`user_id` del token rebut com a paràmetre.

### `POST /api/update-dni`

Actualitza el DNI de l'usuari.

### `GET /api/get-user-type`

Retorna el tipus d'usuari (admin, regular, etc).

### `GET /api/profile`  /  `PATCH /api/profile`

Consulta o actualitza el perfil de l'usuari autenticat.

---

## 🗺️ Serveis i Etiquetes

### `GET /api/getServices`

Llista tots els serveis disponibles.

### `GET /api/getPrices`

Preus definits per servei.

### `POST /api/getSchedules`

Horaris disponibles d'un servei.

```json
{
  "service_id": 2
}
```

### `GET /api/getTags`

Tots els tags existents.

### `POST /api/getServiceTag`

Tag associat a un servei:

```json
{
  "service_id": 2
}
```

### `POST /api/getValoration`

Valoracions d'un servei:

```json
{
  "service_id": 2
}
```

---

## 📍 Localització i IA

### `POST /api/getUserPosition`

Retorna la posició estimada basat en mesures WiFi.

#### Exemple

```json
{
  "measures": [
    { "mac": "AA:BB:CC:DD:EE:01", "rssi": -50 },
    { "mac": "AA:BB:CC:DD:EE:02", "rssi": -60 }
  ]
}
```

### `POST /api/getNearestService`

Retorna serveis propers a una posició.

```json
{
  "x": 0.45,
  "y": 0.75
}
```

---

## 🛣️ Reserves (MongoDB)

### `GET /reserves`

Llista reserves amb filtres opcionals (email, estat, dates, etc).

### `POST /reserves/usuari`

Crea una reserva com a usuari autenticat.

### `POST /reserves/programada`

Crea una reserva com a administrador.

```json
{
  "user_email": "anna@example.com",
  "start_location": "entrada",
  "end_location": "sortida",
  "scheduled_time": "2025-06-01T12:00:00",
  "state": "Programada"
}
```

### `PATCH /reserves/{reserve_id}`

Actualitza una reserva.

### `DELETE /reserves/{reserve_id}`

Elimina una reserva.

---

## 🧠 IA i Routing Extern

### `GET /api/establishment-position`

Retorna la posició d'un establiment per nom.

### `POST /api/shortest-path`

Calcula el camí més curt entre dos punts.

#### Exemple

```json
{
  "start": [0.5, 0.4],
  "goal":  [0.6, 0.3]
}
```

---

## 🚗 Gestor d'Estats de Cotxe

### `PUT /cotxe/{cotxe_id}/esperant`

Canvia estat del cotxe a **"Esperant"**.

### `PUT /cotxe/{cotxe_id}/en_curs`

Canvia estat del cotxe a **"En curs"**.

### `PUT /cotxe/{cotxe_id}/solicitat`

Canvia estat del cotxe a **"Solicitat"**.

### `PUT /cotxe/{cotxe_id}/disponible`

Canvia estat del cotxe a **"Disponible"**.

---

## 📂 Estructura del projecte

```
A3-PTIN-BACK-END/
├── app/
│   ├── main.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── ...
├── requirements.txt
└── README.md
```

