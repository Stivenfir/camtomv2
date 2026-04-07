import requests
import pyodbc
import re
import os
import spacy
import dateparser
from dateutil.parser import parse
from datetime import datetime
from snippedtexto import peticion_descripcion_producto, obtener_clasificacion_arancelaria

CONEXION_FALLIDA = "No se pudo establecer conexión con la base de datos."

# conectar a bdd
def conectar_sql_server():
    try:
        server = "172.16.10.54\\DBABC21"
        database = "Repecev2005_H"
        username = "Repecev2005"
        password = ""

        conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}')
        return conn
    except Exception as e:
        print(f"Error al conectar a SQL Server: {e}")
        return None

def obtener_rutafacturas():
    conn = conectar_sql_server()
    
    if conn:
        cursor = conn.cursor()
        
        # Consulta SQL para obtener el ID del cliente basándose en el nombre
        query = """
        SELECT *
        FROM ProcesarFacturasIA
        WHERE Procesado = 0 AND ClienteID is not null
        """
        
        cursor.execute(query)
        result = cursor.fetchall()

        if result:
            cursor.close()
            conn.close()
            return result
        else:
            cursor.close()
            conn.close()
            return None
    else:
        print(CONEXION_FALLIDA)
        return None

# Función para obtener el ID del cliente desde la base de datos
def obtener_cliente_id(cliente_nombre):
    conn = conectar_sql_server()
    
    if conn:
        cursor = conn.cursor()
        
        # Consulta SQL para obtener el ID del cliente basándose en el nombre
        query = """
        SELECT ClienteID
        FROM vCliente
        WHERE ClienteNombre LIKE ?
        """
        
        cursor.execute(query, (f"%{cliente_nombre}%",))
        result = cursor.fetchone()

        if result:
            # Si encontramos al cliente, devolvemos su ID
            cliente_id = result[0]
            print(f"Cliente encontrado. ID: {cliente_id}")
            cursor.close()
            conn.close()
            return cliente_id
        else:
            print(f"Cliente con nombre {cliente_nombre} no encontrado en la base de datos.")
            cursor.close()
            conn.close()
            return None
    else:
        print(CONEXION_FALLIDA)
        return None

# Función para obtener el ID de la Factura
def obtener_factura_id(factura_numero):
    conn = conectar_sql_server()
    
    if conn:
        cursor = conn.cursor()
        
        # Consulta SQL para obtener el ID de la factura basándose en el numero
        query = """
        SELECT FacturaID
        FROM IMFactura
        WHERE FacturaNumero = ?
        """
        
        cursor.execute(query, factura_numero,)
        result = cursor.fetchone()

        if result:
            # Si encontramos al cliente, devolvemos su ID
            factura_id = result[0]
            print(f"Factura encontrada. ID: {factura_id}")
            cursor.close()
            conn.close()
            return factura_id
        else:
            print(f"Factura con numero {factura_numero} no encontrado en la base de datos.")
            cursor.close()
            conn.close()
            return None
    else:
        print(CONEXION_FALLIDA)
        return None

