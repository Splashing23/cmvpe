import os
import csv
# import zlib
# import json
import random
import shutil
from io import BytesIO
import time

import numpy as np
import requests
from PIL import Image

cities = {
    # Dense ground mapillary data
    # "Colorado_Springs": [-104.910144, 38.726291, -104.473472, 38.997499],  # 30cm/px
    # "Lorain": [-82.227505, 41.399198, -82.137412, 41.485610],  # 30cm/px
    # "Southington": [-72.919021, 41.551956, -72.803413, 41.698687],  # 30cm/px
    # "Montpelier": [-72.700682, 44.246981, -72.556115, 44.300798],  # 30cm/px

    # # Major cities in each 30cm/px state (generally ordered from west to east)
    # "Portland": [-122.836749, 45.432536, -122.472025, 45.652881], # 30cm/px OR
    # "Phoenix": [-112.335284, 33.290260, -111.926052, 33.920570], # 30cm/px AZ
    # "Denver": [-105.109817, 39.614431, -104.600303, 39.914246], # 30cm/px CO
    # "Oklahoma City": [-97.921387, 35.291649, -97.181938, 35.730099], # 30cm/px OK
    # "Des Moines": [-93.734146, 41.518050, -93.457256, 41.682130], # 30cm/px IA
    # "Little Rock": [-92.472519, 34.693828, -92.262406, 34.877798], # 30cm/px AR
    # "New Orleans": [-90.199402, 29.933013, -89.805378, 30.112536], # 30cm/px LA
    # "Cleveland": [-81.766778, 41.290711, -81.669137, 41.499320], # 30cm/px OH
    # "Miami": [-80.299499, 25.709041, -80.139198, 25.855670], # 30cm/px FL
    # "Baltimore": [-76.715707, 39.272081, -76.516857, 39.400711], # 30cm/px MD
    # "Dover": [-75.563591, 39.133555, -75.291482, 39.225296], # 30cm/px DE
    # "Jersey City": [-74.099451, 40.673072, -74.026675, 40.745910], # 30cm/px NJ
    # "Hartford": [-72.725780, 41.724926, -72.547934, 41.819974], # 30cm/px CT
    # "Providence": [-71.419144, 41.812046, -71.279022, 41.876268], # 30cm/px RI
    "Boston": [-71.191157, 42.227854, -70.928462, 42.398452], # 30cm/px MA
    # "Burlington": [-73.297470, 44.279179, -73.186023, 44.503181], # 30cm/px VT
    # "Nashua": [-71.554596, 42.713194, -71.188291, 42.823693], # 30cm/px NH

    # # Major cities in 60cm/px states
    # "Houston": [-95.462265, 29.676326, -95.262451, 29.815917], # 60cm/px
    # "Seattle": [-122.459696, 47.491912, -122.224433, 47.734145], # 60cm/px
    # "Washington_DC": [-77.119759, 38.791645, -76.909393, 38.995548], # most likely 60cm/px
    # "Detroit": [-83.287059, 42.255948, -82.910938, 42.450230], # 60cm/px
    # "San_Francisco": [-123.173825, 37.639830, -122.281780, 37.929824], # 60cm/px
}

# Mapillary API token
MLY_KEY = "MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9"

# Removes existing folder and creates new one
if os.path.exists("dataset"):
    shutil.rmtree("dataset")
os.makedirs("dataset", exist_ok=True)
os.makedirs(os.path.join("dataset", "splits"), exist_ok=True)

# Set number of samples per city
SAMPLES = 100000

# In meters
R_EARTH = 6378000

# Side length of desired aerial image in meters (~100-125 is zoom level 18)
SIDE_LENGTH = 125

TRAIN_TEST_SPLIT = 0.8

