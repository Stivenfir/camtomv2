import requests
import pyodbc
import re
import os
import dateparser
import pandas as pd
import io
import base64
import smtplib
import msal
import numpy as np
import json
import traceback
import logging
import threading
from uuid import uuid4

from time import sleep
from pydantic import BaseModel
from fastapi import BackgroundTasks, FastAPI
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dateutil.parser import parse
from datetime import datetime
from snippedtexto import peticion_descripcion_producto, obtener_clasificacion_arancelaria
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from jsonaxlsx import process_job_with_jobid
from xlsxprocesotiempos import xlsx_process, endpointminimas, fichatecnica_pdf
from extractgeneral import ocr_factura, validate_integralaia_settings

# Configuración básica del logging
logging.basicConfig(
    filename='procesamiento_facturas.log',  # Archivo donde se guardará el log
    level=logging.INFO,                     # Nivel de log (puedes usar DEBUG para más detalle)
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI()
PROCESSING_STATUS: dict[str, dict] = {}
PROCESSING_STATUS_LOCK = threading.Lock()


@app.on_event("startup")
def validate_integralaia_on_startup():
    valid_config, validation_message = validate_integralaia_settings()
    if not valid_config:
        raise RuntimeError(validation_message)

# obtener_clasificacion_arancelaria("carro automatico motor 1.6 de color rojo")

CONEXION_FALLIDA = "No se pudo establecer conexión con la base de datos."
SINDATOS = "NULL"

def verificar_tipo_doc(archivo_path):
    try:
        extension_archivo = archivo_path.rfind('.')
        if extension_archivo != -1:
            subcadena_extension = archivo_path[extension_archivo + 1:].strip()

        return subcadena_extension
    except Exception as e:
        print(f"Error al extraer la extension del archivo - Revisar que la ruta y el nombre del archivo sea correcto - {e}")
        return 
    
# conectar a bdd
def conectar_sql_server():
    try:
        server = "172.16.10.54\\DBABC21"
        database = "Repecev2005_H"
        username = "Repecev2005"
        password = ""

        conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}')
        print("conexión exitosa")
        return conn
    except Exception as e:
        print(f"Error al conectar a SQL Server: {e}")
        return None

def obtener_clasificacion_arancelaria(descripcion):
    # Hacemos la petición a la API
    response = peticion_descripcion_producto(str(descripcion))

    # Si la respuesta no es None, procesamos la respuesta
    if response:
        return response
    else:
        # Si algo falla, devolvemos None
        return None

def insertar_datafactura(data_factura, IAPR_ProcesarFacturaID, clienteid):
    conn = conectar_sql_server()

    inserted_id = 0

    if conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT INTO IA_IM_Factura (
                IAPR_ProcesarFacturaID,
                IAFAC_NumeroFactura,
                IAFAC_FechaFactura,
                IAFAC_Incoterm,
                IAFAC_Moneda,
                IAFAC_Importe,
                IAFAC_Total,
                IAFAC_CostoFlete,
                IAFAC_Seguro,
                IAFAC_NumeroOC,
                IAFAC_FechaOC,
                IAFAC_PosicionOC,
                IAFAC_NombreProveedor,
                IAFAC_DireccionProveedor,
                IAFAC_RazonSocialProveedor,
                IAFAC_NombreCliente,
                ClienteID,
                IAFAC_DireccionCliente,
                IAFAC_DireccionDescarga,
                IAFAC_TipoDescarga,
                IAFAC_FechaDescarga,
                IAFAC_LugarEntrega,
                IAFAC_EstadosProcesamientoIA  
            ) 
            OUTPUT INSERTED.IAFAC_FacturaID
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )""", (
                int(IAPR_ProcesarFacturaID),
                data_factura['IAFAC_NumeroFactura'],
                data_factura['IAFAC_FechaFactura'],
                data_factura['IAFAC_Incoterm'],
                data_factura['IAFAC_Moneda'],
                data_factura['IAFAC_Importe'],
                data_factura['IAFAC_Total'],
                data_factura['IAFAC_CostoFlete'],
                data_factura['IAFAC_Seguro'],
                data_factura['IAFAC_NumeroOC'],
                data_factura['IAFAC_FechaOC'],
                data_factura['IAFAC_PosicionOC'],
                data_factura['IAFAC_NombreProveedor'],
                data_factura['IAFAC_DireccionProveedor'],
                data_factura['IAFAC_RazonSocialProveedor'],
                data_factura['IAFAC_NombreCliente'],
                int(clienteid),
                data_factura['IAFAC_DireccionCliente'],
                data_factura['IAFAC_DireccionDescarga'],
                data_factura['IAFAC_TipoDescarga'],
                data_factura['IAFAC_FechaDescarga'],
                data_factura['IAFAC_LugarEntrega'],
                0 # factura procesada
            ))

            # Recuperar el ID insertado directamente desde la consulta
            inserted_id = cursor.fetchone()[0]
            print(f"ID insertado: {inserted_id}")

            cursor.execute("EXEC SP_RemoverPuntoFechaFactura ?", inserted_id)

        except Exception as e:
            logging.error(f"error al insertar datos de factura IAPR_ProcesarFacturaID={IAPR_ProcesarFacturaID}: {e}")
            logging.debug(traceback.format_exc())
            conn.rollback()
            cursor.close()
            conn.close()
            return 0

        # Confirmar los cambios en la base de datos
        conn.commit()

        # Cerrar la conexión
        cursor.close()
        conn.close()
        return inserted_id
    else:
        return 'Conexión fallida...'

def agregar_item_excel(item, data_factura, datato_excel, observacion, clienteid, referenciasproductos):

    datato_excel['InvoiceID'].append(data_factura['IAFAC_NumeroFactura']),
    datato_excel['CodigoProducto'].append(item.get('product_code', SINDATOS)),
    datato_excel['Description'].append(item.get('description', SINDATOS)),
    datato_excel['Observacion'].append(observacion),
    datato_excel['VendedorNombre'].append(data_factura['IAFAC_NombreProveedor']),
    datato_excel['VendedorDireccion'].append(data_factura['IAFAC_DireccionProveedor']),
    datato_excel['VendedorDireccionDestinatario'].append(data_factura['IAFAC_RazonSocialProveedor']),
    datato_excel['ClienteNombre'].append(data_factura['IAFAC_NombreCliente']),
    datato_excel['ClienteID'].append(clienteid)
    datato_excel['ClienteDireccion'].append(data_factura['IAFAC_DireccionCliente']),
    datato_excel['FechaFactura'].append(data_factura['IAFAC_FechaFactura']),
    datato_excel['TotalFactura'].append(data_factura['IAFAC_Total']),
    datato_excel['FechaVencimientoFactura'].append(data_factura['invoice_due_date']),
    datato_excel['OrdenCompraFactura'].append(data_factura['IAFAC_NumeroOC']),
    datato_excel['SubtotalFactura'].append(data_factura['IAFAC_Importe']),
    datato_excel['ImpuestosTotalesFactura'].append(data_factura['invoice_total_tax']),
    datato_excel['ImporteAdeudado'].append(data_factura['invoice_amount_due']),
    datato_excel['SaldoAnteriorNoPagado'].append(data_factura['invoice_prev_unpaid_balance']),
    datato_excel['DireccionFacturacion'].append(data_factura['addresses_billing_address']),
    datato_excel['DireccionEnvio'].append(data_factura['addresses_shipping_address']),
    datato_excel['DireccionServicio'].append(data_factura['addresses_service_address']),
    datato_excel['DireccionRemesa'].append(data_factura['addresses_remittance_address']),
    datato_excel['DestinatarioFacturacion'].append(data_factura['addresses_billing_recipient']),
    datato_excel['DestinatarioEnvio'].append(data_factura['addresses_shipping_recipient']),
    datato_excel['DestinatarioServicio'].append(data_factura['addresses_service_recipient']),
    datato_excel['DestinatarioRemesa'].append(data_factura['addresses_remittance_recipient']),
    datato_excel['FechaInicio_PeriodoServicio'].append(data_factura['service_period_startdate']),
    datato_excel['FechaFinalizacion_PeriodoServicio'].append(data_factura['service_period_enddate']),
    datato_excel['Cantidad'].append(item.get('item_quantity', SINDATOS))
    datato_excel['Unidad'].append(item.get('item_unit', SINDATOS))
    datato_excel['PrecioUnitario'].append(item.get('item_unit_price', SINDATOS))
    datato_excel['Impuesto'].append(item.get('items_tax', SINDATOS))
    datato_excel['Fecha_Item'].append(item.get('items_date', SINDATOS)),
    datato_excel['IAFAC_Incoterm'].append(data_factura['IAFAC_Incoterm']),
    datato_excel['IAFAC_Moneda'].append(data_factura['IAFAC_Moneda']),
    datato_excel['ReferenciaID'].extend([referencia[0] for referencia in referenciasproductos]) if referenciasproductos else datato_excel['ReferenciaID'].append(0)

    print(f"DATA TO EXCEL: {datato_excel}")

    return 0

def obtener_nombre_archivo(archivo_path):
    # Obtener el nombre del archivo sin la ruta completa
    nombre_archivo_con_extension = os.path.basename(archivo_path)
    
    # Extraer el nombre antes de la extensión ".pdf"
    nombre_archivo = nombre_archivo_con_extension.split('.pdf')[0]
    
    return nombre_archivo

def envio_excel(datato_excel_factura, datato_excel_productos, to_email, subject, body, IAFAC_FacturaID):

    # Crear DataFrame a partir de los datos de la factura y productos
    df_factura = pd.DataFrame([datato_excel_factura])  # La factura puede ser un solo registro
    df_productos = pd.DataFrame(datato_excel_productos)  # Los productos pueden ser múltiples registros

    file_name = f"Factura_{IAFAC_FacturaID}_Coord.xlsx"

    # Crear un archivo Excel en memoria usando BytesIO
    output = BytesIO()

    # Guardar el DataFrame de la factura y de los productos en diferentes hojas dentro del archivo Excel en memoria
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_factura.to_excel(writer, index=False, sheet_name='Factura')
        df_productos.to_excel(writer, index=False, sheet_name='Productos')

    # Mover el puntero al principio del archivo para poder leerlo
    output.seek(0)

    from_email = 'notificaciones@abcrepecev.com'
    from_password = 'AbcRpc2021-'

    smtp_server = 'smtp-mail.outlook.com'
    smtp_port = 587

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    # Crear la parte del archivo adjunto
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(output.read())  # Cargar el contenido del archivo en memoria

    encoders.encode_base64(part)  # Codificar el archivo en base64

    part.add_header('Content-Disposition', f'attachment; filename={file_name}')

    # Adjuntar el archivo al mensaje
    msg.attach(part)

    # Enviar el correo utilizando el servidor SMTP
    try:
        # Conectar al servidor SMTP y enviar el correo
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Iniciar TLS para seguridad
        server.login(from_email, from_password)  # Iniciar sesión en el servidor con tus credenciales
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)  # Enviar el correo
        server.quit()  # Cerrar la conexión
        print("Correo enviado exitosamente.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

def consulta_referenciasproductos(product_code, clienteid):
    conn = conectar_sql_server()

    if conn:
        cursor = conn.cursor()

        cursor.execute(""" SELECT RefProductoID FROM BSReferenciaProducto WHERE 
                        (RefProductoReferencia = ? OR RefCodInternoCliente = ?) AND RefClienteID = ? """, product_code, product_code, clienteid)

        referenciasproductos = cursor.fetchall()

        # Cerrar la conexión
        cursor.close()
        conn.close()

        return referenciasproductos

def proceso_referenciaproducto(product_code, clienteid):

    referenciasproductos = consulta_referenciasproductos(product_code, clienteid)

    if referenciasproductos and len(referenciasproductos) > 1:
        return 3 # Referencia existente más de una vez por cliente
    else:
        return 1 # CAMTOM trae codigo de producto pero no existe en tracking por cliente

def observacionsegunestadoreferencia(IAItemFAC_EstadoProcesamientoReferencia):
    if IAItemFAC_EstadoProcesamientoReferencia == 0:
        return 'No fue posible obtener codigo del producto para este item'
    elif IAItemFAC_EstadoProcesamientoReferencia == 1:
        return 'Se extrajo el codigo de producto pero no existe en tracking por cliente'
    elif IAItemFAC_EstadoProcesamientoReferencia == 2:
        return 'Referencia existente una unica vez en tracking por cliente (verificado por ia)'
    elif IAItemFAC_EstadoProcesamientoReferencia == 3:
        return 'Referencia existente más de una vez por cliente (segun codigo del producto)'

def consultareferenciaid(item, clienteid):
    
    conn = conectar_sql_server()
    refproductoid = None

    if conn:
        cursor = conn.cursor()

        cursor.execute(""" SELECT RefProductoID 
                       FROM BSReferenciaProducto 
                       WHERE RefClienteID = ? AND RefProductoDescripcion = ? """, (clienteid, item.get('description')))

        refproductoid = cursor.fetchall()
        print(f"refproductoid: {refproductoid}")
        
        if refproductoid:
            # Si se encontraron resultados, retornar el primer RefProductoID
            refproductoid = refproductoid[0][0]  # resultado[0] es una tupla, [0] es el RefProductoID
            print(refproductoid)

        # Cerrar la conexión
        cursor.close()
        conn.close()

    return refproductoid

def estado_procesado(archivo_path, accion):
    
    conn = conectar_sql_server()
    resultado = None

    if conn:
        cursor = conn.cursor()

        if accion == 0: # informacion sobre la factura en la tabla IA_IM_ProcesarFacturasIA
            cursor.execute("""SELECT * FROM IA_IM_ProcesarFacturasIA WHERE IAPR_ProcesarFacturaID = ? """, (archivo_path)) #pasarle el IAPR_ProcesarFacturaID

            resultado = cursor.fetchall()
            print(resultado)
            resultado = resultado[0]
            print(resultado)

            # Confirmar los cambios en la base de datos
            conn.commit()
        
        elif accion == 1: # se cambia el estado de la factura a procesado en la tabla IA_IM_ProcesarFacturasIA
            cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_Procesado = 1 WHERE IAPR_ProcesarFacturaID = ?""", (archivo_path))
            conn.commit()  # Confirmamos los cambios en la base de datos

        # Cerrar la conexión
        cursor.close()
        conn.close()

    return resultado