def obtener_reproducto_id(refproducto_referencia, RefProductoDescripcion, PosArancelariaID, RefProductoMarca, cliente_id):
    conn = conectar_sql_server()
    cursor = conn.cursor()

    result_cliente = None
    
    if conn:
        if refproducto_referencia != None:

            # Consulta para obtener el cliente
            query_clienteid = """SELECT * FROM BSClienteTipoFactura WHERE CLIENTEID = ?"""
            cursor.execute(query_clienteid, cliente_id)

            result_cliente = cursor.fetchone()

            print("resultado obtener_producto_id: " + str(result_cliente[0]) if result_cliente else "Cliente no encontrado.")
            input("stop.")  # Para detener y revisar el resultado

            # Verificamos si el producto ya existe antes de insertarlo
            check_query = """
                SELECT RefProductoID
                FROM BSReferenciaProducto
                WHERE (RefProductoDescripcion = ? OR (RefProductoDescripcion IS NULL AND ? IS NULL))
                AND (PosArancelariaID = ? OR (PosArancelariaID IS NULL AND ? IS NULL))
                AND (RefProductoMarca = ? OR (RefProductoMarca IS NULL AND ? IS NULL))
                AND (RefClienteID = ? OR (RefClienteID IS NULL AND ? IS NULL))
            """
            cursor.execute(check_query, (RefProductoDescripcion, RefProductoDescripcion, PosArancelariaID, PosArancelariaID, RefProductoMarca, RefProductoMarca, cliente_id, cliente_id))
            existing_product = cursor.fetchone()

            print(f"stoooooppppp - {existing_product}")

            if existing_product is not None:
                # Si ya existe un producto con la misma referencia, descripción y otras características
                refproducto_id = existing_product[0]
                print(f"Producto con referencia {refproducto_referencia} ya existe con ID: {refproducto_id}")
                cursor.close()
                conn.close()
                return refproducto_id
            else:
                # Si no existe el producto, insertamos uno nuevo
                print(f"Producto con referencia {refproducto_referencia} no encontrado, creando nuevo registro.")
                print(f"con información: {refproducto_referencia, RefProductoDescripcion, PosArancelariaID, RefProductoMarca, 0, cliente_id}")
                
                # Insertamos un nuevo producto en la tabla BSReferenciaProducto
                if result_cliente:  # Usamos RefCodInternoCliente si existe
                    insert_query = """
                        INSERT INTO BSReferenciaProducto (RefCodInternoCliente, RefProductoDescripcion, PosArancelariaID, RefProductoMarca, RefAscii, RefClienteID)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_query, (refproducto_referencia, RefProductoDescripcion, PosArancelariaID, RefProductoMarca, 0, cliente_id))
                else:  # Usamos RefProductoReferencia si no existe RefCodInternoCliente
                    insert_query = """
                        INSERT INTO BSReferenciaProducto (RefProductoReferencia, RefProductoDescripcion, PosArancelariaID, RefProductoMarca, RefAscii, RefClienteID)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_query, (refproducto_referencia, RefProductoDescripcion, PosArancelariaID, RefProductoMarca, 0, cliente_id))

                # Hacemos commit para guardar los cambios
                conn.commit()

                # Obtenemos el RefProductoID autoincremental
                cursor.execute("SELECT SCOPE_IDENTITY()")
                refproducto_id = cursor.fetchone()[0]

                print(f"Nuevo RefProductoID creado: {refproducto_id}")
                cursor.close()
                conn.close()
                return refproducto_id
        else:
            # Si no hay refproducto_referencia, no hacemos nada
            print("Referencia de producto es None, no se puede obtener ID.")
            return None
    else:
        print("Error en la conexión a la base de datos.")
        return None

# Función para obtener el ID de la unidad comercial
def obtener_unidadcomercial_id(codigo_parancelaria):
    conn = conectar_sql_server()
    
    if conn:
        cursor = conn.cursor()
        
        # Consulta SQL para obtener el ID del cliente basándose en el nombre
        query = """
        SELECT UnidadComercialID
        FROM BSPosicionArancelaria
        WHERE PosArancelID = ?
        """
        
        cursor.execute(query, codigo_parancelaria,)
        result = cursor.fetchone()

        if result:
            # Si encontramos al cliente, devolvemos su ID
            factura_id = result[0]
            print(f"ID Partida arancelaria encontrada. ID: {factura_id}")
            cursor.close()
            conn.close()
            return factura_id
        else:
            print(f"Partida arancelaria {codigo_parancelaria} no encontrado en la base de datos.")
            cursor.close()
            conn.close()
            return None
    else:
        print(CONEXION_FALLIDA)
        return None

# Función para obtener el ID del proveedor
def obtener_proveedorid(nombre_proveedor):
    conn = conectar_sql_server()
    
    if conn:
        cursor = conn.cursor()
        
        # Consulta SQL para obtener el ID del cliente basándose en el nombre
        query = """
        SELECT PersonaID
        FROM vProveedor
        WHERE LOWER(NombreCompleto) LIKE LOWER(?)
        """
        
        cursor.execute(query, f"%{nombre_proveedor}%",)
        result = cursor.fetchall()

        if result:
            # Si encontramos al cliente, devolvemos su ID
            proveedor_id = result[-1]
            proveedor_id = proveedor_id[0]
            print(f"ID proveedor encontrado. ID: {proveedor_id}")
            cursor.close()
            conn.close()
            return proveedor_id
        else:
            print(f"Proveedor {nombre_proveedor} no encontrado en la base de datos.")
            cursor.close()
            conn.close()
            return None
    else:
        print(CONEXION_FALLIDA)
        return None

