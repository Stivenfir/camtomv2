import requests
import json

url = "https://api.camtomx.com/api/v3/tariffpro/pdf"

params = {
    'user_identifier': 'jmiranda@abcrepecev.com',
    'country_code': 'COL'
}

headers = {
    'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
}

file_path = 'C:\\Users\\aochoa\\Downloads\\Ficha tecnica Motorola Moto G75 5G XT2437-2 NFC - Mega.pdf'

with open(file_path, 'rb') as file:
    files = {
        'file_path': file
    }

    response = requests.post(url, headers=headers, params=params, files=files)

if response.status_code == 200:
    print("✅ Solicitud exitosa")

    data = response.json()

    # Guardar como archivo JSON bien formateado
    output_file = 'resultado_ficha_tecnica.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"📁 Archivo JSON generado exitosamente: {output_file}")

else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
