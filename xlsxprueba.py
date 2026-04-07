import time
import requests
import pandas as pd
from io import BytesIO

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


def xlsx_process(file_path):

    # URL de la API
    url = 'https://api.camtomx.com/api/v3/tariffpro/xlsx?country_code=COL&user_identifier=optional_user_id'

    HEADERS = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }

    # Abrir el archivo en modo binario
    with open(file_path, 'rb') as file:
        # Enviar la solicitud POST
        response = requests.post(url, files={'file_path': file}, headers=HEADERS)

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
            return 'no se encontró job_id'
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return response.text

def main():
    #################

    file_path = '\\\\172.16.1.7\\DocSoporte\\digitalii\\2025\\130805183254\\DS\\FACTURACOMERCIAL-S2502-411.xlsx'

    #################

    xlsx_process(file_path)

if __name__ == '__main__':
    main()