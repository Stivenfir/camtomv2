import requests
import os
import dotenv
import json

dotenv.load_dotenv()
url = "https://api.camtomx.com/api/v3/camtomdocs/extract?country_code=COL&json_schema=True"
API_KEY = "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2"

description = """
El documento es una Factura Comercial Internacional de comercio exterior. Contiene datos del exportador e importador, Incoterms, logística y una tabla detallada de mercancías que puede incluir clasificaciones aduaneras (Partida Arancelaria / HS Code). Imporante tomar en cuenta que los valores monetarios deben interpretarse asumiendo la coma como separador decimal y así escribirse en el schema,por ejemplo 1.543,00 -> 1543.00, sin usar puntos, ni ningun otro separador para milesimas
 
**Reglas Críticas de Extracción de Ítems:**
1. Enumeración: Respeta estrictamente la literalidad del documento. Si la tabla de productos no tiene una columna impresa con números de ítem (ej: 1, 2, 3...), no generes una secuencia artificial; deja el campo de enumeración vacío.
2. Posición de Orden de Compra (order_position): Este campo es condicional. Solo debes extraer valor si existe una columna explícita en el detalle de productos etiquetada como 'Orden de Compra', 'PO' o similar vinculada a cada línea. Si la Orden de Compra solo aparece en la cabecera general del documento y no por producto, el campo order_position de los ítems debe quedar nulo/vacío.
 
 
**IMPORTANTE - Orden de Compra:**
1. ENCABEZADO: Buscar el número principal de orden de compra en el encabezado del documento (etiquetas: 'Orden', 'Purchase Order', 'PO', 'Pedido'). Este va en purchase_order.number_po.
2. TABLA DE PRODUCTOS: Si existe una columna 'Orden Compra', 'OC', 'PO' en la tabla de productos, los valores de esa columna (ej: 'ODC 106725', 'ODC 105850') van en el campo 'order_position' de cada item. NO confundir con 'reference' que es para SKU/código de producto.
"""

schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Factura",
    "type": "object",
    "properties": {
        "factura": {
            "type": "object",
            "properties": {
                "invoiceNumber": {
                    "type": "string",
                    "description": "numero/id de la factura",
                    "pattern": "^[A-Z0-9_-]+$",
                    "minLength": 1,
                    "maxLength": 50,
                    "example": "INV-2025-0001",
                },
                "invoiceDate": {
                    "type": "string",
                    "description": "Fecha de emisión de la factura. Muchas veces se encuentra de manera diferente en los documentos. Puede ser: '25. JUL 2025', 'JUL 25, 2025', '25 JUL 2025', etc. El formato final debe ser DD/MM/YYYY",
                    "pattern": "^[0-9]{2}/[0-9]{2}/[0-9]{4}$",
                    "minLength": 10,
                    "maxLength": 11,
                    "example": "01/01/2025",
                },
                "incoterm": {
                    "type": "string",
                    "description": "Condición de entrega según Incoterms (por ejemplo, FOB, CIF, DDP)",
                    "pattern": "^[A-Z]{3}$",
                    "minLength": 3,
                    "maxLength": 3,
                    "example": "FOB",
                },
                "currency": {
                    "type": "string",
                    "description": "Código de la moneda de negociación en la que está expresada la factura. Debe ser un código ISO 4217 de 3 letras.",
                    "pattern": "^[A-Z]{3}$",
                    "minLength": 3,
                    "maxLength": 3,
                    "example": "USD",
                },
                "amount": {
                    "type": "string",
                    "description": "Subtotal de la factura antes de impuestos y cargos adicionales. ",
                    "pattern": "^\\d+(?:,\\d{1,2})?$",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "1000,00",
                },
                "total": {
                    "type": "string",
                    "description": "Total de la factura después de impuestos, flete y cargos adicionales.",
                    "pattern": "^\\d+(?:,\\d{1,2})?$",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "1000,00",
                },
                "freight_cost": {
                    "type": "string",
                    "description": "Costo del flete asociado a la factura, si aplica.",
                    "pattern": "^\\d+(?:,\\d{1,2})?$",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "1000,00",
                },
                "insurance": {
                    "type": "string",
                    "description": "Costo del seguro asociado a la factura, si aplica.",
                    "pattern": "^\\d+(?:,\\d{1,2})?$",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "1000,00",
                },
            },
            "required": [
                "invoiceNumber",
                "invoiceDate",
                "incoterm",
                "currency",
                "amount",
                "total",
            ],
        },
        "purchase_order": {
            "type": "object",
            "description": "Información de la orden de compra asociada a la factura. Buscar en el encabezado o sección de referencias del documento. Etiquetas comunes: 'Purchase Order', 'PO', 'P.O.', 'Orden de Compra', 'O.C.', 'OC', 'No. de Pedido', 'Pedido', 'Customer PO', 'Your Order', 'Order No.', 'Ref. Cliente'.",
            "properties": {
                "number_po": {
                    "type": ["string", "null"],
                    "description": "Número o código de la orden de compra del cliente. Buscar cerca de etiquetas como: 'PO Number', 'P.O. No.', 'Purchase Order', 'Orden de Compra', 'O.C.', 'Your Order No.', 'Customer PO', 'Pedido No.', 'Order Reference'. Usualmente aparece en el encabezado de la factura junto a la información de referencia. Puede tener formatos como: PO123456, 4500012345, OC-2024-001. Retornar null SOLO si definitivamente no existe ninguna referencia a orden de compra en el documento.",
                    "pattern": "^[A-Z0-9_-]+$",
                    "minLength": 1,
                    "maxLength": 50,
                    "example": "PO123456",
                },
                "date_po": {
                    "type": "string",
                    "nullable": True,
                    "description": "Fecha de la orden de compra. Buscar cerca de la etiqueta de orden de compra, puede aparecer como 'PO Date', 'Order Date', 'Fecha O.C.', 'Fecha de Pedido'. El formato final debe ser DD/MM/YYYY. Retornar null si no hay fecha específica para la orden de compra.",
                    "pattern": "^[0-9]{2}/[0-9]{2}/[0-9]{4}$",
                    "minLength": 10,
                    "maxLength": 11,
                    "example": "01/01/2025",
                },
                "position_po": {
                    "type": "string",
                    "nullable": True,
                    "description": "Posición o línea dentro de la orden de compra. Buscar en columnas como 'PO Line', 'Item', 'Pos.', 'Línea OC'. Retornar null si no existe esta información.",
                    "pattern": "^[A-Z0-9_-]+$",
                    "minLength": 1,
                    "maxLength": 10,
                    "example": "001",
                },
            },
        },
        "vendor": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "nullable": True,
                    "description": "Nombre del vendedor. E.g. Global Export Ltd.. Deberá ser null si no se encuentra explicitamente en el documento.",
                    
                    "minLength": 1,
                    "maxLength": 50,
                    "example": "John Doe Inc.",
                },
                "address": {
                    "type": "string",
                    "nullable": True,
                    "description": "Dirección del vendedor. E.g. 123 Export Rd, Hamburg, Germany. Deberá ser null si no se encuentra explicitamente en el documento.",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "123 Main St, Anytown, USA",
                },
                "legal_name": {
                    "type": "string",
                    "nullable": True,
                    "description": "Razón social del exportador o vendedor. E.g. Global Export Limited. Deberá ser null si no se encuentra explicitamente en el documento.",
                    
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "Global Export Limited",
                },
            },
        },
        "customer": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "nullable": True,
                    "description": "Nombre del cliente. E.g. John Doe Inc.. Deberá ser null si no se encuentra explicitamente en el documento.",
                    
                    "minLength": 1,
                    "maxLength": 50,
                    "example": "John Doe Inc.",
                },
                "address": {
                    "type": "string",
                    "nullable": True,
                    "description": "Dirección del cliente. E.g. 123 Export Rd, Hamburg, Germany. Deberá ser null si no se encuentra explicitamente en el documento.",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "123 Main St, Anytown, USA",
                },
            },
        },
        "discharge": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "nullable": True,
                    "description": "Dirección final del destinatario o entrega. E.g. 789 Delivery Blvd, Monterrey, Mexico.. Deberá ser null si no se encuentra explicitamente en el documento.",
                    
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "789 Delivery Blvd, Monterrey, Mexico",
                },
                "type": {
                    "type": "string",
                    "nullable": True,
                    "description": "Modo de transporte. Deberá ser null si no se encuentra explicitamente en el documento.",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "Aéreo",
                },
                "date": {
                    "type": "string",
                    "nullable": True,
                    "description": "Fecha de entrega o descarga estimada. en formato DD/MM/YYYY. E.g. 10/03/2024. Deberá ser null si no se encuentra explicitamente en el documento.",
                    "pattern": "^[0-9]{2}/[0-9]{2}/[0-9]{4}$",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "10/03/2024",
                },
            },
        },
        "delivery_place": {
            "type": "string",
            "nullable": True,
            "description": "Lugar de entrega. Puede ser ciudad o puerto. E.g. Veracruz, Hamburg. Deberá ser null si no se encuentra explicitamente en el documento.",
            "minLength": 1,
            "maxLength": 100,
            "example": "Veracruz",
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_position": {
                        "type": "string",
                        "description": "Posición del ítem en la factura. E.g. 001. Deberá ser null si no se encuentra explicitamente en el documento.",
                        "minLength": 0,
                        "maxLength": 1000,
                        "example": "001",
                    },
                    "order_position": {
                        "type": "string",
                        "description": "Número o código de la orden de compra asociada a este ítem/producto específico. IMPORTANTE: Buscar en columnas con encabezados como 'Orden Compra', 'OC', 'O.C.', 'PO', 'Purchase Order', 'Pedido', 'No. Pedido'. Los valores típicos tienen formato como 'ODC 106725', 'OC-12345', 'PO123456'. Este campo captura el código de orden de compra POR LÍNEA de producto. NO es lo mismo que 'reference'. Retornar null solo si no existe columna de orden de compra en la tabla.",
                        "minLength": 0,
                        "maxLength": 1000,
                        "example": "ODC 106725",
                    },
                    "reference": {
                        "type": "string",
                        "description": "Código SKU, número de parte o referencia interna del producto (NO es la orden de compra). Buscar en columnas como 'SKU', 'Part No.', 'Código', 'Ref. Producto', 'Item Code'. Retornar null si no existe este tipo de referencia de producto.",
                        "minLength": 0,
                        "maxLength": 1000,
                        "example": "PRD-12345",
                    },
                    "origin_country": {
                        "type": "string",
                        "description": "Priorizar el país de origen especificado a nivel ítem. Si no se encuentra explícitamente a nivel ítem, utilizar el país de origen indicado en la factura. Si no se menciona en ninguno de los dos casos, deberá ser null",
                        "minLength": 0,
                        "maxLength": 1000,
                        "example": "México",
                    },
                    "brand": {
                        "type": "string",
                        "description": "Marca del producto. E.g. Dell. Deberá ser null si no se encuentra explicitamente en el documento.",
                        "minLength": 0,
                        "maxLength": 1000,
                        "example": "Dell",
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripción detallada del producto o servicio facturado. Deberá ser null si no se encuentra explicitamente en el documento.",
                        "minLength": 0,
                        "maxLength": 1000,
                        "example": "Laptop Dell XPS 13, Intel i7, 16GB RAM, 512GB SSD",
                    },
                    "year_manufacture": {
                        "type": "integer",
                        "description": "Año de fabricación del producto. Deberá ser null si no se encuentra explicitamente en el documento.",
                        "example": 2023,
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Cantidad de unidades del producto o servicio facturado.",
                        "minimum": 0,
                        "example": 3,
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unidad de medida del producto o servicio (por ejemplo, pcs, kg, liters). Deberá ser null si no se encuentra explicitamente en el documento.",
                        "minLength": 0,
                        "maxLength": 20,
                        "example": "liters",
                    },
                    "unitPrice": {
                        "type": "string",
                        "description": "Precio unitario del producto o servicio (por ejemplo, 19954,99). Deberá ser null si no se encuentra explicitamente en el documento.",
                        "minLength": 1,
                        "maxLength": 20,
                        "pattern": "^\\d+(?:,\\d{1,2})?$",
                        "example": "19954,99",
                    },
                    "subTotal": {
                        "type": "string",
                        "description": "Subtotal del producto o servicio (por ejemplo, 599,97). Deberá ser null si no se encuentra explicitamente en el documento.",
                        "minLength": 1,
                        "maxLength": 20,
                        "pattern": "^\\d+(?:,\\d+)?$",
                        "example": "599,97",
                    },
                    "totalweight_kg": {
                        "type": ["string", "NULL"],
                        "description": "Peso bruto total del producto en kilogramos (por ejemplo, 1,5). Deberá ser null si no se encuentra explicitamente en el documento.",
                        "pattern": "^\\d+(?:,\\d{1,2})?$",
                        "example": "1,5",
                    },
                    "totalnetweight_kg": {
                        "type": "string",
                        "nullable": True,
                        "description": "Peso neto total del producto en kilogramos (por ejemplo, 1,2). Deberá ser null si no se encuentra explicitamente en el documento.",
                        "pattern": "^\\d+(?:,\\d{1,2})?$",
                        "example": "1,2",
                    },
                    "amount": {
                        "type": "string",
                        "description": "Valor total del producto o servicio (por ejemplo, 6599,97). Deberá ser null si no se encuentra explicitamente en el documento. Utilizar comas como separador decimal",
                        "pattern": "^\\d+(?:,\\d{1,2})?$",
                        "minLength": 1,
                        "maxLength": 100,
                        "example": "1000,00",
                    },
                },
                "required": [
                    "order_position",
                    "reference",
                    "origin_country",
                    "description",
                    "quantity",
                    "unitPrice",
                    "subTotal",
                    "totalweight_kg",
                    "totalnetweight_kg",
                    "amount",
                ],
            },
            "minItems": 1,
        },
    },
    "required": [
        "factura",
        "purchase_order",
        "vendor",
        "customer",
        "discharge",
        "delivery_place",
        "items",
    ],
}

