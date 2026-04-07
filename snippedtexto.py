import requests

def peticion_descripcion_producto(descripcion_item):
    url = "https://api.camtomx.com/api/v3/tariffpro/text?user_identifier=optional_user_id&country_code=COL"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2",
    }

    data = {
        "product_description": descripcion_item,
        "options": {
            "ambiguity_check": False,
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.ok:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
def obtener_clasificacion_arancelaria(descripcion):
    # Hacemos la petición a la API
    response = peticion_descripcion_producto(descripcion)

    # Si la respuesta no es None, procesamos la respuesta
    if response:
        print(response)
        # Verificamos si 'hscodes_array' existe y tiene elementos
        if 'hscodes_array' in response and response['hscodes_array']:
            # Si hay elementos, obtenemos el 'code' del primer elemento
            hscode_data = response['hscodes_array'][0]
            if 'hscode_10digits' in hscode_data and 'code' in hscode_data['hscode_10digits']:
                return hscode_data['hscode_10digits']['code']
        # Si no hay hscodes_array o está vacío, verificamos el mensaje de la clasificación
        elif 'summary_classification' in response:
            print("Clasificación arancelaria no disponible. Razón:", response['summary_classification'])
    
    # Si algo falla, devolvemos None
    return None