import requests

# URL of the API endpoint
url = "https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/exportImage"

# Optional: Parameters for the request
params = {
    "bbox": "-118.2437,34.0522,-118.1437,34.1522",
    "bboxsr": "4326",
    "size": ",".join(map(str, [4100, 4100])),
    "f": "json"
}

response = requests.get(url, params=params)

# Checking the status code
if response.status_code == 200:
    # Successful request
    data = response.json()  # Parse the JSON response
    print(data)
else:
    print(f"Error: {response.status_code}")
    print(response.text)