def validaprocesamientoia(archivo_path, accion, error):
    conn = conectar_sql_server()

    if conn:
        cursor = conn.cursor()

        if accion == 0: # proceso sin errores
            cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_ErrorProcesamientoIA = 0 WHERE IAPR_ProcesarFacturaID = ?""", (archivo_path))
            conn.commit()  # Confirmamos los cambios en la base de datos
            cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_ErrorProcesamientoIACadena = ? WHERE IAPR_ProcesarFacturaID = ?""", (error, archivo_path))
            conn.commit()  # Confirmamos los cambios en la base de datos
            
        elif accion == 1: # error en el proceso
            cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_ErrorProcesamientoIA = 1 WHERE IAPR_ProcesarFacturaID = ?""", (archivo_path))
            conn.commit()  # Confirmamos los cambios en la base de datos
            cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_ErrorProcesamientoIACadena = ? WHERE IAPR_ProcesarFacturaID = ?""", (error, archivo_path))
            conn.commit()  # Confirmamos los cambios en la base de datos
        
        # Cerrar la conexión
        cursor.close()
        conn.close()

def extraer_incoterm(incoterm_camtom):
    conn = conectar_sql_server()
    incoterms = None

    if conn:
        cursor = conn.cursor()
        cursor.execute(""" SELECT IncotermID FROM BSIncoterm """)
        incoterms = [IAFAC_Incoterm[0] for IAFAC_Incoterm in cursor.fetchall()]
        conn.commit()

    for IAFAC_Incoterm in incoterms:
        IAFAC_Incoterm = IAFAC_Incoterm.upper().strip()
        if IAFAC_Incoterm in incoterm_camtom.upper()[:4]:
            print(IAFAC_Incoterm)
            cursor.close()
            conn.close()

            return IAFAC_Incoterm

def replace_nan_with_none(data):
    # Función recursiva para reemplazar 'nan' por 'None' en un JSON (lista de diccionarios)
    if isinstance(data, list):
        # Si es una lista, recorrer los elementos
        for i in range(len(data)):
            data[i] = replace_nan_with_none(data[i])
    elif isinstance(data, dict):
        # Si es un diccionario, recorrer las claves y valores
        for key, value in data.items():
            if pd.isna(value):
                data[key] = None  # Reemplazar NaN por None
            else:
                data[key] = replace_nan_with_none(value)
    return data

def analizar_separador_decimal(cadena):

    cadena = str(cadena).strip()
    puntos = cadena.count('.')
    comas = cadena.count(',')

    if puntos == 0 and comas == 0:
        return cadena

    if puntos == 0 and comas == 1:
        partes = cadena.split(',')
        if len(partes[-1]) == 3 and len(partes[-2]) == 3:
            return cadena.replace(',', '')
        else:
            return cadena

    if puntos == 1 and comas == 0:
        partes = cadena.split('.')
        if len(partes[-1]) == 3 and len(partes[-2]) == 3:
            return cadena.replace('.', '')
        else:
            return cadena.replace('.', ',')

    if puntos == 0 and comas > 1:
        return cadena.replace(',', '')

    if puntos > 1 and comas == 0:
        return cadena.replace('.', '')

    if puntos > comas:
        return cadena.replace('.', '')

    if comas > puntos:
        cadena = cadena.replace(',', '')
        return cadena.replace('.', ',')

    if comas == puntos:
        index_coma = cadena.rfind(',')
        index_punto = cadena.rfind('.')
        if index_coma > index_punto:
            return cadena.replace('.', '')
        else:
            cadena = cadena.replace(',', '')
            return cadena.replace('.', ',')

    return cadena

def buscar_tipodoc(tipodoc):
    try:
        conn = conectar_sql_server()
        cursor = conn.cursor()

        # Consulta con condición
        query = """
            SELECT *
            FROM IA_campostipodoc
            WHERE id_AItipodoc = ?
        """

        cursor.execute(query, (tipodoc,))
        rows = cursor.fetchall()

        return rows

    except Exception as e:
        print("Error en la conexión o consulta:", e)

    finally:
        if 'conn' in locals():
            conn.close()

