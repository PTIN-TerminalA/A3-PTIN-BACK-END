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

Això posarà en marxa el servidor a `http://127.0.0.1:8000/` per defecte.  
La documentació interactiva està disponible a:  
➡️ `http://127.0.0.1:8000/docs`

---

## 🔐 Autenticació i usuaris

### `POST /api/register`
Registra un nou usuari.

### `POST /api/login`
Autentica un usuari registrat.

### `POST /api/register-login-google`
Login o registre a través de Google.

### `GET /api/get_user_id`
Obtén l'ID de l'usuari des d’un token.

### `POST /api/update-dni`
Actualitza el DNI de l’usuari.

### `GET /api/get-user-type`
Retorna el tipus d’usuari: `regular`, `admin`, `superadmin`, etc.

### `GET /api/profile`
Consulta el perfil complet de l’usuari.

### `PATCH /api/profile`
Actualitza el perfil de l’usuari.

---

## 🗺️ Serveis i tags

### `GET /api/getServices`
Llista de serveis disponibles.

### `GET /api/getPrices`
Preus dels serveis.

### `POST /api/getSchedules`
Horaris disponibles per un servei concret.

### `GET /api/getTags`
Tots els tags disponibles.

### `POST /api/getServiceTag`
Tag associat a un servei.

### `POST /api/getValoration`
Valoracions per a un servei.

---

## 📍 Localització i IA

### `POST /api/getUserPosition`
Rep mesures WiFi i retorna la posició estimada de l’usuari.

### `POST /api/getNearestService`
Rep una posició d’usuari i retorna la llista de serveis més propers (provisional).

---

## 🧭 Rutes i reserves (MongoDB)

### `GET /reserves`
Llista de reserves amb filtres opcionals: email, estat, dates, etc.

### `POST /reserves/usuari`
Crea una reserva com a usuari autenticat.

### `POST /reserves/programada`
Crea una reserva com a administrador.

### `PATCH /reserves/{reserve_id}`
Actualitza una reserva específica.

### `DELETE /reserves/{reserve_id}`
Elimina una reserva.

---

## 🧠 Routing i IA externa

### `GET /api/establishment-position`
Donat el nom d’un establiment, retorna la seva posició.

### `POST /api/shortest-path`
Calcula el camí més curt entre dos punts.

#### Cos de la sol·licitud:
```json
{
  "start": [x_start, y_start],
  "goal":  [x_goal,  y_goal]
}
```

#### Exemple amb `curl`:
```bash
curl -X POST "http://127.0.0.1:8000/api/shortest-path" \\
  -H "Content-Type: application/json" \\
  -d '{
    "start": [0.5016, 0.3987],
    "goal":  [0.5109, 0.3368]
  }'
```

#### Resposta:
```json
{
  "length": 273,
  "path": [
    [0.501, 0.398],
    [0.502, 0.397],
    ...
  ]
}
```

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

