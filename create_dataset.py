import requests, os, random, shutil
from PIL import Image
from io import BytesIO
import numpy as np

cities = {
    "Colorado_Springs": [-104.910144, 38.726291, -104.473472, 38.997499],
    "Miami": [-80.299499, 25.709041, -80.139198, 25.855670],
    "Houston": [-95.462265, 29.676326, -95.262451, 29.815917],
    "Seattle": [-122.459696, 47.491912, -122.224433, 47.734145],
    "Washington_DC": [-77.119759, 38.791645, -76.909393, 38.995548],
    "Detroit": [-83.287059, 42.255948, -82.910938, 42.450230],
    "San_Francisco": [-123.173825, 37.639830, -122.281780, 37.929824],
}

# Mapillary API token
MLY_KEY = "MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9"

# Removes existing folder and creates new one
if os.path.exists("dataset"):
    shutil.rmtree("dataset")
os.makedirs("dataset", exist_ok=False)

# Set number of samples to retrieve from API
SAMPLES = 2

# In meters
R_EARTH = 6378000

# Side length of desired satellite image in meters (100-125 is zoom level 18)
SIDE_LENGTH = 125

TRAIN_TEST_SPLIT = 0.8

for city, bbox in cities.items():
    west, south, east, north = bbox
    os.makedirs(os.path.join("dataset", city))
    os.makedirs(os.path.join("dataset", city, "train"))
    os.makedirs(os.path.join("dataset", city, "test"))
    for i in range(SAMPLES):
        status = "train" if i + 1 <= TRAIN_TEST_SPLIT * SAMPLES else "test"

        latitude, longitude = (
            random.uniform(south, north),
            random.uniform(east, west),
        )  # Get random coordinate sample

        # Get latitude delta for bbox
        lat_delta = ((SIDE_LENGTH / 2) / R_EARTH) * (180 / np.pi)
        # Get longitude delta for bbox (dependent on coordinate latitude)
        lng_delta = (
            ((SIDE_LENGTH / 2) / R_EARTH) * (180 / np.pi) / np.cos(latitude * (np.pi / 180))
        )

        # Create folder for sample
        sample_folder = os.path.join("dataset", city, status, f"sample_{i}")
        os.makedirs(sample_folder)

        sat_bbox = [
            longitude - lng_delta,
            latitude - lat_delta,
            longitude + lng_delta,
            latitude + lat_delta,
        ]

        pano_bbox = [
            longitude - (lng_delta / 2),
            latitude - (lat_delta / 2),
            longitude + (lng_delta / 2),
            latitude + (lat_delta / 2),
        ]

        # Retrieve satellite image
        sat_data_url = "https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/exportImage"

        sat_params = {
            "bbox": ",".join(map(str, sat_bbox)),
            "bboxsr": "4326",
            "size": ",".join(map(str, [4100, 4100])),
            "f": "image",
        }

        sat_bytes_response = requests.get(sat_data_url, params=sat_params)
        if sat_bytes_response.status_code == 200:
            sat_image = Image.open(BytesIO(sat_bytes_response.content))
            output_path = os.path.join(
                sample_folder, f"satellite_{latitude}_{longitude}.png"
            )
            sat_image.convert("RGB").save(output_path, "PNG")
        else:
            print(f"NAIP API Error: {sat_bytes_response.status_code}")
            print(sat_bytes_response.text)

        # Retrieve panoramic images
        pano_data_url = "https://graph.mapillary.com/images"

        pano_params = {
            "access_token": MLY_KEY,
            "bbox": ",".join(map(str, pano_bbox)),
            "is_pano": True,
            "fields": ",".join(
                ["thumb_original_url", "computed_geometry", "computed_compass_angle", "camera_parameters"]
            ),
        }

        pano_data_response = requests.get(pano_data_url, params=pano_params)
        if pano_data_response.status_code == 200:
            pano_data = pano_data_response.json()

            for pano_data in pano_data["data"]:
                # image_id = image_data['id'] # For debugging

                # Get image url and "computed"(adjusted) coordinates
                pano_url = pano_data["thumb_original_url"]
                pano_lat, pano_lng = pano_data["computed_geometry"]["coordinates"]
                pano_ori = pano_data["computed_compass_angle"]
                # if "camera_parameters" in pano_data.keys(): print(pano_data["camera_parameters"])

                # Save image
                pano_bytes_response = requests.get(pano_url)
                if pano_bytes_response.status_code == 200:
                    pano_image = Image.open(BytesIO(pano_bytes_response.content))
                    output_path = os.path.join(
                        sample_folder, f"panorama_{pano_lat}_{pano_lng}_{pano_ori}.jpg"
                    )
                    pano_image.convert("RGB").save(output_path, "JPEG")
                else:
                    print(f"Mapillary API (Image) Error: {pano_data_response.status_code}")
                    print(pano_data_response.text)
        else:
            print(f"Mapillary API (JSON) Error: {pano_data_response.status_code}")
            print(pano_data_response.text)
