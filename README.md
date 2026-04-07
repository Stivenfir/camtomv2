## API limpia para procesamiento de facturas (Integralaia)

### Qué quedó en el repositorio
Solo se dejaron los archivos necesarios para el flujo de API y procesamiento:
- `consolidado.py` (FastAPI + flujo de procesamiento y tracking TK en SQL Server)
- `extractgeneral.py` (OCR de factura usando Integralaia)
- `integralaia_provider.py` (cliente del proveedor Integralaia)
- `snippedtexto.py`, `jsonaxlsx.py`, `xlsxprocesotiempos.py` (módulos auxiliares del flujo existente)
- `requirements.txt`

Se creó carpeta de entrada para pruebas manuales:
- `facturas_entrada/`

---

## Variables de entorno Integralaia
Configura antes de levantar la API:

- `INTEGRALAIA_BASE_URL` (ej: `https://dev-visado-api-abcrepecev.integralaia.com`)
- `INTEGRALAIA_API_KEY`
- `INTEGRALAIA_DOCUMENT_TYPE_CODE` (default: `FACTURACOMERCIAL`)

---

## Ejecución
```bash
python -m uvicorn consolidado:app --host 0.0.0.0 --port 8000
```

---

## Endpoints principales
- `GET /procesarfactura/{docimpoid}`
- `GET /procesoclasificacion/{docimpoid}`
- `POST /procesoexcel`

El flujo de `/procesarfactura/{docimpoid}` mantiene la lógica de tracking TK y tablas SQL existentes.

---

## Prueba recomendada
1. Subir una factura PDF en la ruta/carpeta que ya consume tu proceso en SQL (o usar `facturas_entrada/` como carpeta de staging manual).
2. Asegurar que el registro esté creado en `IA_IM_ProcesarFacturasIA` para el `docimpoid`.
3. Disparar:
```bash
curl -X GET "http://localhost:8000/procesarfactura/{docimpoid}"
```
