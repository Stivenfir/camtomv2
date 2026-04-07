import time
import requests
import pandas as pd
import json
from io import BytesIO
import pyodbc

def job_process(job_id, HEADERS):
    print(f"Job ID obtenido: {job_id}")
            
    # Realizar la solicitud GET para obtener el estado del trabajo
    url_status = f"https://api.camtomx.com/api/v3/jobs/tariffpro/{job_id}"
    
    while True:
        # Esperar un intervalo de tiempo (por ejemplo, 30 segundos)
        time.sleep(40)  # 45 segundos de espera entre solicitudes
        
        # Hacer la solicitud GET para obtener el estado
        response_status = requests.get(url_status, headers=HEADERS)
        
        if response_status.status_code == 200:
            # Si la solicitud fue exitosa, obtener los datos JSON
            status_data = response_status.json()
            print("Estado del trabajo:", status_data)
            
            # Verificar si el estado ya no es 'in_progress' o 'queued'
            if status_data['status'] not in ['queued', 'in_progress']:
                print(f"Trabajo completado o en otro estado: {status_data['status']}")
                
                # Verificar si la clave 'result' existe en la respuesta antes de acceder a ella
                if 'result' in status_data:
                    result_url = status_data['result']
                    response = requests.get(result_url)

                    if response.status_code == 200:
                        # Usamos BytesIO para abrir el archivo descargado como un flujo de bytes
                        excel_file = BytesIO(response.content)
                        
                        # Leemos el archivo Excel directamente en un DataFrame
                        df = pd.read_excel(excel_file)
                        
                        # Convertimos el DataFrame a JSON
                        json_data = df.to_dict(orient='records')
                        
                        # retornamos el JSON
                        print(f"Contenido del archivo en formato JSON: {json_data}")
                        with open('pruebaexcel.xlsx', 'wb') as excel_file:
                            excel_file.write(response.content)
                            print(f"Archivo Excel guardado")
                        return json_data
                    else:
                        print("Error al descargar el archivo.")
                        break  # Salir del bucle si no se puede descargar el archivo
                else:
                    print(f"No se encontró la clave 'result' en la respuesta.")
                    break  # Salir si 'result' no está presente
            else:
                print(f"Trabajo en estado '{status_data['status']}', esperando...")
        else:
            print(f"Error al obtener el estado del trabajo: {response_status.status_code}")
            break  # Salir si hay un error en la solicitud


