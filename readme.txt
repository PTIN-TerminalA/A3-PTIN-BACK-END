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