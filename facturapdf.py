import requests
import pandas as pd
import json
import numpy as np
from datetime import datetime
from io import BytesIO

URL = "https://api.camtomx.com/api/v3/tariffpro/extract-and-classify-invoice?country_code=COL"
USER_IDENTIFIER = 'jmiranda@abcrepecev.com'
AUTH_TOKEN = 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
FILE_PATH = "C:\\Users\\aochoa\\Downloads\\1-S2502-411B.pdf"

PARAMS = {
    'user_identifier': USER_IDENTIFIER,
}

HEADERS = {
    'Authorization': AUTH_TOKEN
}

def solicitud_api(file_path):
    with open(file_path, 'rb') as file:
        files = {'file_path': file}
        response = requests.post(URL, headers=HEADERS, params=PARAMS, files=files)
        return response
    
def convertir_df_json(df):
    json_array = df.to_dict(orient='records')

    def nan_null(obj):
        return {key: (None if isinstance(value, float) and np.isnan(value) else value)
                for key, value in obj.items()}

    return [nan_null(item) for item in json_array]

def procesar_factura(file_path):
    response = solicitud_api(file_path)

    if response.status_code == 200:
        print("solicitud exitosa")

        try:
            excel_file_path = 'factura_recibida.xlsx'
            datetimeee = datetime.now()
            with open(excel_file_path, 'wb') as excel_file:
                excel_file.write(response.content)
            print(f"Archivo Excel guardado como {excel_file_path}_{datetimeee}")

            excel_data = BytesIO(response.content)
            df = pd.read_excel(excel_data)
            
            json_array = convertir_df_json(df)

            with open('datafactura.json', 'w') as json_file:
                json.dump(json_array, json_file, indent=4)
        
        except Exception as e:
            print('error al leer el archivo excel: ', e)
    else:
        print(f"error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    procesar_factura(FILE_PATH)