def xlsx_process(df):

    # URL de la API
    url = 'https://api.camtomx.com/api/v3/tariffpro/xlsx?country_code=COL&user_identifier=optional_user_id'

    HEADERS = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    df = df.map(lambda x: None if pd.isna(x) else x)

    # Crear un buffer en memoria para el archivo Excel
    buffer = BytesIO()

    # Guardar el DataFrame en el buffer de memoria como archivo Excel
    df.to_excel(buffer, index=False, engine='openpyxl')

    # Volver al principio del buffer
    buffer.seek(0)

    # Enviar el archivo a la API en formato binario
    files = {'file_path': ('archivo.xlsx', buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}

    # Enviar la solicitud POST
    response = requests.post(url, files=files, headers=HEADERS)

    # Comprobar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa")
        print(response.text)
        return response.text
    elif response.status_code == 202:
        # Extraer el job_id de la respuesta JSON
        response_data = response.json()
        job_id = response_data.get('job_id')
        if job_id:
            json_data = job_process(job_id, HEADERS)
            return json_data
        else:
            print("No se encontró el job_id en la respuesta.")
            return 'No se encontró job_id'
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return response.text
    
import requests
import json

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
    

def parse_descriptions(descriptions_str):
    if not descriptions_str:
        return {}

    partes = [p.strip() for p in descriptions_str.split(",") if p.strip()]
    out = {}
    for p in partes:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out

def tablaminimassql(hs_code, RefProductoIDef, applicable_descriptions, mandatory_descriptions):
    conn = conectar_sql_server()
    resultado = None

    if conn:
        cursor = conn.cursor()

        applicable_descriptions = parse_descriptions(applicable_descriptions) # 0
        mandatory_descriptions = parse_descriptions(mandatory_descriptions) # 1

        if not applicable_descriptions and not mandatory_descriptions:
            print("No hay descripciones mínimas para insertar (applicable/mandatory vacías).")
            return

        for clave, valor in applicable_descriptions.items():
            cursor.execute("""SELECT CodigoMinima FROM IMMinima WHERE NombreMinima = ?""", (clave,))
            minima_id_row = cursor.fetchone()
            minima_id = minima_id_row[0] if minima_id_row else None
            print(f"CodigoMinima para {clave}: {minima_id}")
            conn.commit()
            cursor.execute("""INSERT INTO IA_IM_MinimasReferencias (RefProductoID, PosArancelID, MinimaID, Descripcion, MinimaObligatoria) 
                           VALUES (?, ?, ?, ?, ?)""", (RefProductoIDef, hs_code, minima_id, valor, 0))
            conn.commit()

        for clave, valor in mandatory_descriptions.items():
            cursor.execute("""SELECT CodigoMinima FROM IMMinima WHERE NombreMinima = ?""", (clave,))
            minima_id_row = cursor.fetchone()
            minima_id = minima_id_row[0] if minima_id_row else None
            print(f"CodigoMinima para {clave}: {minima_id}")
            conn.commit()
            cursor.execute("""INSERT INTO IA_IM_MinimasReferencias (RefProductoID, PosArancelID, MinimaID, Descripcion, MinimaObligatoria) 
                           VALUES (?, ?, ?, ?, ?)""", (RefProductoIDef, hs_code, minima_id, valor, 1))
            conn.commit()

        print(f"Datos consultados de la tabla IMMinima: {resultado}")

    # Cerrar la conexión
    cursor.close()
    conn.close()

##, refproductoid
def endpointminimas(descripcion, hs_code,refproductoid, ficha_path):

    print(f"Procesando endpointminimas para HS Code: {hs_code}, RefProductoID: {refproductoid}, Ficha Técnica: {ficha_path}")
    # URL de la API
    url = 'https://api.camtomx.com/api/v3/descriptors/autocomplete-descriptions'

    HEADERS = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    data = {
        'product_description': descripcion,
        'hscode': hs_code,
        'country_code': 'COL',
    }

    files = {
        'documents': open(ficha_path, 'rb')   # << Archivo real
    }

    # Enviar la solicitud POST
    response = requests.post(url, data=data, headers=HEADERS, files=files)


    # Comprobar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa")
        json_data = response.json()

        # Extraer los diccionarios
        applicable = json_data.get("applicable_descriptions", {})
        mandatory = json_data.get("mandatory_descriptions", {})

        # Convertir a texto tipo key=value
        applicable_descriptions = ', '.join(f'{k}={v}' for k, v in applicable.items())
        mandatory_descriptions = ', '.join(f'{k}={v}' for k, v in mandatory.items())

        print(f"::::::| {applicable_descriptions} |::::::")
        print(f":::::: {mandatory_descriptions} ::::::")

        tablaminimassql(hs_code, refproductoid, applicable_descriptions, mandatory_descriptions)

        return applicable_descriptions, mandatory_descriptions
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None, None
    
def fichatecnica_pdf(file_path):

    # URL de la API
    url = 'https://api.camtomx.com/api/v3/tariffpro/pdf?country_code=COL'

    # Encabezado de autorización
    headers = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    # Abrir el archivo y realizar la petición POST
    with open(file_path, 'rb') as f:
        files = {'file_path': f}
        response = requests.post(url, headers=headers, files=files)

    # Mostrar la respuesta
    print('Código de estado:', response.status_code)
    print('Respuesta del servidor:', response.text)



#partida arancelaria ficha tecnica