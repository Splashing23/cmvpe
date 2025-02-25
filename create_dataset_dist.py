import os
import csv
import random
import time
import requests
from io import BytesIO
from PIL import Image
import numpy as np
import torch.multiprocessing as mp

# Mapillary API token
MLY_KEY = "MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9"

# City bounding boxes
cities = {
    "Colorado_Springs": [-104.910144, 38.726291, -104.473472, 38.997499],  # 30cm/px
    "Lorain": [-82.227505, 41.399198, -82.137412, 41.485610],  # 30cm/px
    "Southington": [-72.919021, 41.551956, -72.803413, 41.698687],  # 30cm/px
    "Montpelier": [-72.700682, 44.246981, -72.556115, 44.300798],  # 30cm/px

    # # Major cities in each 30cm/px state (generally ordered from west to east)
    "Portland": [-122.836749, 45.432536, -122.472025, 45.652881], # 30cm/px OR
    "Phoenix": [-112.335284, 33.290260, -111.926052, 33.920570], # 30cm/px AZ
    "Denver": [-105.109817, 39.614431, -104.600303, 39.914246], # 30cm/px CO
    "Oklahoma City": [-97.921387, 35.291649, -97.181938, 35.730099], # 30cm/px OK
    "Des Moines": [-93.734146, 41.518050, -93.457256, 41.682130], # 30cm/px IA
    "Little Rock": [-92.472519, 34.693828, -92.262406, 34.877798], # 30cm/px AR
    "New Orleans": [-90.199402, 29.933013, -89.805378, 30.112536], # 30cm/px LA
    "Cleveland": [-81.766778, 41.290711, -81.669137, 41.499320], # 30cm/px OH
    "Miami": [-80.299499, 25.709041, -80.139198, 25.855670], # 30cm/px FL
    "Baltimore": [-76.715707, 39.272081, -76.516857, 39.400711], # 30cm/px MD
    "Dover": [-75.563591, 39.133555, -75.291482, 39.225296], # 30cm/px DE
    "Jersey City": [-74.099451, 40.673072, -74.026675, 40.745910], # 30cm/px NJ
    "Hartford": [-72.725780, 41.724926, -72.547934, 41.819974], # 30cm/px CT
    "Providence": [-71.419144, 41.812046, -71.279022, 41.876268], # 30cm/px RI
    "Boston": [-71.191157, 42.227854, -70.928462, 42.398452], # 30cm/px MA
    "Burlington": [-73.297470, 44.279179, -73.186023, 44.503181], # 30cm/px VT
    "Nashua": [-71.554596, 42.713194, -71.188291, 42.823693], # 30cm/px NH

    # # Major cities in 60cm/px states
    "Houston": [-95.462265, 29.676326, -95.262451, 29.815917], # 60cm/px
    "Seattle": [-122.459696, 47.491912, -122.224433, 47.734145], # 60cm/px
    "Washington_DC": [-77.119759, 38.791645, -76.909393, 38.995548], # most likely 60cm/px
    "Detroit": [-83.287059, 42.255948, -82.910938, 42.450230], # 60cm/px
    "San_Francisco": [-123.173825, 37.639830, -122.281780, 37.929824], # 60cm/px
}

# Constants
SAMPLES = 100000  # Number of samples per city
R_EARTH = 6378000
SIDE_LENGTH = 125  # Approximate size for aerial images
TRAIN_TEST_SPLIT = 0.8  # 80% train, 20% test

# Create dataset directories
# os.makedirs("dataset", exist_ok=True)
RIS_DIR = "/storage1/jacobsn/Active/user_h.nia/projects/cmvpe/dataset"
os.makedirs(os.path.join(RIS_DIR, "splits"), exist_ok=True)

for city in cities:
    os.makedirs(os.path.join(RIS_DIR, city, "aerial"), exist_ok=True)
    os.makedirs(os.path.join(RIS_DIR, city, "ground"), exist_ok=True)
    os.makedirs(os.path.join(RIS_DIR, "splits", city), exist_ok=True)


