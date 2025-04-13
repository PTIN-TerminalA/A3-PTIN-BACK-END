Para poder utilizar bien todo el entorno de desarrollo es crucial seguir los siguientes pasos:

1. Crear el entorno virtual en la raiz del proyecto
    - python3 -m venv venv

2. Iniciar el entorno virtual (se debe hacer siempre que nos pongamos a trabajar)
    Linux --> source venv/bin/activate 
    Windows --> venv\Scripts\activate

3. Instalar las dependencias del proyecto
    pip install -r requirements.txt

IMPORTANTE

En el gitignore se especifica que no se tiene que subir el entorno viirtual (la carpeta venv)
Esto se tiene que dejar como está, ada uno tiene que tener su propio entorno virtual.


Es necesario que para que el script database.py todos tengais un archivo con el nombre .env en la raiz del pryecto.
En este archivo se pondran las credenciales de la bdd que tengamos que utilizar de la siguiente forma:

DB_HOST=hostname
DB_PORT=portnumber
DB_USER=root
DB_PASSWORD=contraseña
DB_NAME=nombrebdd

Esto se hace asi para no publicar en el repositorio las claves de acceso a la base de datos.
Obviamente, el archivo .env estará en el .gitignore.