# insertar imfactura
def insertar_imfactura(data):
    facturanueva = False

    conn = conectar_sql_server()
    cursor = conn.cursor()

    # Verificar si el FacturaNumero ya existe en la tabla
    query_verificar = """
        SELECT COUNT(*) 
        FROM IMFactura 
        WHERE FacturaNumero = ?
    """

    cursor.execute(query_verificar, (data['FacturaNumero'],))
    existe = cursor.fetchone()[0]  # Obtiene el número de registros encontrados

    if existe == 0:  # Si no existe el FacturaNumero
        try:
            query_insertar = """
                INSERT INTO IMFactura (ClienteID, ProveedorExtID, FacturaNumero, FacturaFecha, IncotermID, MonedaMcID, FacturaLugarEntrega, FacturaSubTotal, FacturaIntereses, FacturaTotal, FacturaRegistro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query_insertar, (data['ClienteID'], data['ProveedorExtID'], data['FacturaNumero'], data['FacturaFecha'], data['IncotermID'], data['MonedaMcID'], data['FacturaLugarEntrega'], data['FacturaSubTotal'], data['FacturaIntereses'], data['FacturaTotal'], data['FacturaRegistro']))
            conn.commit()
            print("Factura insertada correctamente.")
            facturanueva = True
        except Exception as e:
            print(e)
            facturanueva = False
    else:
        print(f"Factura con el número {data['FacturaNumero']} ya existe.")
        facturanueva = False

    # Actualizar la tabla ProcesarFacturasIA (tanto si se insertó como si ya existía)
    try:
        query_update = """
            UPDATE ProcesarFacturasIA 
            SET 
                Procesado = ?
            WHERE RutaFactura = ?
        """
        print(f"\\{data['ArchivoPath'].replace("\\\\", "\\")}")
        cursor.execute(query_update, (1, f"\\{data['ArchivoPath'].replace("\\\\", "\\")}"))
        conn.commit()
        print(f"Factura con el número {data['FacturaNumero']} actualizada correctamente en ProcesarFacturasIA.")
    except Exception as e:
        print(f"Error al actualizar en ProcesarFacturasIA: {e}")

    cursor.close()
    conn.close()

    return facturanueva

# insertar imitemfactura
def insertar_imitemfactura(data):
    conn = conectar_sql_server()  # Conectar a la base de datos
    cursor = conn.cursor()

    # Consulta SQL para insertar los datos en la tabla IMItemFactura
    query_insertar = """
        INSERT INTO IMItemFactura (FacturaID, RefProductoID, ItemFactPedido, ItemFactDescripcion, ItemFactcantidadInicialDav, ItemFactCantidadInicial, UnidadComercialID, ItemPrecioTotal, ItemPrecioOriginal, ItemPrecioUnitario, visado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    for item in data:
        # Ejecutar la consulta para cada item de la lista
        cursor.execute(query_insertar, 
                       (item['FacturaID'], item['RefProductoID'], item['ItemFactPedido'], item['ItemFactDescripcion'], item['ItemFactcantidadInicialDav'], item['ItemFactCantidadInicial'], 
                        item['UnidadComercialID'], item['ItemPrecioTotal'], item['ItemPrecioOriginal'], 
                        item['ItemPrecioUnitario'], item['visado']))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"{len(data)} items insertados correctamente.")

# verificar tipo de archivo por extension
def verificar_tipo_doc(archivo_path):
    try:
        extension_archivo = archivo_path.rfind('.')
        if extension_archivo != -1:
            subcadena_extension = archivo_path[extension_archivo + 1:].strip()

        return subcadena_extension
    except Exception as e:
        print(f"Error al extraer la extension del archivo - Revisar que la ruta y el nombre del archivo sea correcto - {e}")
        return 

def limpiar_y_convertir_a_float(value):
    # Eliminar cualquier carácter no numérico, excepto puntos y comas
    cleaned_value = re.sub(r'[^0-9.,]', '', value)
    
    # Si la coma está presente, la consideramos como separador decimal y la convertimos en punto
    if ',' in cleaned_value and '.' not in cleaned_value:
        cleaned_value = cleaned_value.replace(',', '.')
    
    # Intentamos convertir el valor limpiado a float
    try:
        return float(cleaned_value)
    except ValueError:
        # Si no se puede convertir, retornamos 0
        return 0.0