def procesar_factura(archivo_path, clienteid, tipodoc):

    # Verificar si el archivo existe y se puede abrir
    if not os.path.exists(archivo_path) or not os.access(archivo_path, os.R_OK):
        print(f"El archivo {archivo_path} no se puede abrir o no existe.")
        return None, None

    data_factura = {}
    items_factura = []
    
    response = ocr_factura(archivo_path, tipodoc)

    if response.status_code == 200:
        print("solicitud exitosa")
        jsonrespuesta = response.json()
        
        print(f"JSONRESPUESTA: {jsonrespuesta}")

        fechafactura_str = jsonrespuesta['document_data']['factura'].get('invoiceDate', '')
        try:
            
            IAFAC_FechaFactura = datetime.strptime(fechafactura_str, "%d/%m/%Y")
        except Exception as e:
            IAFAC_FechaFactura = None
        
        fechaoc_str = jsonrespuesta['document_data']['purchase_order'].get('date_po', '')
        try:
            IAFAC_FechaOC = datetime.strptime(fechaoc_str, "%d/%m/%Y")
        except Exception as e:
            IAFAC_FechaOC = None

        fechadescarga_str = jsonrespuesta['document_data']['discharge'].get('date', '')
        try:
            IAFAC_FechaDescarga = datetime.strptime(fechadescarga_str, "%d/%m/%Y")
        except Exception as e:
            IAFAC_FechaDescarga = None

        data_factura = {

            "IAFAC_NumeroFactura": jsonrespuesta['document_data']['factura'].get('invoiceNumber', ''),
            "IAFAC_FechaFactura": IAFAC_FechaFactura,
            "IAFAC_Incoterm": extraer_incoterm(jsonrespuesta['document_data']['factura'].get('incoterm', '')),
            "IAFAC_Moneda": jsonrespuesta['document_data']['factura'].get('currency', ''),
            "IAFAC_Importe": jsonrespuesta['document_data']['factura'].get('amount', SINDATOS) if jsonrespuesta['document_data']['factura'].get('amount', SINDATOS) == SINDATOS else jsonrespuesta['document_data']['factura'].get('amount', SINDATOS),
            "IAFAC_Total": jsonrespuesta['document_data']['factura'].get('total', SINDATOS) if jsonrespuesta['document_data']['factura'].get('total', SINDATOS) == SINDATOS else jsonrespuesta['document_data']['factura'].get('total', SINDATOS),
            "IAFAC_CostoFlete": jsonrespuesta['document_data']['factura'].get('freight_cost', SINDATOS),
            "IAFAC_Seguro": jsonrespuesta['document_data']['factura'].get('insurance', SINDATOS),

            "IAFAC_NumeroOC": jsonrespuesta['document_data']['purchase_order'].get('number_po', ''),
            "IAFAC_FechaOC": IAFAC_FechaOC,
            "IAFAC_PosicionOC": jsonrespuesta['document_data']['purchase_order'].get('position_po', SINDATOS),

            "IAFAC_NombreProveedor": jsonrespuesta['document_data']['vendor'].get('name', ''),
            "IAFAC_DireccionProveedor": jsonrespuesta['document_data']['vendor'].get('address', ''),
            "IAFAC_RazonSocialProveedor": jsonrespuesta['document_data']['vendor'].get('legal_name', SINDATOS),

            "ClienteID": jsonrespuesta['document_data']['customer'].get('id', 0),
            "IAFAC_NombreCliente": jsonrespuesta['document_data']['customer'].get('name', ''),
            "IAFAC_DireccionCliente": jsonrespuesta['document_data']['customer'].get('address', ''),
            
            "IAFAC_DireccionDescarga": jsonrespuesta['document_data']['discharge'].get('address', ''),
            "IAFAC_TipoDescarga": jsonrespuesta['document_data']['discharge'].get('type', ''),
            "IAFAC_FechaDescarga": IAFAC_FechaDescarga,

            "IAFAC_LugarEntrega": jsonrespuesta['document_data'].get('delivery_place', SINDATOS),

        }

        itemslist = jsonrespuesta['document_data']['items']

        if itemslist:
            print(itemslist)
            for item in itemslist:

                unit_price = item.get('unitPrice', SINDATOS)
                amount = item.get('subTotal', SINDATOS)
                product_code = item.get('reference', SINDATOS)
                numerooc = item.get('purchaseorder_number_item', SINDATOS)
                posicionoc = item.get('purchaseorder_position', SINDATOS)
                ImporteTotal = item.get('total_amount', SINDATOS)
                Subtotal = item.get('subtotal', SINDATOS)

                fechaocitem_str = item.get('order_date', '')
                try:
                    IAFAC_FechaOC = datetime.strptime(fechaocitem_str, "%d/%m/%Y")
                except Exception as e:
                    IAFAC_FechaOC = None

                anio_fabricacion = item.get('year_manufacture')
                try:
                    IAItemFAC_AnioFabricacion = int(anio_fabricacion)
                except (ValueError, TypeError):
                    IAItemFAC_AnioFabricacion = None

                data_item = {
                    "IAItemFAC_NumeroOC": item.get('order_position', SINDATOS),
                    "IAItemFAC_FechaOC": IAFAC_FechaOC,
                    "IAItemFAC_PosicionOC": posicionoc,
                    "IAItemFAC_Referencia": product_code,
                    "IAItemFAC_CodInterno": product_code,
                    "IAItemFAC_PaisOrigen": item.get('origin_country', SINDATOS),
                    "IAItemFAC_Marca": item.get('brand', SINDATOS),
                    "IAItemFAC_Descripcion": item.get('description', SINDATOS) if item.get('description') else SINDATOS,
                    "IAItemFAC_AnioFabricacion": IAItemFAC_AnioFabricacion,
                    "IAItemFAC_Cantidad": item.get('quantity', SINDATOS),
                    "IAItemFAC_Unidad": item.get('unit', SINDATOS),
                    "IAItemFAC_PrecioUnitario": (
                        analizar_separador_decimal(unit_price)
                        if unit_price == SINDATOS
                        else str(unit_price)
                    ),
                    "IAItemFAC_ImporteTotal": item.get('amount', SINDATOS),
                    "IAItemFAC_Subtotal": item.get('subTotal', SINDATOS),
                    "IAItemFAC_Total": (
                        item.get('subTotal') if amount == SINDATOS else str(amount)
                    ),
                    "IAItemFAC_PesoBrutoKg": item.get('totalweight_kg', SINDATOS),
                    "IAItemFAC_PesoNetoKg": item.get('totalnetweight_kg', SINDATOS)
                    #"estado_referencia": 2 if item.get('ITEM STATUS') == 'verified' else (proceso_referenciaproducto(str(item.get('PRODUCT CODE')), clienteid) if item.get('PRODUCT CODE') else 0)
                }
                items_factura.append(data_item)
        else: 
            print("resultados vacios")
        
        # envio_excel(datato_excel, 'aochoa@abcrepecev.com', 'Factura y Datos de Producto', 'Adjunto te envío el archivo Excel con los detalles de la factura y productos.', archivo_path)

        print(f"items factura: {items_factura}")

        return data_factura, items_factura
    else:
        print(f'entró al else: {response.text}')
        return None, None

def sql_null(valor):
    if valor in ("", "NULL", "null", None):
        return None
    return valor

def insertar_itemsfactura(IAFAC_FacturaID, items_factura):
    conn = conectar_sql_server()



    if conn:
        for item in items_factura:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                INSERT INTO IA_IM_FacturaItem (
                        IAFAC_FacturaID,    
                        IAItemFAC_NumeroOC,
                        IAItemFAC_FechaOC,
                        IAItemFAC_PosicionOC,
                        IAItemFAC_Referencia,
                        IAItemFAC_CodInterno,
                        IAItemFAC_PaisOrigen,
                        IAItemFAC_Marca,
                        IAItemFAC_Descripcion,
                        IAItemFAC_AnioFabricacion,
                        IAItemFAC_Cantidad,
                        IAItemFAC_Unidad,
                        IAItemFAC_PrecioUnitario,
                        IAItemFAC_ImporteTotal,
                        IAItemFAC_Subtotal,
                        IAItemFAC_Total,
                        IAItemFAC_PesoBrutoKg,
                        IAItemFAC_PesoNetoKg
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    int(IAFAC_FacturaID),
                    sql_null(item['IAItemFAC_NumeroOC']),
                    sql_null(item['IAItemFAC_FechaOC']),
                    sql_null(item['IAItemFAC_PosicionOC']),
                    sql_null(item['IAItemFAC_Referencia']),
                    sql_null(item['IAItemFAC_CodInterno']),
                    sql_null(item['IAItemFAC_PaisOrigen']),
                    sql_null(item['IAItemFAC_Marca']),
                    sql_null(item['IAItemFAC_Descripcion'].replace("'", " ")),
                    sql_null(item['IAItemFAC_AnioFabricacion']),
                    sql_null(item['IAItemFAC_Cantidad']),
                    sql_null(item['IAItemFAC_Unidad']),
                    sql_null(item['IAItemFAC_PrecioUnitario']),
                    sql_null(item['IAItemFAC_ImporteTotal']),
                    sql_null(item['IAItemFAC_Subtotal']),
                    sql_null(item['IAItemFAC_Total']),
                    sql_null(item['IAItemFAC_PesoBrutoKg']),
                    sql_null(item['IAItemFAC_PesoNetoKg'])
                ))

            except Exception as e:
                print(f"error al insertar datos: {e} - {traceback.print_exc()}")
                return 'Error al insertar datos...'

            # Confirmar los cambios en la base de datos
            conn.commit()

        # Cerrar la conexión
        cursor.close()
        conn.close()
        return 'Conexión correcta...'
    else:
        return 'Conexión fallida...'

