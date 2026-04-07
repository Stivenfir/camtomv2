import requests
import pandas as pd
import json
import numpy as np
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO

def job_process(job_id, HEADERS):
    print(f"Job ID obtenido: {job_id}")
    
    # Realizar la solicitud GET para obtener el estado del trabajo
    url_status = f"https://api.camtomx.com/api/v3/jobs/tariffpro/{job_id}"
    
    while True:
        # Esperar un intervalo de tiempo (por ejemplo, 45 segundos)
        time.sleep(45)  # 45 segundos de espera entre solicitudes
        
        # Hacer la solicitud GET para obtener el estado
        response_status = requests.get(url_status, headers=HEADERS)
        
        if response_status.status_code == 200:
            # Si la solicitud fue exitosa, obtener los datos JSON
            status_data = response_status.json()
            print("Estado del trabajo:", status_data)
            
            # Verificar si el estado ya no es 'in_progress'
            if status_data['status'] != 'in_progress' and status_data['status'] != 'queued':
                print(f"Trabajo completado o en otro estado: {status_data['status']}")
                
                # Hacer una solicitud GET para obtener el archivo
                response = requests.get(status_data['result'])
                
                if response.status_code == 200:
                    # Guardar el archivo Excel localmente
                    file_name = f"Factura_{job_id}.xlsx"
                    with open(file_name, 'wb') as f:
                        f.write(response.content)
                    print(f"Archivo Excel guardado como: {file_name}")

                    # Usamos BytesIO para abrir el archivo descargado como un flujo de bytes
                    excel_file = BytesIO(response.content)
                    
                    # Leemos el archivo Excel directamente en un DataFrame
                    df = pd.read_excel(excel_file)
                    
                    # Convertimos el DataFrame a JSON
                    json_data = df.to_dict(orient='records')

                    print(f"Contenido del archivo en formato JSON: {json_data}")
                    return json_data
                else:
                    print("Error al obtener el archivo.")
                break  # Salir del bucle cuando el estado no sea 'in_progress'
            else:
                print(status_data['status'])
        else:
            print(f"Error al obtener el estado del trabajo: {response_status.status_code}")
            break  # Salir si hay un error en la solicitud

def process_job_with_jobid(dataitems):
    url = "https://api.camtomx.com/api/v3/tariffpro/items-to-excel?user_identifier=optional_user_id&country_code=COL"

    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2",
    }

    data = {
        "country_code": "COL",
        "items": dataitems # [{'amount': '873.64', 'date': '', 'description': 'CR3133, Can Wireless MFG: IFM DE BRAND: IFM', 'category': '', 'hscode': '', 'product_code': '', 'quantity': '2', 'tax': '', 'unit': '', 'unit_price': '436.82'}, {'amount': '182.44', 'date': '', 'description': 'EC3133, Antena, Combined, For WLAN And Bluetooth MFG: IFM DE BRAND: IFM', 'category': '', 'hscode': '', 'product_code': '', 'quantity': '2', 'tax': '', 'unit': '', 'unit_price': '91.22'}, {'amount': '66.34', 'date': '', 'description': 'EC3146, Cable With Connector MFG: IFM PL BRAND: IFM', 'category': '', 'hscode': '', 'product_code': '', 'quantity': '2', 'tax': '', 'unit': '', 'unit_price': '33.17'}]
    }

    # Realizar la solicitud POST para obtener el job_id
    response = requests.post(url, headers=HEADERS, json=data)

    if response.ok:
        try:
            # Extraer el job_id de la respuesta JSON
            response_data = response.json()
            job_id = response_data.get('job_id')
            
            if job_id:
                print(f"Job ID obtenido: {job_id}")
                
                # Llamamos a job_process para obtener el archivo Excel cuando el trabajo esté completado
                json_data = job_process(job_id, HEADERS)
                
                return json_data
            else:
                print("No se encontró el job_id en la respuesta.")
                return 'no se encontró job_id'
        except Exception as e:
            print(f"Error al procesar la respuesta: {e}")
            return f"Error: {e}"
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return response.text

# Llamamos a la función para obtener el trabajo y procesar el archivo Excel
"""json_result = process_job_with_jobid()
print(json_result)"""