for city, bbox in cities.items():
    west, south, east, north = bbox
    os.makedirs(os.path.join("dataset", city), exist_ok=True)
    os.makedirs(os.path.join("dataset", city, "aerial"), exist_ok=True)
    os.makedirs(os.path.join("dataset", city, "ground"), exist_ok=True)
    os.makedirs(os.path.join("dataset", "splits", city), exist_ok=True)

    start_time = time.time()
    num_lines = 0
    for i in range(SAMPLES):
        status = "train" if i + 1 <= TRAIN_TEST_SPLIT * SAMPLES else "test"

        latitude, longitude = (
            random.uniform(south, north),
            random.uniform(east, west),
        )  # Get uniform random coordinate sample

        # Get latitude delta for bbox
        lat_delta = (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / 2
        # Get longitude delta for bbox (dependent on coordinate latitude)
        lng_delta = (
            (SIDE_LENGTH / R_EARTH)
            * (180 / np.pi)
            / np.cos(latitude * (np.pi / 180))
            / 2
        )

        aer_bbox = [
            longitude - lng_delta,
            latitude - lat_delta,
            longitude + lng_delta,
            latitude + lat_delta,
        ]

        gl_bbox = [
            longitude - (lng_delta / 2),
            latitude - (lat_delta / 2),
            longitude + (lng_delta / 2),
            latitude + (lat_delta / 2),
        ]


        gl_data_url = "https://graph.mapillary.com/images"

        gl_fields = [
            "id",
            "geometry"
            "computed_geometry",
            "compass_angle",
            "computed_compass_angle",
            "computed_rotation",
            "computed_altitude",
            "height",
            "captured_at",
            "camera_parameters",
            "camera_type",
            "sequence",
            "make",
            "model",
        ]

        limit = 25
        gl_params = {
            "access_token": MLY_KEY,
            "bbox": ",".join(map(str, gl_bbox)),
            "is_pano": False,
            "limit": limit,
            "fields": ",".join(gl_fields + ["thumb_original_url"]),
        }

        aer_data_url = "https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/exportImage"

        aer_params = {
            "bbox": ",".join(map(str, aer_bbox)),
            "bboxsr": 4326,
            "size": ",".join(map(str, [512, 512])),
            "adjustAspectRatio": False,
            "format": "png32",
            "interpolation": "RSP_NearestNeighbor",
            "f": "image",
        }

        gl_data_response = requests.get(gl_data_url, params=gl_params)
        if gl_data_response.status_code == 200:
            gl_data_dict = gl_data_response.json()
            if len(gl_data_dict["data"]) >= 1:
                    
                try:
                    # Retrieve aerial image
                    aer_bytes_response = requests.get(aer_data_url, params=aer_params)
                    if aer_bytes_response.status_code == 200:
                        aer_image = Image.open(BytesIO(aer_bytes_response.content))
                        output_path = os.path.join(
                            "dataset", city, "aerial", f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png"
                        )
                        aer_image.convert("RGB").save(output_path, "PNG")
                    else:
                        print(f"NAIP API Error: {aer_bytes_response.status_code}")
                        print(aer_bytes_response.text)
                        continue

                    row = []
                    row.append(f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png")
                except Exception as e:
                    print(e)
                    continue


                # Retrieve ground images
                for gl_data in gl_data_dict["data"]:
                    gl_id = gl_data['id']

                    # Get image url and 'computed'(adjusted) coordinates
                    if "thumb_original_url" not in gl_data.keys():
                        continue
                    gl_url = gl_data["thumb_original_url"]
                    # gl_lat, gl_lng = gl_data["computed_geometry"]["coordinates"]
                    # gl_ori = gl_data["computed_compass_angle"]
                    # gl_rot = gl_data["computed_rotation"]
                    # gl_type = gl_data["camera_type"]
                    # print(gl_rot)
                    # print(gl_data["sfm_cluster"])

                    # decompressed_data = zlib.decompress(requests.get(gl_data["sfm_cluster"]["url"]).content)
                    # json_data = json.loads(decompressed_data)
                    
                    # output_json_path = 'pc.json'
                    # with open(output_json_path, 'w') as json_file:
                    #     json.dump(json_data, json_file, indent=4)

                    try:
                        # Save image
                        gl_bytes_response = requests.get(gl_url)
                        if gl_bytes_response.status_code == 200:
                            gl_image = Image.open(BytesIO(gl_bytes_response.content))
                            output_path = os.path.join(
                                "dataset",
                                city,
                                "ground",
                                f"{gl_id}.jpg",
                            )
                            gl_image.convert("RGB").save(output_path, "JPEG")

                            row.append(f"{gl_id}.jpg")
                        else:
                            print(
                                f"Mapillary API (Image) Error: {gl_data_response.status_code}"
                            )
                            print(gl_data_response.text)

                        gl_data.pop("thumb_original_url", None)
                    except Exception as e:
                        gl_data.pop("thumb_original_url", None)
                        print(e)
                        continue

                with open(os.path.join("dataset", "splits", city, f"samples.csv"), "a", newline='') as file: # {status}_
                    if len(row) >= 2:
                        writer = csv.writer(file)
                        writer.writerow(row)
                        num_lines += 1

                with open(os.path.join("dataset", "splits", city, f"ground_metadata.csv"), "a", newline='') as file: # {status}_
                    writer = csv.DictWriter(file, fieldnames=gl_fields)
                    writer.writeheader()
                    writer.writerows(gl_data_dict["data"])
        else:
            print(f"Mapillary API (JSON) Error: {gl_data_response.status_code}")
            print(gl_data_response.text)
        
        if (i + 1) % 2 == 0:
            print(f"Avg time per sample is {((time.time() - start_time) / num_lines):.4f} seconds")