def busqueda_IAPR_ProcesarFacturaID(encabezado_path):
    conn = conectar_sql_server()

    if conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DocImpoID, IAPR_ProcesarFacturaID FROM IA_IM_ProcesarFacturasIA WHERE IAPR_RutaFactura = ? """, (encabezado_path.replace("/", "\\")))

        DocImpoID = cursor.fetchall()
        
        if DocImpoID:
            DocImpoID, IAPR_ProcesarFacturaID = DocImpoID[0]
            print(f"DocImpoID encontrado: {DocImpoID}")
            print(f"IAPR_ProcesarFacturaID encontrado: {IAPR_ProcesarFacturaID}")

            cursor.execute("""SELECT IAPR_ProcesarFacturaID FROM IA_IM_ProcesarFacturasIA WHERE DocImpoID = ? AND IAPR_RutaFactura != ?""", (DocImpoID, encabezado_path.replace("/", "\\")))

            otro_DocImpoID = cursor.fetchall()
            print(f"Otro docimpoid: {otro_DocImpoID}")

            if otro_DocImpoID:
                # Suponemos que el primer resultado es el otro IAPR_ProcesarFacturaID
                otro_IAPR_ProcesarFacturaID = otro_DocImpoID[0][0]
                print(f"Otro IAPR_ProcesarFacturaID encontrado con el mismo DocImpoID: {otro_IAPR_ProcesarFacturaID}")
                return otro_IAPR_ProcesarFacturaID
            else:
                print(f"No se encontró otro IAPR_ProcesarFacturaID con el mismo DocImpoID: {DocImpoID}")
                return None
        else:
            print(f"No se encontró el DocImpoID para el encabezado_path: {encabezado_path}")
            return None

def update_tablas_CAMTOM(json_data, IAPR_ProcesarFacturaID):
    conn = conectar_sql_server()
    resultado = None

    if conn:
        cursor = conn.cursor()
        
        cursor.execute("""SELECT IAFAC_FacturaID FROM IA_IM_Factura WHERE IAPR_ProcesarFacturaID = ? """, (IAPR_ProcesarFacturaID))

        resultado = cursor.fetchall()
        print(resultado)
        IAFAC_FacturaID = resultado[0][0]
        print(f"IAFAC_FacturaID: {IAFAC_FacturaID}")

        # Actualización de columnas en la tabla IA_IM_Factura
        mapeo_columnas_encabezado = {
            'INVOICEID': 'IAFAC_NumeroFactura',
            'VENDEDORNOMBRE': 'IAFAC_NombreProveedor',
            'VENDEDORDIRECCION': 'IAFAC_DireccionProveedor',
            'VENDEDORDIRECCIONDESTINATARIO': 'IAFAC_RazonSocialProveedor',
            'CLIENTENOMBRE': 'IAFAC_NombreCliente',
            'CLIENTEDIRECCION': 'IAFAC_DireccionCliente',
            'DIRECCIONFACTURACION': 'addresses_billing_address',
            'DIRECCIONENVIO': 'addresses_shipping_address',
            'DIRECCIONSERVICIO': 'addresses_service_address',
            'DIRECCIONREMESA': 'addresses_remittance_address',
            'DESTINATARIOFACTURACION': 'addresses_billing_recipient',
            'DESTINATARIOENVIO': 'addresses_shipping_recipient',
            'DESTINATARIOSERVICIO': 'addresses_service_recipient',
            'DESTINATARIOREMESA': 'addresses_remittance_recipient',
            'FECHAINICIO PERIODOSERVICIO': 'service_period_startdate',
            'FECHAFINALIZACION PERIODOSERVICIO': 'service_period_enddate'
        }

        mapeo_columnas_trabajo = {
            'DESCRIPTION': 'IAItemFAC_Descripcion',
            'CANTIDAD': 'IAItemFAC_Cantidad',
            'UNIDAD': 'IAItemFAC_Unidad',
            'PRECIOUNITARIO': 'IAItemFAC_PrecioUnitario',
            'FECHAITEM': 'items_date',
            'CODIGOPRODUCTO': 'IAItemFAC_Referencia',
            'IMPUESTO': 'items_tax',
            'REFERENCIAID': 'RefProductoID' # corregir
        }

        try:
            # Asegúrate de que json_data sea una lista no vacía y que contiene un diccionario
            if json_data and isinstance(json_data[0], dict):
                # Aquí vamos a iterar sobre las claves del json_data
                for clave_json, columna_db in mapeo_columnas_encabezado.items():
                    if clave_json in json_data[0]:  # Verificar que la clave esté en json_data
                        valor = json_data[0][clave_json]
                        
                        # Comprobar si el valor es nan
                        if isinstance(valor, float) and np.isnan(valor):
                            valor = None  # Asignar None si es nan
                        print(f"Actualizando columna: {columna_db} con valor: {valor}")

                        # Realizar la actualización en la base de datos
                        cursor.execute(f"""UPDATE IA_IM_Factura SET {columna_db} = ? WHERE IAPR_ProcesarFacturaID = ?""", (valor, IAPR_ProcesarFacturaID))
                        conn.commit()

                for clave_json, columna_db in mapeo_columnas_trabajo.items():
                    if clave_json in json_data[0]:  # Verificar que la clave esté en json_data
                        valor = json_data[0][clave_json]
                        
                        # Comprobar si el valor es nan
                        if isinstance(valor, float) and np.isnan(valor):
                            valor = None  # Asignar None si es nan
                        print(f"Actualizando columna: {columna_db} con valor: {valor}")

                        # Realizar la actualización en la base de datos
                        cursor.execute(f"""UPDATE IA_IM_FacturaItem SET {columna_db} = ? WHERE IAFAC_FacturaID = ?""", (valor, IAFAC_FacturaID))
                        conn.commit()

                # Actualización del estado
                cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAPR_ProcesarFacturaID = ?""", (4, IAPR_ProcesarFacturaID))
                conn.commit()

                # Ejecutar el procedimiento almacenado con los parámetros
                cursor.execute("{CALL SP_ProcesosIA (?, ?)}", (1, IAPR_ProcesarFacturaID))

                # Confirmar si el procedimiento se ejecutó correctamente (si es necesario)
                conn.commit()

            else:
                print(f"json_data no es una lista de diccionarios válida o está vacío.")

        except Exception as e:
            print(f"Falló la inserción de los datos en IAFAC_FacturaID... {e}")

        # Cerrar la conexión
        cursor.close()
        conn.close()
    
def estado_procesamientoia(estadoprocesamientoia, encabezado_path):
    conn = conectar_sql_server()
    resultado = None

    if conn:
        cursor = conn.cursor()
        if estadoprocesamientoia == 0:
            cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAFAC_FacturaID = ?""", (0, encabezado_path))
            conn.commit()  # Confirmamos los cambios en la base de datos
        elif estadoprocesamientoia == 1:
            cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAFAC_FacturaID = ?""", (1, encabezado_path))
            conn.commit()  # Confirmamos los cambios en la base de datos
        elif estadoprocesamientoia == 2:
            try:
                cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAFAC_FacturaID = ?""", (2, encabezado_path))
                sleep(20)
                conn.commit() # Confirmamos los cambios en la base de datos
                print(f"hizo el update (?) - UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = 2 WHERE IAFAC_FacturaID = {encabezado_path}")
                ### cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_FechaEnviadoAlCoordinador = ? WHERE IAFAC_FacturaID = ?""", (datetime.now(), encabezado_path))
                ### conn.commit()  # Confirmamos los cambios en la base de datos
            except Exception as e:
                print(f"error al ejecutar el update {e}")
        elif estadoprocesamientoia == 5: # error en clasificacion
            try:
                cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAFAC_FacturaID = ?""", (5, encabezado_path))
                sleep(20)
                conn.commit() # Confirmamos los cambios en la base de datos
                print(f"hizo el update por ERROR en clasificacion - UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = 5 WHERE IAFAC_FacturaID = {encabezado_path}")
                ### cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_FechaEnviadoAlCoordinador = ? WHERE IAFAC_FacturaID = ?""", (datetime.now(), encabezado_path))
                ### conn.commit()  # Confirmamos los cambios en la base de datos
            except Exception as e:
                print(f"error al ejecutar el update {e}")
        elif estadoprocesamientoia == 3:

            # IAPR_ProcesarFacturaID = busqueda_IAPR_ProcesarFacturaID(encabezado_path)

            if encabezado_path: #and IAPR_ProcesarFacturaID: #procesarfacturaia
                # Ahora, actualizamos el estado en la tabla IA_IM_Factura utilizando el otro IAPR_ProcesarFacturaID
                ### cursor.execute("""UPDATE IA_IM_Factura SET IAItemFAC_FechaRecibidoDelcoordinador = ? WHERE IAPR_ProcesarFacturaID = ?""", (datetime.now(), IAPR_ProcesarFacturaID))
                ### conn.commit()

                cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAFAC_FacturaID = ?""", (3, encabezado_path))
                conn.commit()  # Confirmamos los cambios en la base de datos

                # Ejecutar el procedimiento almacenado con los parámetros
                cursor.execute("{CALL SP_ProcesosIA (?, ?)}", (1, encabezado_path))
                conn.commit()

                # json_data = xlsx_process(encabezado_path)

                # print(type(json_data))

                #update_tablas_CAMTOM(json_data, IAPR_ProcesarFacturaID)
            else:
                print("No se encontró factura correspondiente en bdd...")
        elif estadoprocesamientoia == 4:
            cursor.execute("""UPDATE IA_IM_Factura SET IAFAC_EstadosProcesamientoIA = ? WHERE IAFAC_FacturaID = ?""", (4, encabezado_path))
            conn.commit()  # Confirmamos los cambios en la base de datos

    # Cerrar la conexión
    cursor.close()
    conn.close()

def buscar_data_factura(IAFAC_FacturaID):
    conn = conectar_sql_server()
    resultado_idce_data = None

    if conn:
        cursor = conn.cursor()
    
        try:
            # Ahora, realizamos la consulta
            cursor.execute("""
                SELECT * 
                FROM IA_IM_Factura
                WHERE IAFAC_FacturaID = ?""", (int(IAFAC_FacturaID)))
            
             # Traemos los resultados como un diccionario usando fetchone()
            columns = [column[0] for column in cursor.description]  # Obtener los nombres de las columnas
            result = cursor.fetchone()
            
            if result:
                # Convertir la fila a un diccionario
                resultado_idce_data = dict(zip(columns, result))
            
        except Exception as e:
            print(f"Error al ejecutar la consulta: {e}")
        
        finally:
            # Cerrar el cursor y la conexión
            cursor.close()
            conn.close()

        return resultado_idce_data
    
def buscarIAPR_ProcesarFacturaID_sininiciar(IAPR_ProcesarFacturaID):
    conn = conectar_sql_server()
    iniciado = False

    if conn:
        cursor = conn.cursor()
    
        try:
            # Ahora, realizamos la consulta
            cursor.execute("""
                SELECT * 
                FROM IA_IM_ProcesarFacturasIA
                WHERE IAPR_ProcesarFacturaID = ? and IAPR_FechaInicioProcesamiento IS NOT NULL""", (int(IAPR_ProcesarFacturaID)))
            
            facturasiniciadas = cursor.fetchone()
            
            if facturasiniciadas:
                iniciado = True
            else:
                iniciado = False
            
            return iniciado 

        except Exception as e:
            print(f"Error al ejecutar la consulta: {e}")
        
        finally:
            # Cerrar el cursor y la conexión
            cursor.close()
            conn.close()

def buscar_data_productos(IAFAC_FacturaID):
    conn = conectar_sql_server()
    resultado_idce_data_productos = None

    if conn:
        cursor = conn.cursor()
    
        try:
            # Ahora, realizamos la consulta
            cursor.execute("""
                SELECT * 
                FROM IA_IM_FacturaItem
                WHERE IAFAC_FacturaID = ?""", (int(IAFAC_FacturaID)))
            
            resultado_idce_data_productos = cursor.fetchall()
            
            # Obtener los nombres de las columnas
            columnas = [desc[0] for desc in cursor.description]
            
            # Convertir los resultados en un diccionario
            resultado_dict = []
            for fila in resultado_idce_data_productos:
                fila_dict = dict(zip(columnas, fila))  # Emparejar las columnas con los datos
                resultado_dict.append(fila_dict)
            
            # Mostrar el resultado en formato de diccionario
            print(resultado_dict)

        except Exception as e:
            print(f"Error al ejecutar la consulta: {e}")
        
        finally:
            # Cerrar el cursor y la conexión
            cursor.close()
            conn.close()

        return resultado_dict

def informacioninicioprocesamiento(IAPR_ProcesarFacturaID, fecha):
    conn = conectar_sql_server()

    cursor = conn.cursor()

    cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_FechaInicioProcesamiento = ? WHERE IAPR_ProcesarFacturaID = ?""", (fecha, IAPR_ProcesarFacturaID))
    conn.commit()  # Confirmamos los cambios en la base de datos
            
    # Cerrar la conexión
    cursor.close()
    conn.close()

    logging.info(f"Se extrajo la fecha de inicio y se actualizó en la tabla IA_IM_ProcesarFacturasIA: {IAPR_ProcesarFacturaID} - {fecha}")

