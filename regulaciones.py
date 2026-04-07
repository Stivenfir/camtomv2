import requests

url = "https://api.camtomx.com/api/v3/tariffinfo/get_tariff_details"

params = {
    "country_code": "COL",
    "hscode": "6109100000"
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2",
}

# Enviamos una petición POST sin body
response = requests.get(url, params=params, headers=headers)

# Mostrar el resultado
print("Status code:", response.status_code)
print("Respuesta:", response.text)