def normalizar_año(fecha):
    if re.match(r"\d{1,2}-\d{1,2}-\d{2,4}$", fecha):
        partes = fecha.split('-')
        if len(partes[2]) == 2:  # Si el año tiene 2 dígitos
            try:
                # Convertir a 4 dígitos
                fecha_obj = datetime.strptime(fecha, "%d-%m-%y")
                fecha_normalizada = fecha_obj.strftime("%d-%m-%Y")  # Convertir a 4 dígitos
                return fecha_normalizada
            except ValueError:
                return None  # Si no se puede convertir, retornamos None
        else:
            return fecha  # Si el año ya tiene 4 dígitos, lo retornamos tal cual
    return None

def procesar_fecha(fechafactura, meses):
    """
    Esta función procesa la fecha para asegurarse de que esté en el formato adecuado.
    """
    # Reemplazar los meses en español por sus números correspondientes
    for mes, numero in meses.items():
        if mes in fechafactura:
            fechafactura = fechafactura.replace(mes, numero)

    # Reemplazar caracteres innecesarios ("/", ".", ",", " " por "-")
    fechafactura = fechafactura.replace(".", "-").replace(" ", "-").replace("/", "-").replace(",", "-").replace("--", "-").replace("--", "-")
    
    print(f"Fecha procesada (antes de verificación): {fechafactura}")

    # Si la fecha está en el formato YYYY-MM-DD, la dejamos tal cual
    if re.match(r"^\d{4}-\d{2}-\d{2}$", fechafactura):
        print(f"Fecha en formato yyyy-mm-dd (sin cambios): {fechafactura}")
        return fechafactura

    # Normalizar año si es necesario
    fechafactura = normalizar_año(fechafactura)

    if fechafactura is None:
        print("Fecha procesada no válida. | No se procesó la factura")
        return "No se procesó la factura por formato de fecha inválido"

    # Verificamos si la fecha tiene el formato dd-mm-yyyy o d-m-yyyy
    if re.match(r"^\d{1,2}-\d{1,2}-\d{2,4}$", fechafactura):
        # Añadimos ceros si el día o el mes tiene un solo dígito
        fechafactura = '-'.join([str(int(part)).zfill(2) for part in fechafactura.split('-')])
        print(f"Fecha corregida (con ceros añadidos): {fechafactura}")

        return fechafactura
    else:
        print("Fecha no tiene el formato adecuado. | No se procesó la factura")
        return "No se procesó la factura por formato de fecha inválido"