def informacionfinalizacionprocesamiento(IAPR_ProcesarFacturaID, fecha):
    conn = conectar_sql_server()

    cursor = conn.cursor()

    cursor.execute("""UPDATE IA_IM_ProcesarFacturasIA SET IAPR_FechaFinalizacionProcesamiento = ? WHERE IAPR_ProcesarFacturaID = ?""", (fecha, IAPR_ProcesarFacturaID))
    conn.commit()  # Confirmamos los cambios en la base de datos
            
    # Cerrar la conexión
    cursor.close()
    conn.close()

    logging.info(f"Se extrajo la fecha de finalizacion y se actualizó en la tabla IA_IM_ProcesarFacturasIA: {IAPR_ProcesarFacturaID} - {fecha}")

@app.get("/procesarfichatecnica/{docimpoid:path}") #docimpoid
async def main(docimpoid: str):
    if not docimpoid:
        return {"error": "DocImpoID no puede estar vacío"}

    # Lanzamos un hilo directamente
    thread = threading.Thread(target=procesar_fichatecnica_background, args=(docimpoid,))
    thread.start()

    return {"status": "processing", "docimpoid": docimpoid}

def procesar_fichatecnica_background(docimpoid: str):
    try:
        logging.info(f"Iniciando procesamiento de ficha técnica en segundo plano para docimpoid: {docimpoid}")
        conn = conectar_sql_server()
        archivos_path = None

        # Validar y convertir docimpoid
        try:
            if '/' in docimpoid:
                docimpoid = int(docimpoid.split('/')[1]) if docimpoid.split('/')[1] else int(docimpoid.split('/')[0])
            else:
                docimpoid = int(docimpoid)
            logging.debug(f"docimpoid transformado a entero: {docimpoid}")
        except Exception as e:
            logging.error(f"Error transformando docimpoid a entero: {e}")
            raise

        if conn:
            cursor = conn.cursor()
            logging.info("Conexión a SQL Server exitosa. Consultando facturas por procesar...")

            cursor.execute(""" select Ruta from IA_IM_FacturaItem as IMFI
                                INNER JOIN TMPDocumentosCompletarFactura as DCF ON DCF.IAItemFAC_ItemfacID = IMFI.IAItemFAC_ItemfacID
                                where DCF.DocImpoID = ? and DCF.tipodocumentoid = 3 """, (docimpoid,))

            archivos_path = cursor.fetchall()
            logging.info(f"{len(archivos_path)} FICHAS TECNICAS encontrada(s) para procesar. Detalles: {archivos_path}")
            conn.commit()

            cursor.close()
            conn.close()

            for ruta_path in archivos_path:
                RutaFichaTecnica = ruta_path[0].replace('1.7', '10.39')
                logging.debug(f"Ruta modificada del archivo: {RutaFichaTecnica}")
                print(RutaFichaTecnica)

    except Exception as e:
        logging.error(f"Error en el procesamiento de ficha técnica en segundo plano para docimpoid: {docimpoid} - {e}")

@app.get("/procesarfactura/{docimpoid:path}") #docimpoid
async def procesar_factura_endpoint(docimpoid: str):
    if not docimpoid:
        return {"error": "DocImpoID no puede estar vacío"}

    request_id = str(uuid4())
    with PROCESSING_STATUS_LOCK:
        PROCESSING_STATUS[request_id] = {
            "request_id": request_id,
            "docimpoid": docimpoid,
            "status": "processing",
            "message": "Proceso iniciado",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "total_facturas": 0,
            "procesadas_ok": 0,
            "procesadas_error": 0,
            "saltadas": 0,
            "items": [],
        }

    # Lanzamos un hilo directamente
    thread = threading.Thread(target=procesar_factura_background, args=(docimpoid, request_id))
    thread.start()

    return {
        "status": "processing",
        "docimpoid": docimpoid,
        "request_id": request_id,
        "status_endpoint": f"/procesarfactura-estado/{request_id}",
    }


@app.get("/procesarfactura-estado/{request_id}")
async def obtener_estado_procesamiento(request_id: str):
    with PROCESSING_STATUS_LOCK:
        estado = PROCESSING_STATUS.get(request_id)
    if not estado:
        return {"error": "request_id no encontrado"}
    return estado


def _status_update(request_id: str, **kwargs):
    with PROCESSING_STATUS_LOCK:
        if request_id in PROCESSING_STATUS:
            PROCESSING_STATUS[request_id].update(kwargs)


def _status_add_item(request_id: str, item: dict):
    with PROCESSING_STATUS_LOCK:
        if request_id in PROCESSING_STATUS:
            PROCESSING_STATUS[request_id]["items"].append(item)


