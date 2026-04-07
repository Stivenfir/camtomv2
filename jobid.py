import requests
import pandas as pd
import json
import numpy as np
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO

URL = "https://api.camtomx.com/api/v3/tariffpro/extract-and-classify-invoice?country_code=COL"
USER_IDENTIFIER = 'jmiranda@abcrepecev.com'
AUTH_TOKEN = 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'

URLTEXTO = "https://api.camtomx.com/api/v3/tariffpro/text?&country_code=COL"

PARAMS = {
    'user_identifier': USER_IDENTIFIER,
}

HEADERS = {
    'Authorization': AUTH_TOKEN
}

def solicitud_texto(descripcion):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2",
    }

    data = {
        "product_description": descripcion,
        "options": {
            "ambiguity_check": False,
        }
    }

    response = requests.post(URLTEXTO, headers=headers, json=data)
    return response

def solicitud_api(file_path):
    with open(file_path, 'rb') as file:
        files = {'file_path': file}
        response = requests.post(URL, headers=HEADERS, params=PARAMS, files=files)
        print(response)
        return response
    
def convertir_df_json(df):
    json_array = df.to_dict(orient='records')

    def nan_null(obj):
        return {key: (None if isinstance(value, float) and np.isnan(value) else value)
                for key, value in obj.items()}

    return [nan_null(item) for item in json_array]

def job_process(job_id, HEADERS, file_path):
    print(f"Job ID obtenido: {job_id}")
            
    # Realizar la solicitud GET para obtener el estado del trabajo
    url_status = f"https://api.camtomx.com/api/v3/jobs/tariffpro/{job_id}"
    
    while True:
        # Esperar un intervalo de tiempo (por ejemplo, 30 segundos)
        time.sleep(20)  # 45 segundos de espera entre solicitudes
        
        # Hacer la solicitud GET para obtener el estado
        response_status = requests.get(url_status, headers=HEADERS)
        
        if response_status.status_code == 200:
            # Si la solicitud fue exitosa, obtener los datos JSON
            status_data = response_status.json()
            print("Estado del trabajo:", status_data)
            
            # Verificar si el estado ya no es 'in_progress'
            if status_data['status'] != 'in_progress' and status_data['status'] != 'queued':
                print(f"Trabajo completado o en otro estado: {status_data['status']}")
                response = requests.get(status_data['result'])

                if response.status_code == 200:

                    file_path = Path(file_path)
                    file_name = file_path.name
                    excel_name = f"Factura_{file_name.replace('.pdf', '.xlsx')}"
                    
                    # Guardar el archivo Excel localmente
                    with open(excel_name, 'wb') as f:
                        f.write(response.content)
                    print(f"Archivo Excel guardado como: {excel_name}")

                    # Usamos BytesIO para abrir el archivo descargado como un flujo de bytes
                    excel_file = BytesIO(response.content)
                    
                    # Leemos el archivo Excel directamente en un DataFrame
                    df = pd.read_excel(excel_file)
                    
                    # Convertimos el DataFrame a JSON
                    json_data = df.to_dict(orient='records')

                    print(f"Contenido del archivo en formato JSON: {json_data}")
                    return response
                else:
                    print("error...")
                break  # Salir del bucle cuando el estado no sea 'in_progress'
            else:
                print(status_data['status'])
        else:
            print(f"Error al obtener el estado del trabajo: {response_status.status_code}")
            break  # Salir si hay un error en la solicitud

def procesar_factura(file_path):
    response = solicitud_api(file_path)

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
            json_data = job_process(job_id, HEADERS, file_path)
            return json_data
        else:
            print("No se encontró el job_id en la respuesta.")
            return 'no se encontró job_id'
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return response.text
    
def procesar_texto(descripcion, file_path):
    response = solicitud_texto(descripcion)

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
            json_data = job_process(job_id, HEADERS, file_path)
            return json_data
        else:
            print("No se encontró el job_id en la respuesta.")
            return 'no se encontró job_id'
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return response.text

if __name__ == "__main__":
    FILE_PATH = "C:\\Users\\aochoa\\Downloads\\1-S2502-411A.pdf"
    procesar_factura(FILE_PATH)
    #procesar_texto('SWITCH RUGGEDCOM RX1524 ROBUST.')