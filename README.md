## Ejecucion del servidor:
    python -m uvicorn consolidado:app --host 0.0.0.0 --port 8000

## Variables de entorno requeridas (Integralaia)

Este servicio ahora usa únicamente Integralaia para extracción de facturas.
Antes de iniciar, define:

- `INTEGRALAIA_BASE_URL`
- `INTEGRALAIA_API_KEY`

Opcionales:

- `INTEGRALAIA_TIMEOUT` (default `60`)
- `INTEGRALAIA_EXTRACTION_TIMEOUT` (default `180`)

El servicio intenta cargar automáticamente `./.env` al iniciar.  
También puedes iniciar con: `python -m uvicorn consolidado:app --env-file .env --host 0.0.0.0 --port 8000`


-----------------------------------------------------------------------


    curl -X GET "https://apps.abcrepecev.com:1901/API-ABC/procesarfactura.php?id=xxxxxx

## Descripcion general
Este endpoint inicia el procesamiento de una o varias facturas asociadas a un identificador DocImpoID. 
El procesamiento se realiza en segundo plano utilizando el sistema de tareas BackgroundTasks de FastAPI, 
permitiendo que el cliente reciba una respuesta inmediata mientras el sistema continúa trabajando de forma asíncrona.


------------------------------------------------------------------------


    curl -X GET "https://apps.abcrepecev.com:1901/API-ABC/procesoclasificacion.php?id=xxxxxx

## Descripcion general
Este endpoint inicia un proceso automatizado de clasificación arancelaria de ítems relacionados a un documento de importación identificado por DocImpoID.
El proceso se ejecuta en segundo plano, 
permitiendo una respuesta inmediata mientras se realiza la actualización en base de datos con la clasificación sugerida por un modelo o proceso.


------------------------------------------------------------------------


    curl -X POST "https://apps.abcrepecev.com:1901/API-ABC/procesoexcel.php" -H "Content-Type: application/x-www-form-urlencoded" -d "ruta=xxxxxx.xlsx&idmaestro=xxxxxx

## Descripcion general
Este endpoint recibe una ruta de archivo Excel y un id de maestro (idmaestro) para:
- Leer el archivo Excel.
- Procesar los datos en segundo plano (background).
- Clasificar productos y actualizar la base de datos con esa información.