def procesar_factura_background(docimpoid: str, request_id: str): #docimpoid
    try:
        logging.info(f"Iniciando procesamiento de factura en segundo plano para docimpoid: {docimpoid}")
        conn = conectar_sql_server()
        archivos_path = None
        countfacturasnoprocesadas = 0
        countfacturasok = 0
        countsaltadas = 0

        # Validar y convertir docimpoid
        try:
            if '/' in docimpoid:
                docimpoid = int(docimpoid.split('/')[1]) if docimpoid.split('/')[1] else int(docimpoid.split('/')[0])
            else:
                docimpoid = int(docimpoid)
            logging.debug(f"docimpoid transformado a entero: {docimpoid}")
        except Exception as e:
            logging.error(f"Error transformando docimpoid a entero: {e}")
            raise

        if conn:
            cursor = conn.cursor()
            logging.info("Conexión a SQL Server exitosa. Consultando facturas por procesar...")
            ### cursor.execute(""" SELECT dbo.RutaDocumentosServer7(DocimpoID)+'\\'+SUBSTRING(IAPR_RutaFactura, CHARINDEX('DS\', IAPR_RutaFactura), LEN(IAPR_RutaFactura)), IAPR_ProcesarFacturaID 
            ###                FROM IA_IM_ProcesarFacturasIA 
            ###                WHERE DocImpoID = ? AND IAPR_FacturaEnviadaProcesar = 1 """, (docimpoid))

            cursor.execute(""" SELECT dbo.RutaDocumentosServer7(IA_IM_ProcesarFacturasIA.DocimpoID)+'\'+IAPR_RutaFactura, IAPR_ProcesarFacturaID,IMDocumentosSoporteDo.BSDocsoprtedeclaimpoid
                                FROM IA_IM_ProcesarFacturasIA
                                INNER JOIN IMDocumentosSoporteDo ON IA_IM_ProcesarFacturasIA.IMDocumentosSoporteDoID = IMDocumentosSoporteDo.IMDocumentosSoporteDoID
                                WHERE IA_IM_ProcesarFacturasIA.DocImpoID = ? AND IAPR_FacturaEnviadaProcesar = 1 AND ISNULL(IAPR_Procesado,0) = 0""", (docimpoid))

            archivos_path = cursor.fetchall()
            logging.info(f"{len(archivos_path)} factura(s) encontrada(s) para procesar. Detalles: {archivos_path}")
            _status_update(request_id, total_facturas=len(archivos_path), message=f"{len(archivos_path)} facturas encontradas")
            conn.commit()

            cursor.close()
            conn.close()

            for ruta_path in archivos_path:
                IAPR_ProcesarFacturaID = ruta_path[1]
                tipodoc = ruta_path[2]
                facturas_sin_iniciar = buscarIAPR_ProcesarFacturaID_sininiciar(IAPR_ProcesarFacturaID)
                if facturas_sin_iniciar == True:
                    logging.debug(f"RESULTADO BUSQUEDA DE FACTURAS ID SIN INICIAR: {facturas_sin_iniciar}")
                    countsaltadas += 1
                    _status_add_item(
                        request_id,
                        {
                            "IAPR_ProcesarFacturaID": IAPR_ProcesarFacturaID,
                            "ruta": ruta_path[0],
                            "estado": "skipped",
                            "mensaje": "Factura ya iniciada previamente (FechaInicioProcesamiento no nula)",
                        },
                    )
                    continue
                else:
                    ruta_path = ruta_path[0].replace('1.7', '10.39')
                    logging.debug(f"Ruta modificada del archivo: {ruta_path}")

                    estado_factura = estado_procesado(IAPR_ProcesarFacturaID, 0)
                    logging.debug(f"Estado de factura recuperado: {estado_factura}")

                    extension_archivo = verificar_tipo_doc(ruta_path)
                    logging.debug(f"Extensión del archivo: {extension_archivo}")

                    if extension_archivo.lower() == 'pdf' and estado_factura[3] == 0:
                        try:
                            logging.info(f"Procesando archivo PDF: {ruta_path}")
                            fecha_inicio_procesamiento = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                            informacioninicioprocesamiento(IAPR_ProcesarFacturaID, fecha_inicio_procesamiento)
                            data_factura, items_factura = procesar_factura(ruta_path, estado_factura[5], tipodoc)
                            logging.info(f"Datos extraídos: {data_factura}, {len(items_factura) if items_factura else 0} ítem(s)")

                            if data_factura and items_factura: # añadir validacion de facturaid unico por cliente 
                                IAFAC_FacturaID = insertar_datafactura(data_factura, estado_factura[0], estado_factura[5])
                                if not IAFAC_FacturaID:
                                    raise ValueError("No se logró insertar el encabezado de factura en IA_IM_Factura.")
                                insertar_itemsfactura(IAFAC_FacturaID, items_factura)

                                estado_procesado(IAPR_ProcesarFacturaID, 1)
                                estado_procesamientoia(0, IAFAC_FacturaID)
                                validaprocesamientoia(IAPR_ProcesarFacturaID, 0, '')
                                countfacturasok += 1
                                _status_add_item(
                                    request_id,
                                    {
                                        "IAPR_ProcesarFacturaID": IAPR_ProcesarFacturaID,
                                        "ruta": ruta_path,
                                        "estado": "ok",
                                        "IAFAC_FacturaID": IAFAC_FacturaID,
                                        "mensaje": "Factura insertada correctamente",
                                    },
                                )

                                logging.info(f"Factura procesada exitosamente. IAPR_ProcesarFacturaID={IAPR_ProcesarFacturaID}")
                            else:
                                raise ValueError("No se extrajeron datos válidos de la factura.")
                        except Exception as e:
                            logging.error(f"Error procesando factura ID {IAPR_ProcesarFacturaID}: {e} - {traceback.format_exc()}")
                            logging.debug(traceback.format_exc())

                            validaprocesamientoia(IAPR_ProcesarFacturaID, 1, f'Error al insertar la información: {str(e)}')
                            estado_procesado(IAPR_ProcesarFacturaID, 1)
                            countfacturasnoprocesadas += 1
                            _status_add_item(
                                request_id,
                                {
                                    "IAPR_ProcesarFacturaID": IAPR_ProcesarFacturaID,
                                    "ruta": ruta_path,
                                    "estado": "error",
                                    "mensaje": str(e),
                                },
                            )

                        fecha_final_procesamiento = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                        informacionfinalizacionprocesamiento(IAPR_ProcesarFacturaID, fecha_final_procesamiento)
                    else:
                        logging.warning(f"Omitiendo archivo: formato no válido o ya procesado. IAPR_ProcesarFacturaID={IAPR_ProcesarFacturaID} - {traceback.format_exc()}")
                        estado_procesado(IAPR_ProcesarFacturaID, 1)
                        countsaltadas += 1
                        _status_add_item(
                            request_id,
                            {
                                "IAPR_ProcesarFacturaID": IAPR_ProcesarFacturaID,
                                "ruta": ruta_path,
                                "estado": "skipped",
                                "mensaje": "Formato no válido o ya procesado",
                            },
                        )
            
            # Acciones según número de facturas no procesadas
            if countfacturasnoprocesadas == len(archivos_path):
                logging.warning("Todas las facturas fallaron en el procesamiento. Notificando a CAMTOM con código 7.")
                conn = conectar_sql_server()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("{CALL SP_ProcesosIA (?, ?)}", (7, int(docimpoid)))
                    conn.commit()
                    cursor.close()
                    conn.close()
            else:
                logging.info("Al menos una factura procesada correctamente. Notificando a CAMTOM con código 2.")
                conn = conectar_sql_server()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("{CALL SP_ProcesosIA (?, ?)}", (2, int(docimpoid)))
                    conn.commit()
                    cursor.close()
                    conn.close()

            logging.info(f"Finalizó procesamiento para docimpoid {docimpoid}")
            logging.info(f":::::::::::::::::::::::::::::::::::::::::::::::::::")
            print(f"Finalizó procesamiento para docimpoid {docimpoid}")
            print(f":::::::::::::::::::::::::::::::::::::::::::::::::::")
            _status_update(
                request_id,
                status="completed",
                message="Procesamiento finalizado",
                finished_at=datetime.now().isoformat(),
                procesadas_ok=countfacturasok,
                procesadas_error=countfacturasnoprocesadas,
                saltadas=countsaltadas,
            )

    except Exception as e:
        logging.critical(f"Error fatal durante el procesamiento de docimpoid {docimpoid}: {e}")
        logging.debug(traceback.format_exc())
        logging.error(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
        _status_update(
            request_id,
            status="error",
            message=str(e),
            finished_at=datetime.now().isoformat(),
        )
    
@app.get("/procesoclasificacion/{docimpoid:path}")
async def procesoclasificacion(docimpoid: str, background_tasks: BackgroundTasks):
    # Validamos rápidamente el parámetro y delegamos el procesamiento pesado
    if not docimpoid:
        return {"error": "DocImpoID no puede estar vacío"}
    
    # Añadimos la tarea al sistema de tareas en background de FastAPI
    background_tasks.add_task(procesoclasificacion_background, docimpoid)
    
    # Devolvemos respuesta inmediata al cliente
    return {"status": "processing", "docimpoid": docimpoid}

async def procesoclasificacion_background(docimpoid: str):
    
    # llega confirmada por jit descripcion, marca, cod interno o referencia

    try:
        logging.info(f"Iniciando proceso de clasificación arancelaria para docimpoid: {docimpoid}")

        conn = conectar_sql_server()
        id_y_descripcion = None
        IAFAC_FacturaID = None
        IAItemFAC_ItemFacID = None

        if conn:
            cursor = conn.cursor()
            logging.info("Conexión a SQL Server establecida. Ejecutando consulta de trabajo...")

            cursor.execute("""
                SELECT TRABAJO.IAFAC_FacturaID, TRABAJO.IAItemFAC_ItemFacID, TRABAJO.IAItemFAC_Descripcion, TRABAJO.RefProductoID 
                FROM IA_IM_FacturaItem TRABAJO
                INNER JOIN BSReferenciaProducto REFPRODUCTO
                ON REFPRODUCTO.RefProductoID = TRABAJO.RefProductoID
                JOIN
                    (SELECT IAFAC_FacturaID
                    FROM IA_IM_ProcesarFacturasIA
                    RIGHT JOIN IA_IM_Factura
                    ON IA_IM_ProcesarFacturasIA.IAPR_ProcesarFacturaID = IA_IM_Factura.IAPR_ProcesarFacturaID
                    WHERE IA_IM_ProcesarFacturasIA.DocImpoID = ? AND IA_IM_ProcesarFacturasIA.IAPR_FacturaEnviadaJITClasificar = 1
                           AND (IA_IM_Factura.IAFAC_EstadosProcesamientoIA IS NULL OR IA_IM_Factura.IAFAC_EstadosProcesamientoIA = 0)) ENCABEZADO
                ON TRABAJO.IAFAC_FacturaID = ENCABEZADO.IAFAC_FacturaID
                WHERE (REFPRODUCTO.RefProductoEstado NOT IN ('C', 'V') OR IA_IM_EnviarClasificar = 1)
            """, (docimpoid,))

            id_y_descripcion = cursor.fetchall()
            logging.info(f"Se recuperaron {len(id_y_descripcion)} registro(s) para clasificación.")

            conn.commit()

            if not id_y_descripcion:
                logging.warning(f"No se encontraron registros para clasificar con docimpoid {docimpoid}.")
                return

            IAFAC_FacturaID = id_y_descripcion[0][0]

            estado_procesamientoia(1, IAFAC_FacturaID)
            logging.info(f"Marcado estado de procesamiento IA = 1 para IAFAC_FacturaID: {IAFAC_FacturaID}")

            json_iddescripcion = [
                {
                    "IDCAMTOMENCABEZADO": t[0],
                    "IDCAMTOMTRABAJO": t[1],
                    "DESCRIPTION": t[2],
                    "RefProductoID": t[3]
                }
                for t in id_y_descripcion
            ]

            df = pd.DataFrame(json_iddescripcion)
            print(df)
            logging.debug(f"DataFrame creado a partir de los datos obtenidos: {df.shape[0]} filas.")

            itemsprocesados = xlsx_process(df)
            itemsprocesados = replace_nan_with_none(itemsprocesados)
            logging.info(f"Items procesados: {len(itemsprocesados)}")

            if itemsprocesados:

                    # ✅ usa la MISMA conexión para todo el loop
                    RutaFichaTecnica = None

                    for item in itemsprocesados:
                        print("KEYS:", list(item.keys()))
                        print("ITEM:", item)

                        IAFAC_FacturaID = item.get('IDCAMTOMENCABEZADO')
                        IAItemFAC_ItemFacID = item.get('IDCAMTOMTRABAJO')
                        acuerdos_comerciales = item.get('ACUERDOS COMERCIALES')
                        posarancelID = str(item.get('HS CODE', SINDATOS))

                        RefProductoID = item.get('REFPRODUCTOID')
                        RefProductoID = int(RefProductoID) if RefProductoID not in (None, "", "NULL", "None") else None

                        # ✅ IMPORTANTE: reiniciar por ítem (para que no se quede el del ítem anterior)
                        RutaFichaTecnica = None

                        ###################################### BUSQUEDA DE FICHAS TECNICAS ######################################
                        logging.info("Consultando si existe FICHA TECNICA para item por procesar...")

                        cursor.execute("""
                            select dbo.RutaDocumentosServer7(DCF.DocImpoID) + Ruta
                            from IA_IM_FacturaItem as IMFI
                            INNER JOIN TMPDocumentosCompletarFactura as DCF ON DCF.IAItemFAC_ItemfacID = IMFI.IAItemFAC_ItemfacID
                            where DCF.DocImpoID = ? and DCF.tipodocumentoid = 3 and IMFI.IAItemFAC_ItemfacID = ?
                        """, (docimpoid, IAItemFAC_ItemFacID))

                        ficha_row = cursor.fetchone()
                        ficha_path = ficha_row[0] if ficha_row else None
                        logging.info(f"FICHA TECNICA para item {IAItemFAC_ItemFacID}: {ficha_path}")

                        if ficha_path:
                            RutaFichaTecnica = ficha_path.replace('1.7', '10.39')

                        #########################################################################################################

                        descminimasaplicables, descminimasobligatorias = endpointminimas(
                            item.get('DESCRIPTION'),
                            str(item.get('HS CODE')),
                            RefProductoID,
                            RutaFichaTecnica  # puede ser None y está bien
                        )

                        print(f"descminimas {descminimasaplicables}, {descminimasobligatorias}")

                        params = (
                            float(item.get('CONFIDENCE')) if item.get('CONFIDENCE') is not None else 0,
                            posarancelID,
                            item.get('SUMMARY CLASSIFICATION', SINDATOS),
                            item.get('JUSTIFICATION', SINDATOS),
                            item.get('RECOMMENDATIONS', SINDATOS),
                            int(item.get('ARANCEL')) if item.get('ARANCEL') is not None else 0,
                            int(item.get('ARANCEL VARIABLE')) if item.get('ARANCEL VARIABLE') is not None else 0,
                            int(item.get('IVA')) if item.get('IVA') is not None else 0,
                            int(item.get('UNIDAD COMERCIAL ID')) if item.get('UNIDAD COMERCIAL ID') is not None else 0,
                            str(descminimasaplicables).replace("=", ":"),
                            str(descminimasobligatorias).replace("=", ":"),
                            item.get('REGIMEN LICENCIA PREVIA', SINDATOS),
                            item.get('CONSEJO NACIONAL ESTUPEFACIENTES', SINDATOS),
                            item.get('FONDO NACIONAL ESTUPEFACIENTES', SINDATOS),
                            item.get('INSTITUTO COLOMBIANO AGROPECUARIO', SINDATOS),
                            item.get('DESCRIPCION MINIMA', SINDATOS),
                            item.get('INDUSTRIA MILITAR', SINDATOS),
                            item.get('INGEOMINAS', SINDATOS),
                            item.get('INSTITUTO NACIONAL PESCA', SINDATOS),
                            item.get('INSTITUTO NACIONAL VIGILANCIA MEDICAMENTOS Y ALIMENTOS', SINDATOS),
                            item.get('MINISTERIO AGRICULTURA', SINDATOS),
                            item.get('MINISTERIO DESARROLLO', SINDATOS),
                            item.get('AMOUNT', SINDATOS),
                            item.get('MINISTERIO TRANSPORTE', SINDATOS),
                            item.get('MINISTERIO MEDIO AMBIENTE', SINDATOS),
                            item.get('MINISTERIO SALUD', SINDATOS),
                            item.get('SUPER INTENDENCIA VIGILANCIA Y SEGURIDAD', SINDATOS),
                            item.get('SUPERINTENDENCIA INDUSTRIA Y COMERCIO', SINDATOS),
                            item.get('AUTOPARTES Y COMPLEMENTOS', SINDATOS),
                            item.get('MEDIDAS ANTIDUMPING', SINDATOS),
                            item.get('OBSERVACIONES', SINDATOS),
                            item.get('DECRETO1', SINDATOS),
                            item.get('DECRETO2', SINDATOS),
                            ', '.join(acuerdos_comerciales) if isinstance(acuerdos_comerciales, list)
                                else acuerdos_comerciales if isinstance(acuerdos_comerciales, str)
                                else SINDATOS,
                            IAItemFAC_ItemFacID
                        )

                        try:
                            cursor.execute("""
                                UPDATE IA_IM_FacturaItem
                                SET
                                    IAItemFAC_Confiabilidad = ?, IAItemFAC_PosArancelID = ?, IAItemFAC_ResumenClasificacion = ?, IAItemFAC_JustificacionClasificacion = ?, IAItemFAC_RecomendacionesClasificacion = ?,
                                    IAItemFAC_posArancelArancel = ?, IAItemFAC_posArancelArancelVar = ?, IAItemFAC_posArancelIva = ?, IAItemFAC_posArancelUcomercialId = ?,
                                    IAItemFAC_posArancelMinimasAplicables = ?, IAItemFAC_posArancelMinimasObligatorias = ?, IAItemFAC_requisitosRegimenLicenciaPrevia = ?,
                                    IAItemFAC_requisitosCnestupefacientes = ?, IAItemFAC_requisitosFnestupefacientes = ?, IAItemFAC_requisitosIcagropecuario = ?,
                                    IAItemFAC_requisitosDescMinima = ?, IAItemFAC_requisitosIndustriaMilitar = ?, IAItemFAC_requisitosIngeominas = ?, IAItemFAC_requisitosInpesca = ?,
                                    IAItemFAC_requisitosInvmedyalimentos = ?, IAItemFAC_requisitosMinAgricultura = ?, IAItemFAC_requisitosMinDesarrollo = ?, IAItemFAC_requisitosMinMinas = ?,
                                    IAItemFAC_requisitosMinTransporte = ?, IAItemFAC_requisitosMinMedioAmbiente = ?, IAItemFAC_requisitosMinSalud = ?, IAItemFAC_requisitosSupintVigySeguridad = ?,
                                    IAItemFAC_requisitosSupintIndyComercio = ?, IAItemFAC_requisitosAutopartesYComplementos = ?, IAItemFAC_requisitosMedidasAntidumping = ?,
                                    IAItemFAC_requisitosObservaciones = ?, IAItemFAC_requisitosDecreto1 = ?, IAItemFAC_requisitosDecreto2 = ?, IAItemFAC_posArancelAcuerdosComerciales = ?
                                WHERE IAItemFAC_ItemFacID = ?
                            """, params)

                            conn.commit()
                            logging.info(f"Actualización exitosa de IAItemFAC_ItemFacID {IAItemFAC_ItemFacID}")

                        except Exception as e:
                            conn.rollback()
                            logging.error(f"Error al actualizar IAItemFAC_ItemFacID {IAItemFAC_ItemFacID}: {e}")
                            logging.debug(traceback.format_exc())

                    # ✅ Cerrar UNA sola vez, al final
                    cursor.close()
                    conn.close()

                    estado_procesamientoia(2, IAFAC_FacturaID)
                    logging.info(f"Proceso de clasificación completado para IAFAC_FacturaID {IAFAC_FacturaID}")
            else:
                logging.warning("No se encontraron ítems procesados para actualizar.")
                estado_procesamientoia(2, IAFAC_FacturaID)
            
            logging.info(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")

    except Exception as e:
        logging.critical(f"Error en proceso de clasificación para docimpoid {docimpoid}: {e} ")
        logging.debug(traceback.format_exc())
        if IAFAC_FacturaID:
            estado_procesamientoia(5, IAFAC_FacturaID)
        logging.error(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")

    # estado_procesamientoia(3, IAFAC_FacturaID)

    # print(datato_excel_productos)

    # return datato_excel_factura, datato_excel_productos

def ejecutar_consulta_idmaestro(id_maestro, ref_cod_interno_cliente, ref_producto_referencia):
    conn = conectar_sql_server()
    cursor = conn.cursor()

    # Imprimir los parámetros para verificar su valor
    print(f"Parámetros de la consulta - IDMaestro: {id_maestro}, RefCodInternoCliente: {ref_cod_interno_cliente}, RefProductoReferencia: {ref_producto_referencia}")

    # Crear la consulta SQL con los parámetros recibidos
    consulta = """
                SELECT IAItemFAC_ItemFacID, IAFAC_FacturaID
                FROM IA_IM_FacturaItem  
                WHERE (IAItemFAC_CodInterno = ? OR IAItemFAC_Referencia = ?) 
                AND IAFAC_FacturaID IN 
                (
                    SELECT IAFAC_FacturaID 
                    FROM IA_IM_Factura 
                    WHERE IAPR_ProcesarFacturaID IN 
                    (
                        SELECT IAPR_ProcesarFacturaID 
                        FROM IA_IM_ProcesarFacturasIA
                        WHERE IDMaestro = ?
                    )
                )
                """

    try:
        # Ejecutar la consulta con los parámetros pasados
        cursor.execute(consulta, (ref_cod_interno_cliente, ref_producto_referencia, id_maestro))

        # Obtener los resultados
        resultados = cursor.fetchone()

        # Si la consulta retorna algún resultado, devolverlo
        if resultados:
            print(f"{resultados[0]} - {resultados[1]}")
            return resultados[0], resultados[1]
        else:
            print("No se encontraron resultados.")
            return [], []

    except Exception as e:
        print(f"Error ejecutando la consulta: {e} - {traceback.format_exc}")
        return [], []

    finally:
        cursor.close()
        conn.close()

class RutaRequest(BaseModel):
    ruta: str
    idmaestro: str

@app.post("/procesoexcel")
async def procesoexcel(request_data: RutaRequest, background_tasks: BackgroundTasks):
    ruta = request_data.ruta
    idmaestro = request_data.idmaestro
    
    # Validamos rápidamente el parámetro
    if not ruta and not idmaestro:
        return {"error": "ruta/idmaestro no pueden estar vacío"}
    
    # Añadimos la tarea al sistema de tareas en background de FastAPI
    background_tasks.add_task(procesoexcel_background, ruta, idmaestro)
    
    # Devolvemos respuesta inmediata al cliente
    return {"status": "processing", "ruta": ruta}

def leer_archivo_excel(ruta):
    extension = os.path.splitext(ruta)[1].lower()

    try:
        if extension in ['.xls', '.xlsx']:
            logging.info(f"Leyendo archivo Excel: {ruta}")
            df = pd.read_excel(ruta, engine='openpyxl' if extension == '.xlsx' else 'xlrd')
            metodo_exitoso = "xlsx" if extension == '.xlsx' else "xls"

            logging.info("--- INFORMACIÓN DEL ARCHIVO ---")
            logging.info(f"Método de lectura exitoso: {metodo_exitoso}")
            logging.info(f"Filas: {len(df)}")
            logging.info(f"Columnas: {len(df.columns)}")
            return df
        else:
            logging.warning(f"Extensión de archivo no soportada: {extension}")
            return None
    except Exception as e:
        logging.error(f"Error al leer el archivo Excel: {e}", exc_info=True)
        return None

async def procesoexcel_background(ruta: str, idmaestro: str):
    try:
        logging.info(f"Iniciando procesamiento de archivo Excel: {ruta} para idmaestro: {idmaestro}")
        df = leer_archivo_excel(ruta)
        datos_excel = []

        if df is not None:
            logging.info(f"Columnas encontradas: {df.columns.tolist()}")
            df.columns = df.columns.str.replace(' ', '_')

            for fila in df.itertuples():
                try:
                    valor_codinterno = '' if pd.isna(fila.Codigo_Interno) else fila.Codigo_Interno
                    valor_referencia = '' if pd.isna(fila.Referencia) else fila.Referencia

                    IAItemFAC_ItemFacID, IAFAC_FacturaID = ejecutar_consulta_idmaestro(idmaestro, str(valor_codinterno), str(valor_referencia))
                    descripcion = f"{fila.Referencia} - {fila.Marca} - {fila.Codigo_Interno} - {fila.Nombre_Tecnico_del_Producto} - {fila.Nombre_Comercial_del_Producto} - {fila.Que_Funcion_cumple_el_Producto}"
                    
                    datos_excel.append({
                        "IAItemFAC_ItemFacID": IAItemFAC_ItemFacID,
                        "IAFAC_FacturaID": IAFAC_FacturaID,
                        "Description": descripcion
                    })

                    logging.debug(f"Procesado: Trabajo={IAItemFAC_ItemFacID}, Referencia={valor_referencia}")
                except Exception as e:
                    logging.error(f"Error al procesar fila: {fila} - {e}", exc_info=True)
                    continue

            df_resultado = pd.DataFrame(datos_excel)
            itemsprocesados = replace_nan_with_none(xlsx_process(df_resultado))

        if itemsprocesados and IAItemFAC_ItemFacID:

            conn = conectar_sql_server()
            cursor = conn.cursor()

            try:
                for item in itemsprocesados:
                    IAFAC_FacturaID = item.get('IDCAMTOM ENCABEZADO')
                    IAItemFAC_ItemFacID = item.get('IDCAMTOM TRABAJO')
                    acuerdos_comerciales = item.get('ACUERDOS COMERCIALES')
                    descminimasaplicables = item.get('DESCRIPCIONES MINIMAS APLICABLES')
                    descminimasobligatorias = item.get('DESCRIPCIONES MINIMAS OBLIGATORIAS')

                    try:
                        cursor.execute("""
                            UPDATE IA_IM_FacturaItem SET
                                IAItemFAC_Confiabilidad = ?, IAItemFAC_PosArancelID = ?, IAItemFAC_ResumenClasificacion = ?, IAItemFAC_JustificacionClasificacion = ?, IAItemFAC_RecomendacionesClasificacion = ?,
                                IAItemFAC_posArancelArancel = ?, IAItemFAC_posArancelArancelVar = ?, IAItemFAC_posArancelIva = ?, IAItemFAC_posArancelUcomercialId = ?,
                                IAItemFAC_posArancelMinimasAplicables = ?, IAItemFAC_posArancelMinimasObligatorias = ?, IAItemFAC_requisitosRegimenLicenciaPrevia = ?,
                                IAItemFAC_requisitosCnestupefacientes = ?, IAItemFAC_requisitosFnestupefacientes = ?, IAItemFAC_requisitosIcagropecuario = ?,
                                IAItemFAC_requisitosDescMinima = ?, IAItemFAC_requisitosIndustriaMilitar = ?, IAItemFAC_requisitosIngeominas = ?, IAItemFAC_requisitosInpesca = ?,
                                IAItemFAC_requisitosInvmedyalimentos = ?, IAItemFAC_requisitosMinAgricultura = ?, IAItemFAC_requisitosMinDesarrollo = ?, IAItemFAC_requisitosMinMinas = ?,
                                IAItemFAC_requisitosMinTransporte = ?, IAItemFAC_requisitosMinMedioAmbiente = ?, IAItemFAC_requisitosMinSalud = ?, IAItemFAC_requisitosSupintVigySeguridad = ?,
                                IAItemFAC_requisitosSupintIndyComercio = ?, IAItemFAC_requisitosAutopartesYComplementos = ?, IAItemFAC_requisitosMedidasAntidumping = ?,
                                IAItemFAC_requisitosObservaciones = ?, IAItemFAC_requisitosDecreto1 = ?, IAItemFAC_requisitosDecreto2 = ?, IAItemFAC_posArancelAcuerdosComerciales = ?
                            WHERE IAItemFAC_ItemFacID = ?
                        """, (
                            float(item.get('CONFIDENCE')) if item.get('CONFIDENCE') is not None else 0,
                            str(item.get('HS CODE', SINDATOS)),
                            item.get('SUMMARY CLASSIFICATION', SINDATOS),
                            item.get('JUSTIFICATION', SINDATOS),
                            item.get('RECOMMENDATIONS', SINDATOS),
                            item.get('ARANCEL') or 0,
                            item.get('ARANCEL VARIABLE') or 0,
                            item.get('IVA') or 0,
                            item.get('UNIDAD COMERCIAL ID') or 0,
                            ', '.join(descminimasaplicables) if isinstance(descminimasaplicables, list) else SINDATOS,
                            ', '.join(descminimasobligatorias) if isinstance(descminimasobligatorias, list) else SINDATOS,
                            item.get('REGIMEN LICENCIA PREVIA', SINDATOS),
                            item.get('CONSEJO NACIONAL ESTUPEFACIENTES', SINDATOS),
                            item.get('FONDO NACIONAL ESTUPEFACIENTES', SINDATOS),
                            item.get('INSTITUTO COLOMBIANO AGROPECUARIO', SINDATOS),
                            item.get('DESCRIPCION MINIMA', SINDATOS),
                            item.get('INDUSTRIA MILITAR', SINDATOS),
                            item.get('INGEOMINAS', SINDATOS),
                            item.get('INSTITUTO NACIONAL PESCA', SINDATOS),
                            item.get('INSTITUTO NACIONAL VIGILANCIA MEDICAMENTOS Y ALIMENTOS', SINDATOS),
                            item.get('MINISTERIO AGRICULTURA', SINDATOS),
                            item.get('MINISTERIO DESARROLLO', SINDATOS),
                            item.get('AMOUNT', SINDATOS),
                            item.get('MINISTERIO TRANSPORTE', SINDATOS),
                            item.get('MINISTERIO MEDIO AMBIENTE', SINDATOS),
                            item.get('MINISTERIO SALUD', SINDATOS),
                            item.get('SUPER INTENDENCIA VIGILANCIA Y SEGURIDAD', SINDATOS),
                            item.get('SUPERINTENDENCIA INDUSTRIA Y COMERCIO', SINDATOS),
                            item.get('AUTOPARTES Y COMPLEMENTOS', SINDATOS),
                            item.get('MEDIDAS ANTIDUMPING', SINDATOS),
                            item.get('OBSERVACIONES', SINDATOS),
                            item.get('DECRETO1', SINDATOS),
                            item.get('DECRETO2', SINDATOS),
                            ', '.join(acuerdos_comerciales) if isinstance(acuerdos_comerciales, list)
                                else acuerdos_comerciales if isinstance(acuerdos_comerciales, str)
                                else SINDATOS,
                            IAItemFAC_ItemFacID
                        ))

                        conn.commit()
                        logging.info(f"Actualización exitosa de IAItemFAC_ItemFacID: {IAItemFAC_ItemFacID}")

                    except Exception as e:
                        conn.rollback()
                        logging.error(f"Error al actualizar IAItemFAC_ItemFacID {IAItemFAC_ItemFacID}: {e}", exc_info=True)

                estado_procesamientoia(4, IAFAC_FacturaID)
                logging.info(f"Estado de procesamiento IA actualizado a 4 para encabezado {IAFAC_FacturaID}")

            finally:
                cursor.close()
                conn.close()


                estado_procesamientoia(4, IAFAC_FacturaID)
                logging.info(f"Estado de procesamiento IA actualizado a 4 para encabezado {IAFAC_FacturaID}")

            logging.info("Proceso Excel completado exitosamente.")
            return {"status": "success"}

        else:
            logging.warning("El archivo no pudo ser leído correctamente o no contiene datos.")
            return {"status": "error", "mensaje": "Archivo vacío o ilegible"}

    except Exception as e:
        logging.critical(f"Error crítico en procesoexcel_background: {e}", exc_info=True)
        return {"status": "error", "mensaje": str(e)}
