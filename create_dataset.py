import requests, os, random, shutil
from PIL import Image
from io import BytesIO

west, south, east, north = -95.462265, 29.676326, -95.262451, 29.815917

mly_key = 'MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9'

if os.path.exists('dataset'):
    shutil.rmtree('dataset')
os.makedirs('dataset', exist_ok=True)

SAMPLES = 1
ZOOM_LEVEL_18 = 0.0008 # approx
ZOOM_LEVEL = 0.0003
ZOOM_LEVEL_19 = 0.00004 # approx
ZOOM_LEVEL_20 = 0.00002 # approx

for i in range(SAMPLES):
    coordinate = (random.uniform(east, west), random.uniform(south, north))
    
    sample_folder = os.path.join("dataset", f"sample_{coordinate[0]}_{coordinate[1]}")
    os.makedirs(sample_folder)

    bbox_str = f'{coordinate[0] - ZOOM_LEVEL},{coordinate[1] - ZOOM_LEVEL},{coordinate[0] + ZOOM_LEVEL},{coordinate[1] + ZOOM_LEVEL}'

    images_data_url = f'https://graph.mapillary.com/images?access_token={mly_key}&bbox={bbox_str}&is_pano=true&fields=thumb_original_url,computed_geometry'

    images_data_response = requests.get(images_data_url)
    if images_data_response.status_code == 200:
        images_data = images_data_response.json()

        for image_data in images_data['data']:
            image_url = image_data['thumb_original_url']
            image_id = image_data['id']
            image_lat, image_lng = image_data['computed_geometry']['coordinates']
            
            image_bytes_response = requests.get(image_url)
            image = Image.open(BytesIO(image_bytes_response.content))
            output_path = os.path.join(sample_folder, f'panorama_{image_lat}_{image_lng}.jpeg')
            image.convert('RGB').save(output_path, 'JPEG')
