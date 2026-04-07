import requests
import json

# URL de la API
url = 'https://dev-flask.camtomx.com/api/v3/tariffpro/text-and-image?country_code=COL'

# Datos que se enviarán en la solicitud POST
data = {
    "product_description": "SUV Chevrolet Onix, 4 puertas y motor 4 cilindros.",
    "img_url": "C:\\Users\\aochoa\\Downloads\\facturadeventaprueba.png"
}
params = {
        'user_identifier': 'jmiranda@abcrepecev.com'
    }
headers = {
    'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
}

# Convertir los datos a formato JSON
json_data = json.dumps(data)

# Realizar la solicitud POST
response = requests.post(url, data=json_data, headers=headers, params=params)

# Verificar la respuesta
if response.status_code == 200:
    print("Solicitud exitosa")
    print(response.json())  # Imprimir la respuesta JSON de la API
else:
    print(f"Error: {response.status_code}")
    print(response.text)
