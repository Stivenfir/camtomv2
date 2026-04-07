import requests

url = "https://api.camtomx.com/api/v3/camtomdocs/extract-invoice?country_code=COL"

params = {
    'user_identifier': 'jmiranda@abcrepecev.com'
}

headers = {
    'Authorization': 'Bearer sk_6345e9288e81f89290ac68a279f6e22c1804fb74f7c5758f8b3a0235f6af61e2'
}


file_path = 'C:\\CAMTOM\\OTROS_DOCUMENTOS-FACTUIMPO1-A2402-375A.pdf'

with open(file_path, 'rb') as file:
    files = {
        'file_path': file
    }

    response = requests.post(url, headers=headers, params=params, files=files)

if response.status_code == 200:
    print("Solicitud exitosa")
    
    print(response.json())

else:
    print(f"Error: {response.status_code}")
    print(response.text)