# Extraemos los datos relevantes de una factura en pdf
def factura_pdf(archivo_path, cliente_id):

    nlp = spacy.load("en_core_web_sm")

    # Verificar si el archivo existe y se puede abrir
    if not os.path.exists(archivo_path) or not os.access(archivo_path, os.R_OK):
        print(f"El archivo {archivo_path} no se puede abrir o no existe.")
        return []


    data_factura = {}
    
    url_endpoint = "https://dev-flask.camtomx.com/api/v3/camtomdocs/extract-invoice?country_code=COL"

    params = {
        'user_identifier': 'jmiranda@abcrepecev.com'
    }

    headers = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    with open(archivo_path, 'rb') as file:
        files = {
            'file_path': file
        }

        response = requests.post(url_endpoint, headers=headers, params=params, files=files)

    if response.status_code == 200:
        print("solicitud exitosa")
        jsonrespuesta = response.json()
        
        print(jsonrespuesta)
        
        factura_subtotal = jsonrespuesta['invoice_data']['invoice']['subtotal']
        facturatotal = jsonrespuesta['invoice_data']['invoice']['total']

        # Mapeo de meses en español a sus números
        meses = {
            'january': '01',
            'ene': '01',
            'jan': '01',
            'february': '02',
            'feb': '02',
            'march': '03',
            'mar': '03',
            'april': '04',
            'apr': '04',
            'abr': '04',
            'may': '05',
            'june': '06',
            'jun': '06',
            'july': '07',
            'jul': '07',
            'august': '08',
            'ago': '08',
            'aug': '08',
            'september': '09',
            'sep': '09',
            'october': '10',
            'oct': '10',
            'november': '11',
            'nov': '11',
            'december': '12',
            'dic': '12',
            'dec': '12'
        }

        if jsonrespuesta['invoice_data']['invoice']['date']:
            fechafactura = jsonrespuesta['invoice_data']['invoice']['date'].replace(" .- ", "-").lower()
            fechafactura = procesar_fecha(fechafactura, meses)
            
            if fechafactura:
                # Pasamos la fecha corregida al modelo NLP para su análisis
                fechafactura_procesada = nlp(fechafactura)
                print(fechafactura_procesada.ents)  # Ver las entidades detectadas

                for ent in fechafactura_procesada.ents:
                    if ent.label_ == "DATE":
                        fechafactura = ent.text
                        print(f"Fecha extraída por NLP: {fechafactura}")
                        break
                else:
                    # Si no se encontró una entidad de tipo DATE, verificamos si cumple con el formato
                    if re.match(r"\d{2}-\d{2}-\d{4}", fechafactura):
                        print(f"Fecha válida (final): {fechafactura}")
                    else:
                        print("Fecha de factura no disponible. | No se procesó la factura")
                        fechafactura = None
                        return "No se procesó la factura por falta de campo fechafactura"
            else:
                print("Fecha no tiene el formato adecuado. | No se procesó la factura")
                fechafactura = None
                return "No se procesó la factura por formato de fecha inválido"
        else:
            print("Fecha de factura no disponible. | No se procesó la factura")
            fechafactura = None
            return "No se procesó la factura por falta de campo fechafactura"

        facturaintereses = re.sub(r'[^\d.]', '', jsonrespuesta['invoice_data']['invoice']['total_tax'].split("\n")[0].strip()) if jsonrespuesta['invoice_data']['invoice']['total_tax'] and jsonrespuesta['invoice_data']['invoice']['total_tax'].strip() != '' else None

        data_factura = {
            'ArchivoPath': archivo_path,
            'ClienteID': cliente_id,
            'ProveedorExtID': obtener_proveedorid(jsonrespuesta['invoice_data']['vendor']['address_recipient']),
            'FacturaNumero': str(jsonrespuesta['invoice_data']['invoice']['id']),
            'FacturaFecha': parse(fechafactura),
            'IncotermID': 'FOB',
            'MonedaMcID': 1,
            'FacturaLugarEntrega': str(jsonrespuesta['invoice_data']['vendor']['address']),
            'FacturaSubTotal': float(re.sub(r'[^\d.]', '', factura_subtotal)) if factura_subtotal else 0,
            'FacturaIntereses': float(facturaintereses) if facturaintereses else 0,
            'FacturaTotal': float(re.sub(r'\.(?=\d{3})', '', re.sub(r'[^\d.-]', '', facturatotal))) if facturatotal else 0,
            'FacturaRegistro': 0
        }

        if insertar_imfactura(data_factura) == True:
            data_items = []
            factura_id = obtener_factura_id(jsonrespuesta['invoice_data']['invoice']['id'])

            if factura_id != None:
                for item in jsonrespuesta['invoice_data']['items']:
                    
                    # OBTENER CLASIFICACION ARANCELARIA DEL ITEM
                    clasificacion_arancelaria = obtener_clasificacion_arancelaria(item['description']) if item['description'] else None
                    product_code = item['product_code'].replace("\n", " ") if item['product_code'] else None
                    ItemFactcantidadInicialDav = re.sub(r'[^\d.-]', '', item['quantity']) if item['quantity'] and re.sub(r'[^\d.-]', '', item['quantity']) else None

                    data_item = {
                        'FacturaID': int(factura_id),
                        'RefProductoID': obtener_reproducto_id(product_code, item['description'], clasificacion_arancelaria, 'SIN MARCA', cliente_id),
                        'ItemFactPedido': str(jsonrespuesta['invoice_data']['invoice']['purchase_order']),
                        'ItemFactDescripcion': str(item['description']),
                        'ItemFactcantidadInicialDav': float(ItemFactcantidadInicialDav) if ItemFactcantidadInicialDav else 0,
                        'ItemFactCantidadInicial': float(ItemFactcantidadInicialDav) if ItemFactcantidadInicialDav else 0,
                        'UnidadComercialIDDav': int(obtener_unidadcomercial_id(clasificacion_arancelaria)) if clasificacion_arancelaria else None,
                        'UnidadComercialID': int(obtener_unidadcomercial_id(clasificacion_arancelaria)) if clasificacion_arancelaria else None,
                        'ItemPrecioTotal': limpiar_y_convertir_a_float(item['amount']) if item['amount'] else 0,
                        'ItemPrecioOriginal': limpiar_y_convertir_a_float(item['unit_price']) if item['unit_price'] else 0,
                        'ItemPrecioUnitario': limpiar_y_convertir_a_float(item['unit_price']) if item['unit_price'] else 0,
                        'visado': 0
                    }
                    data_items.append(data_item)

                insertar_imitemfactura(data_items)
            return data_factura, data_items
        else:
            return []
    else:
        print(f"Error {response.status_code}")
        return response.text

