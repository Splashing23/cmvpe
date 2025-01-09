import requests, os, random, shutil
from PIL import Image
from io import BytesIO
import math

# Bounding box of entire city (currently Houston)
west, south, east, north = -95.462265, 29.676326, -95.262451, 29.815917

# Mapillary API token
MLY_KEY = 'MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9'

# Removes existing folder and creates new one
if os.path.exists('dataset'):
    shutil.rmtree('dataset')
os.makedirs('dataset', exist_ok=False)

# Set number of samples to retrieve from API (does NOT get random sample; used for debugging)
SAMPLES = 1

# In meters
R_EARTH = 6378000 

# Area of desired satellite image in square meters (100 is slightly larger than zoom level 18)
AREA = 100 

for i in range(SAMPLES):
    latitude, longitude= random.uniform(south, north), random.uniform(east, west) # Get random coordinate sample

    # Get lattitude delta for bbox
    lat_delta  = ((AREA / 2) / R_EARTH) * (180 / math.pi)
    # Get longitude delta for bbox (dependent on coordinate lattitude)
    lng_delta = ((AREA / 2) / R_EARTH) * (180 / math.pi) / math.cos(latitude * (math.pi / 180))
    
    # Create folder for sample
    sample_folder = os.path.join("dataset", f"sample_{latitude}_{longitude}")
    os.makedirs(sample_folder)

    bbox_str = f'{longitude - lng_delta},{latitude - lat_delta},{longitude + lng_delta},{latitude + lat_delta}'

    images_data_url = f'https://graph.mapillary.com/images?access_token={MLY_KEY}&bbox={bbox_str}&is_pano=true&fields=thumb_original_url,computed_geometry'

    images_data_response = requests.get(images_data_url)
    if images_data_response.status_code == 200:
        images_data = images_data_response.json()

        for image_data in images_data['data']:
            # image_id = image_data['id'] # For debugging

            # Get image url and "computed"(adjusted) coordinates
            image_url = image_data['thumb_original_url']
            image_lat, image_lng = image_data['computed_geometry']['coordinates']
            
            # Save image
            image_bytes_response = requests.get(image_url)
            image = Image.open(BytesIO(image_bytes_response.content))
            output_path = os.path.join(sample_folder, f'panorama_{image_lat}_{image_lng}.jpeg')
            image.convert('RGB').save(output_path, 'JPEG')
