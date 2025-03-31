import csv
import multiprocessing as mp
import os
import random
import shutil
import threading
import time
from io import BytesIO

import numpy as np
import requests
from PIL import Image


def task(
    city,
    west,
    south,
    east,
    north,
    start_time,
    samples_path,
    metadata_path,
    MLY_KEY,
    R_EARTH,
    SIDE_LENGTH,
):
    latitude, longitude = (
        random.uniform(south, north),
        random.uniform(east, west),
    )  # Get uniform random coordinate sample

    # Get latitude delta for bbox
    lat_delta = (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / 2
    # Get longitude delta for bbox (dependent on coordinate latitude)
    lng_delta = (
        (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / np.cos(latitude * (np.pi / 180)) / 2
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
        "thumb_original_url",
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

    GL_SAMPLES_LIMIT = 25
    gl_params = {
        "access_token": MLY_KEY,
        "bbox": ",".join(map(str, gl_bbox)),
        "is_pano": False,
        "limit": GL_SAMPLES_LIMIT,
        "fields": ",".join(gl_fields),
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

    stop_event = threading.Event()

    # Retrieve ground-level data
    gl_data_dict = make_request(stop_event, url=gl_data_url, params=gl_params)
    if gl_data_dict:
        gl_data_dict["data"] = [
            gl_data
            for gl_data in gl_data_dict["data"]
            if "thumb_original_url" in gl_data
        ]
        if not gl_data_dict["data"]:
            return
    else:
        return

    # Retrieve aerial image
    aer_image = []
    aer_thread = threading.Thread(
        target=make_request,
        kwargs={
            "stop_event": stop_event,
            "url": aer_data_url,
            "save_to": aer_image,
            "params": aer_params,
        },
    )
    aer_thread.start()

    # Retrieve ground images
    gl_images = []
    gl_ids = []
    threads = []
    for gl_data in gl_data_dict["data"]:
        gl_ids.append(gl_data["id"])
        threads.append(
            threading.Thread(
                target=make_request,
                kwargs={
                    "stop_event": stop_event,
                    "url": gl_data["thumb_original_url"],
                    "save_to": gl_images,
                },
            )
        )
        # gl_data.pop("thumb_original_url", None) # to remove url from metadata

    for t in threads:
        t.start()

    aer_thread.join()
    aer_image = aer_image[0]
    if not aer_image:
        stop_event.set()
        return

    aer_output_path = os.path.join(
        "dataset",
        city,
        "aerial",
        f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png",
    )
    try:
        aer_image.convert("RGB").save(aer_output_path, "PNG")
    except Exception as e:
        print(f"Aerial image bytes could not be saved into png with error: {e}")
        return

    row = []
    row.append(f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png")

    for t in threads:
        t.join()

    for gl_id, gl_image in zip(gl_ids, gl_images):
        if gl_image is None:
            return

        gl_output_path = os.path.join("dataset", city, "ground", f"{gl_id}.jpg")
        try:
            gl_image.convert("RGB").save(gl_output_path, "JPEG")
        except Exception as e:
            print(f"GL image bytes could not be saved into jpeg with error: {e}")
            return

        row.append(f"{gl_id}.jpg")

    if len(row) <= 1:
        return

    with lock:
        with open(samples_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)
            num_lines.value += 1

        if write_header.value:
            with open(metadata_path, mode="w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=gl_fields)
                writer.writeheader()
            write_header.value = False

        with open(metadata_path, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=gl_fields)
            writer.writerows(gl_data_dict["data"])

        print(
            f"Avg time per sample is {((time.time() - start_time) / num_lines.value):.4f} seconds"
        )

def make_request(
    stop_event,
    url: str,
    save_to: list = None,
    params: dict = None,
    retries: int = 4,
    delay: int = 1,
):
    for attempt in range(retries):
        if stop_event.is_set():
            return
        try:
            response = requests.get(url, params=params, timeout=5)
            if save_to is None:
                return response.json()
            else:
                save_to.append(Image.open(BytesIO(response.content)))
                return
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    if save_to:
        save_to.append(None)
    else:
        return None

def init_worker(shared_lock, shared_write_header, shared_num_lines):
    global lock
    global write_header
    global num_lines
    lock = shared_lock
    write_header = shared_write_header
    num_lines = shared_num_lines


if __name__ == "__main__":
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
        "Boston": [-71.191157, 42.227854, -70.928462, 42.398452],  # 30cm/px MA
        # "Burlington": [-73.297470, 44.279179, -73.186023, 44.503181], # 30cm/px VT
        # "Nashua": [-71.554596, 42.713194, -71.188291, 42.823693], # 30cm/px NH
        # # Major cities in 60cm/px states
        # "Houston": [-95.462265, 29.676326, -95.262451, 29.815917], # 60cm/px
        # "Seattle": [-122.459696, 47.491912, -122.224433, 47.734145], # 60cm/px
        # "Washington_DC": [-77.119759, 38.791645, -76.909393, 38.995548], # most likely 60cm/px
        # "Detroit": [-83.287059, 42.255948, -82.910938, 42.450230], # 60cm/px
        # "San_Francisco": [-123.173825, 37.639830, -122.281780, 37.929824], # 60cm/px
    }

    # Removes existing folder and creates new one
    if os.path.exists("dataset"):
        shutil.rmtree("dataset")
    os.makedirs("dataset", exist_ok=True)
    os.makedirs(os.path.join("dataset", "splits"), exist_ok=True)

    # Set number of samples per city
    SAMPLES = 25000

    # Mapillary API token
    MLY_KEY = "MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9"

    # In meters
    R_EARTH = 6378000

    # Side length of desired aerial image in meters (~100-125 is zoom level 18)
    SIDE_LENGTH = 125

    # TRAIN_TEST_SPLIT = 0.8
    # status = "train" if i + 1 <= TRAIN_TEST_SPLIT * SAMPLES else "test"

    start_time = time.time()
    num_lines = mp.Value("i", 0)

    for city, bbox in cities.items():
        west, south, east, north = bbox
        os.makedirs(os.path.join("dataset", city), exist_ok=True)
        os.makedirs(os.path.join("dataset", city, "aerial"), exist_ok=True)
        os.makedirs(os.path.join("dataset", city, "ground"), exist_ok=True)
        os.makedirs(os.path.join("dataset", "splits", city), exist_ok=True)

        samples_path = os.path.join("dataset", "splits", city, "samples.csv")
        metadata_path = os.path.join("dataset", "splits", city, "ground_metadata.csv")

        write_header = mp.Value("b", True)
        lock = mp.Lock()

        args = (
            (
                city,
                west,
                south,
                east,
                north,
                start_time,
                samples_path,
                metadata_path,
                MLY_KEY,
                R_EARTH,
                SIDE_LENGTH,
            )
            for _ in range(SAMPLES)
        )

        with mp.Pool(
            processes=10,
            initializer=init_worker,
            initargs=(lock, write_header, num_lines),
        ) as pool:
            pool.starmap(task, args)