# clasificacion de los items que se encuentran el la factura en formato pdf
def clasificacion_factura_pdf(archivo_path):
    url_endpoint = "https://dev-flask.camtomx.com/api/v3/tariffpro/extract-and-classify-invoice?country_code=COL"

    params = {
        'user_identifier': 'jmiranda@abcrepecev.com'
    }

    headers = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    with open(archivo_path, 'rb') as file:
        files = {'file_path': file}
        response = requests.post(url_endpoint, headers=headers, params=params, files=files)
        if response.status_code == 200:
            excel_file_path = 'factura_recibida.xlsx'
            with open(excel_file_path, 'wb') as excel_file:
                excel_file.write(response.content)
            return f"Archivo Excel guardado como {excel_file_path}"
        else:
            return f"error funcion clasificacion_factura_pdf() {response.status_code}"

# clasificacion de los items que se encuentran en el archivo excel
def clasificacion_excel(archivo_path):
    url_endpoint = 'https://dev-flask.camtomx.com/api/v3/tariffpro/xlsx?country_code=COL&user_identifier=optional_user_id'

    headers = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    with open(archivo_path, 'rb') as file:
        response = requests.post(url_endpoint, files={'file_path': file}, headers=headers)

    if response.status_code == 200:
        excel_file_path = 'factura_clasificada.xlsx'

        # Guardar el contenido binario como un archivo Excel
        with open(excel_file_path, 'wb') as excel_file:
            excel_file.write(response.content)

        print(f"Archivo Excel guardado como {excel_file_path}")
    else:
        print(f"error en la petición para clasificar los elementos del excel... {response.text}")

# clasificacion arancelaria de item en formato imagen (png, jpg, jpeg)
def clasificacion_imagen(archivo_path):

    url_endpoint = "https://dev-flask.camtomx.com/api/v3/tariffpro/image?user_identifier=optional_user_id&country_code=COL"

    data = {
        "img_url": archivo_path
    }
    
    params = {
        'user_identifier': 'jmiranda@abcrepecev.com'
    }
    
    headers = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    response = requests.post(url_endpoint, json=data, headers=headers, params=params)

    # Verificar la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa")
        print(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

# ejecucion general
def main():
    facturas = obtener_rutafacturas()

    #for factura in facturas:
    archivo_path = "\\\\172.16.1.7\\DocSoporte\\digitalii\\2025\\893102204251\\DS\\FACTURACOMERCIAL-9103203497_FC.PDF"
    cliente_id = 1074

    print(archivo_path)

    # verificamos la extension para saber como tratar el archivo
    extension_archivo = verificar_tipo_doc(archivo_path)

    # procedimiento por tipo de archivo
    if extension_archivo == 'pdf' or extension_archivo == 'PDF':
        # informacion de la factura
        data_factura = factura_pdf(archivo_path, cliente_id)
        # print(f"\n{data_factura[0]} \n\n{data_factura[1]}")
        input("pausa!!! " + extension_archivo + " " + archivo_path)
        """# clasificacion arancelaria
        clasificacion_factura_pdf(archivo_path)"""
    """elif extension_archivo == 'xlsx':
        print("usar endpoint excel")
        clasificacion_excel(archivo_path)
    elif extension_archivo in ['jpeg', 'jpg', 'png']:
        print("es una imagen")
        clasificacion_imagen(archivo_path)"""

if __name__  == '__main__':
    main()