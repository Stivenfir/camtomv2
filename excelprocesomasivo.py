import pandas as pd
import requests
from xlsxprueba import xlsx_process

def dividir_excel(file_path, filas_por_archivo=10):
    # Leer el archivo .xls
    df = pd.read_excel(file_path, engine='xlrd')  # Usamos 'xlrd' para leer .xls
    
    # Dividir el DataFrame en partes
    num_partes = len(df) // filas_por_archivo + 1
    archivos = []
    
    for i in range(num_partes):
        inicio = i * filas_por_archivo
        fin = (i + 1) * filas_por_archivo
        df_parte = df.iloc[inicio:fin]
        archivo_parte = f'parte_{i + 1}.xlsx'  # Guardamos como archivo .xlsx
        df_parte.to_excel(archivo_parte, index=False, engine='openpyxl')  # Usamos 'openpyxl' para guardar como .xlsx
        archivos.append(archivo_parte)
    
    return archivos

def enviar_a_api(archivo):
    url_api = 'https://api.tu-servidor.com/endpoint'  # Aquí debes poner la URL de la API
    archivos = {'file': open(archivo, 'rb')}
    response = requests.post(url_api, files=archivos)
    
    if response.status_code == 200:
        print(f"Archivo {archivo} enviado correctamente.")
        return response.json()  # Suponiendo que la API devuelve una respuesta JSON
    else:
        print(f"Error al enviar el archivo {archivo}.")
        return None
    
# Función para unir los resultados en un archivo Excel final
def unir_resultados(resultados, archivo_final='resultado_unido.xlsx'):
    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_excel(archivo_final, index=False, engine='openpyxl')
    print(f"Archivo final guardado como {archivo_final}")

# Función principal que coordina todo el flujo
def procesar_archivo():
    # Dividir el archivo original en partes más pequeñas
    archivos_divididos = dividir_excel('BASE DE DATOS PARTIDAS copia.xls', filas_por_archivo=3)

    # Lista para almacenar los resultados
    resultados = []

    # Enviar los archivos divididos a la API y recolectar los resultados
    for archivo in archivos_divididos:
        print(f"Procesando archivo: {archivo}")
        resultado = xlsx_process(archivo)  # Procesar archivo con la API

        if resultado and isinstance(resultado, list):  # Verificar que sea una lista
            # Filtrar solo los resultados válidos (no vacíos)
            resultado_filtrado = [item for item in resultado if item]
            if resultado_filtrado:
                print(f"Resultado procesado para {archivo}: {resultado_filtrado}")
                resultados.extend(resultado_filtrado)  # Agregar los resultados al conjunto total
            else:
                print(f"Archivo {archivo} no produjo resultados válidos.")
        else:
            print(f"Resultado no válido para el archivo {archivo}.")
    
    # Unir todos los resultados en un solo archivo Excel
    unir_resultados(resultados)

# Ejecutar el flujo de trabajo
procesar_archivo()