import requests

AUTH_TOKEN = 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
description = 'Advastab TM697 2750# Totes ESTABILIZADOR TM 697'

# URL del endpoint con el parámetro `description` en la URL
url = f'https://dev-flask.camtomx.com/api/v2/pretariff/search?country_code=COL&description={description}'

HEADERS = {
    'Authorization': AUTH_TOKEN
}

# Realizar la solicitud GET
response = requests.get(url, headers=HEADERS)

# Mostrar la respuesta
print(response.status_code)
print(response.json())  # Si la respuesta es JSON