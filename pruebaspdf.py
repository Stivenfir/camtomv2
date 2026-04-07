import requests
import pandas as pd
import logging
from datetime import datetime

# Configuración del logger
logging.basicConfig(
    filename="app_log.log",  # Nombre del archivo donde se guardarán los logs
    level=logging.INFO,  # Nivel mínimo de los logs a registrar
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def extract_pdf(file_path, url, headers, params):
    try:
        logging.info("Iniciando extracción de PDF.")
        with open(file_path, 'rb') as file:
            files = {
                'file_path': file
            }
            logging.debug(f"Archivo PDF {file_path} cargado.")

            response = requests.post(url, headers=headers, params=params, files=files)
            logging.debug(f"Solicitud POST enviada a {url} con código de estado: {response.status_code}")
        
        if response.status_code == 200:
            logging.info("Solicitud exitosa.")
            # Convertir la respuesta JSON en un diccionario
            data = response.json()

            # Imprimir todo lo que sea 'invoice_data' para revisar su estructura
            if 'invoice_data' in data:
                logging.info(f"Información de 'invoice_data' recibida: {data['invoice_data']}")
            
            # Si 'invoice_data' y 'items' existen en la respuesta
            if 'invoice_data' in data and 'items' in data['invoice_data']:
                items_data = data['invoice_data']['items']
                df_items = pd.json_normalize(items_data, sep='_')
                logging.info(f"Items extraídos: {df_items.head()}")
                return df_items
            else:
                logging.error(f"Error: No se encontraron 'items' en la respuesta.")
                return response.text
        else:
            logging.error(f"Error en la respuesta: {response.status_code} - {response.text}")
            return response.text
    except Exception as e:
        logging.error(f"Error en 'extract_pdf': {e}")
        return str(e)

def partidasapartirdetexto(texto):
    try:
        url = "https://dev-flask.camtomx.com/api/v3/tariffpro/text?user_identifier=optional_user_id&country_code=COL"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2",
        }
        data = {
            "product_description": f"{texto}",
            "options": {
                "ambiguity_check": False,
            }
        }
        logging.info(f"Solicitando código HS para el texto: {texto}")
        response = requests.post(url, headers=headers, json=data)

        if response.ok:
            data = response.json()
            hscode_info = [data['hscodes_array'][0]['hscode_10digits']['code'], 
                           data['hscodes_array'][0]['hscode_10digits']['name']]
            logging.info(f"Código HS encontrado: {hscode_info}")
            return hscode_info
        else:
            logging.error(f"Error al obtener código HS: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error en 'partidasapartirdetexto': {e}")
        return None

def regulaciones(hscode):
    try:
        url = f"http://dev-flask.camtomx.com/api/v3/tariffinfo/get_tariff_details?country_code=COL&hscode={hscode}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2",
        }

        logging.info(f"Consultando regulaciones para HS Code: {hscode}")
        response = requests.get(url, headers=headers)

        if response.ok:
            data = response.json()
            minimas = data.get('minimas_colombia', [])
            minimas_descripcion = [item['minima_descripcion'] for item in minimas if item.get('obligatoria') == 1]

            acuerdos = data.get('acuerdos_colombia', [])
            acuerdos_info = [f"{acuerdo['pais_acuerdo']} - {acuerdo['norma_acuerdo']}" for acuerdo in acuerdos]
            
            requisitos = data.get('requisitos_colombia', [])

            regulaciones_info = {
                'minimas': ', '.join(minimas_descripcion),
                'acuerdos': '; '.join(acuerdos_info),
                'requisitos': str(requisitos)
            }

            logging.info(f"Regulaciones encontradas: {regulaciones_info}")
            return regulaciones_info
        else:
            logging.error(f"Error al obtener regulaciones: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error en 'regulaciones': {e}")
        return None

def main():
    url = "https://dev-flask.camtomx.com/api/v3/camtomdocs/extract-invoice?country_code=COL"
    params = {
        'user_identifier': 'jmiranda@abcrepecev.com'
    }
    headers = {
        'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
    }
    file_path = "C:\\CAMTOM\\FEVP730423.pdf"
    
    data_to_export = []

    try:
        logging.info(f"Iniciando el proceso para extraer datos de la factura: {file_path}")
        pdf_items = extract_pdf(file_path, url, headers, params)
        
        if pdf_items is not None:
            for index, row in pdf_items.iterrows():
                hscode = partidasapartirdetexto(row['description'])
                if hscode:
                    logging.info(f"Partida arancelaria: {hscode[0]} - Descripción: {hscode[1]}")
                    regulaciones_info = regulaciones(hscode[0])
                    
                    if regulaciones_info:
                        logging.info(f"Regulaciones para {hscode[0]}: {regulaciones_info}")
                        data_to_export.append({
                            "description": row['description'],
                            "hscode": hscode[0],
                            "hscode_description": hscode[1],
                            "minimas": regulaciones_info['minimas'],
                            "acuerdos": regulaciones_info['acuerdos'],
                            "requisitos_colombia": regulaciones_info['requisitos']
                        })
        
            # Convertir la lista de diccionarios a un DataFrame
            df_export = pd.DataFrame(data_to_export)
            # Guardar el DataFrame como un archivo Excel
            df_export.to_excel("resultado_factura.xlsx", index=False)
            logging.info("Datos exportados a 'resultado_factura.xlsx' exitosamente.")
        else:
            logging.error("No se pudieron extraer los items del PDF.")
    except Exception as e:
        logging.error(f"Error en el proceso principal: {e}")

if __name__ == "__main__":
    main()
