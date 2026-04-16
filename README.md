# CAMTOMV2 API (Integralaia)

API FastAPI para procesamiento de facturas con extracción OCR vía Integralaia.

## Ejecutar

```bash
python -m uvicorn consolidado:app --host 0.0.0.0 --port 8000
```

> También puedes usar: `python -m uvicorn consolidado:app --env-file .env --host 0.0.0.0 --port 8000`

## Variables de entorno

Requeridas:
- `INTEGRALAIA_BASE_URL`
- `INTEGRALAIA_API_KEY`

Opcionales:
- `INTEGRALAIA_TIMEOUT` (default `60`)
- `INTEGRALAIA_EXTRACTION_TIMEOUT` (default `180`)

La aplicación intenta cargar automáticamente `./.env`.

## Endpoints principales

### 1) Iniciar procesamiento

`GET /checkfactura/{docimpoid}`

Respuesta:
```json
{
  "status": "processing",
  "docimpoid": "416792",
  "request_id": "...",
  "status_endpoint": "/checkfactura-estado/..."
}
```

### 2) Consultar estado detallado

`GET /checkfactura-estado/{request_id}`

Incluye resumen (`ok`, `error`, `saltadas`) y detalle por factura procesada.

## Compatibilidad

Por compatibilidad temporal aún existen rutas legacy ocultas del schema:
- `/procesarfactura/{docimpoid}`
- `/procesarfactura-estado/{request_id}`