def process_sample(i, city, bbox, lock):
    """Processes a single sample, downloading aerial and ground images."""
    west, south, east, north = bbox

    status = "train" if i + 1 <= TRAIN_TEST_SPLIT * SAMPLES else "test"

    latitude, longitude = random.uniform(south, north), random.uniform(east, west)

    # Get latitude and longitude deltas
    lat_delta = (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / 2
    lng_delta = (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / np.cos(latitude * (np.pi / 180)) / 2

    aer_bbox = [longitude - lng_delta, latitude - lat_delta, longitude + lng_delta, latitude + lat_delta]
    gl_bbox = [longitude - (lng_delta / 2), latitude - (lat_delta / 2), longitude + (lng_delta / 2), latitude + (lat_delta / 2)]

    # Mapillary API request for ground images
    gl_data_url = "https://graph.mapillary.com/images"
    gl_fields = ["id", "geometry", "compass_angle", "computed_compass_angle", "height", "captured_at"]
    gl_params = {
        "access_token": MLY_KEY,
        "bbox": ",".join(map(str, gl_bbox)),
        "is_pano": False,
        "limit": 25,
        "fields": ",".join(gl_fields + ["thumb_original_url"]),
    }

    # NAIP aerial imagery request
    aer_data_url = "https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/exportImage"
    aer_params = {
        "bbox": ",".join(map(str, aer_bbox)),
        "bboxsr": 4326,
        "size": "512,512",
        "adjustAspectRatio": False,
        "format": "png32",
        "interpolation": "RSP_NearestNeighbor",
        "f": "image",
    }

    # Download aerial image
    # aer_bytes_response = requests.get(aer_data_url, params=aer_params)
    aer_bytes_response = requests.get(aer_data_url, params=aer_params, timeout=30)
    if aer_bytes_response.status_code == 200:
        aer_image = Image.open(BytesIO(aer_bytes_response.content))
        aer_filename = f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png"
        aer_image.convert("RGB").save(os.path.join(RIS_DIR, city, "aerial", aer_filename), "PNG")
    else:
        return

    row = [aer_filename]

    # Download ground images
    # gl_data_response = requests.get(gl_data_url, params=gl_params)
    gl_data_response = requests.get(gl_data_url, params=gl_params, timeout=30)
    if gl_data_response.status_code == 200:
        gl_data_dict = gl_data_response.json()
        for gl_data in gl_data_dict["data"]:
            gl_id = gl_data['id']
            if "thumb_original_url" not in gl_data:
                continue

            gl_url = gl_data["thumb_original_url"]
            gl_bytes_response = requests.get(gl_url)
            if gl_bytes_response.status_code == 200:
                gl_image = Image.open(BytesIO(gl_bytes_response.content))
                gl_filename = f"{gl_id}.jpg"
                gl_image.convert("RGB").save(os.path.join(RIS_DIR, city, "ground", gl_filename), "JPEG")
                row.append(gl_filename)

    # Safely write metadata with a lock
    with lock:
        with open(os.path.join(RIS_DIR, "splits", city, "samples.csv"), "a", newline='') as file:
            if len(row) >= 2:
                writer = csv.writer(file)
                writer.writerow(row)


def process_city(city, bbox):
    """Runs multiprocessing for a given city."""
    start_time = time.time()

    num_workers = mp.cpu_count() - 1  # Use all but one CPU core
    lock = mp.Manager().Lock()  # Lock to prevent concurrent file writes

    with mp.Pool(num_workers) as pool:
        pool.starmap(process_sample, [(i, city, bbox, lock) for i in range(SAMPLES)])

    print(f"Finished {city} in {time.time() - start_time:.2f} seconds.")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)  # Set multiprocessing start method
    processes = []

    for city, bbox in cities.items():
        p = mp.Process(target=process_city, args=(city, bbox))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("All cities processed.")
