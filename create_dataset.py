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
from typing import Optional
from tqdm import tqdm


def task(
    city,
    west,
    south,
    east,
    north,
    samples_path,
    metadata_path,
    MLY_KEY,
    R_EARTH,
    SIDE_LENGTH,
):
    latitude, longitude = random.uniform(south, north), random.uniform(east, west)

    lat_delta = (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / 2
    lng_delta = (SIDE_LENGTH / R_EARTH) * (180 / np.pi) / np.cos(latitude * (np.pi / 180)) / 2
    
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
        "captured_at",
        "height",
        "sequence",

        "altitude",
        "computed_altitude",

        "compass_angle",
        "computed_compass_angle",

        "geometry",
        "computed_geometry",

        "computed_rotation",
        "camera_parameters",
    ]

    # Set the min and max number of ground-level images per sample
    GL_SAMPLES_MIN = 1
    GL_SAMPLES_MAX = 25
    gl_params = {
        "access_token": MLY_KEY,
        "bbox": ",".join(map(str, gl_bbox)),
        "is_pano": False,
        "limit": GL_SAMPLES_MAX,
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

    gl_data_dict = make_request(stop_event, url=gl_data_url, params=gl_params)
    if gl_data_dict and "data" in gl_data_dict.keys():
        gl_data_dict["data"] = [
            gl_data
            for gl_data in gl_data_dict["data"]
            if all(field in gl_data for field in gl_fields)
        ]
        if len(gl_data_dict["data"]) < GL_SAMPLES_MIN:
            # print("Response didn't return enough ground-level images for the sample")
            return False

        # before = len(gl_data_dict["data"])
        
        # diff = len(gl_data_dict["data"]) - before
        # if diff > 0:
        #     print(f"Lost {diff} ground-level images due to missing metadata fields")
    else:
        # print("Ground-level samples request returned empty")
        return False

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

    threads = []
    gl_data_map = {}

    for gl_data in gl_data_dict["data"]:
        gl_data["latitude"] = gl_data["geometry"]["coordinates"][1]
        gl_data["longitude"] = gl_data["geometry"]["coordinates"][0]
        gl_data.pop("geometry")

        gl_data["computed_latitude"] = gl_data["computed_geometry"]["coordinates"][1]
        gl_data["computed_longitude"] = gl_data["computed_geometry"]["coordinates"][0]
        gl_data.pop("computed_geometry")

        gl_data["computed_rot_x"] = gl_data["computed_rotation"][0]
        gl_data["computed_rot_y"] = gl_data["computed_rotation"][1]
        gl_data["computed_rot_z"] = gl_data["computed_rotation"][2]
        gl_data.pop("computed_rotation")

        gl_data["focal_length"] = gl_data["camera_parameters"][0]
        gl_data["radial_k1"] = gl_data["camera_parameters"][1]
        gl_data["radial_k2"] = gl_data["camera_parameters"][2]
        gl_data.pop("camera_parameters")

        gl_data_map[gl_data["id"]] = []

        threads.append(
            threading.Thread(
                target=make_request,
                kwargs={
                    "stop_event": stop_event,
                    "url": gl_data["thumb_original_url"],
                    "save_to": gl_data_map[gl_data["id"]],
                },
            )
        )
        gl_data.pop("thumb_original_url")

    for t in threads:
        t.start()

    aer_thread.join()

    if not aer_image:
        # print("make_request didn't return an aerial image")
        stop_event.set()
        return False
    
    aer_image = aer_image[0]

    aer_output_path = os.path.join(
        "dataset",
        city,
        "aerial",
        f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png",
    )
    try:
        aer_image.convert("RGB").save(aer_output_path, "PNG")
    except Exception as e:
        stop_event.set()
        return False

    row = []
    row.append(f"aerial_{aer_bbox[0]}_{aer_bbox[1]}_{aer_bbox[2]}_{aer_bbox[3]}.png")

    for t in threads:
        t.join()

    for gl_id, gl_image in gl_data_map.items():
        if gl_image:
            gl_image = gl_image[0]
        else:
            continue

        gl_output_path = os.path.join("dataset", city, "ground", f"{gl_id}.jpg")
        
        try:
            gl_image.convert("RGB").save(gl_output_path, "JPEG")
        except Exception as e:
            # print(f"GL image bytes could not be saved into jpeg with error: {e}")
            continue
        
        row.append(f"{gl_id}.jpg")

    if len(row) < 1 + GL_SAMPLES_MIN:
        files_to_remove = [aer_output_path] + [
            os.path.join("dataset", city, "ground", f"{gl_id}.jpg") 
            for gl_id in row[1:]
        ]
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        # print(f"Sample failed to meet minimum threshold of {GL_SAMPLES_MIN} ground-level image(s)")
        return False

    with lock:
        with open(samples_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)
            num_lines.value += 1

        with open(metadata_path, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=gl_data_dict["data"][0].keys())
            
            if file.tell() == 0:
                writer.writeheader()
            
            writer.writerows(gl_data_dict["data"])

        # print(f"Sample saved successfully!")
        return True # Indicate success


def make_request(
    stop_event,
    url: str,
    save_to: Optional[list] = None,
    params: Optional[dict] = None,
    retries: int = 4,
    delay: int = 1,
):
    for attempt in range(retries):
        if stop_event.is_set():
            return
        try:
            response = requests.get(url, params=params, timeout=6)
            if save_to is None:
                return response.json()
            else:
                save_to.append(Image.open(BytesIO(response.content)))
                return
        except Exception as e:
            # print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    return


def init_worker(shared_lock, shared_num_lines):
    global lock
    global num_lines
    lock = shared_lock
    num_lines = shared_num_lines


if __name__ == "__main__":
    cities = {
        # Dense ground mapillary data
        # "Colorado Springs": [-104.985348, 38.6739578, -104.665348, 38.9939578],  # 30cm/px
        # "Montpelier": [-72.7351208, 44.1002164, -72.4151208, 44.4202164],  # 30cm/px

        # # Major cities in each 30cm/px state (generally ordered from west to east) (FOCUS ON THESE)
        # "Portland": [-70.4172642, 43.4992687, -70.0972642, 43.8192687],  # 30cm/px OR
        # "Phoenix": [-112.234141, 33.2884367, -111.914141, 33.6084367],  # 30cm/px AZ
        # "Denver": [-105.144862, 39.5792364, -104.824862, 39.8992364],  # 30cm/px CO
        # "Oklahoma City": [-97.830948,35.290695,-97.124718,35.6748662],  # 30cm/px OK
        # "Des Moines": [-93.7091411,41.4796389,-93.4936911,41.6589106],  # 30cm/px IA
        # "Little Rock": [-92.5215905,34.6256657,-92.1506554,34.8218226],  # 30cm/px AR
        # "New Orleans": [-90.1399307,29.8654809,-89.6251763,30.1994687],  # 30cm/px LA
        # "Cleveland": [-81.8536772, 41.3396574, -81.5336772, 41.6596574],  # 30cm/px OH
        "Miami": [-80.35362, 25.6141728, -80.03362, 25.9341728],  # 30cm/px FL
        # "Baltimore": [-76.770759, 39.1308816, -76.450759, 39.4508816],  # 30cm/px MD
        # "Dover": [-71.0339761, 43.0381117, -70.7139761, 43.3581117],  # 30cm/px DE
        # "Jersey City": [-74.1166865,40.661622,-74.0206386,40.7689376],  # 30cm/px NJ
        # "Hartford": [-72.8508547, 41.604582, -72.5308547, 41.924582],  # 30cm/px CT
        # "Providence": [-71.5728343, 41.6639891, -71.2528343, 41.9839891],  # 30cm/px RI
        # "Boston": [-71.220511, 42.1954334, -70.900511, 42.5154334],  # 30cm/px MA
        # "Burlington": [-73.372906, 44.3161601, -73.052906, 44.6361601],  # 30cm/px VT
        # "Nashua": [-71.6277032, 42.6056251, -71.3077032, 42.9256251],  # 30cm/px NH

        # # Major cities in 60cm/px states
        # "Houston": [-95.5276974, 29.5989382, -95.2076974, 29.9189382],  # 60cm/px
        # "Seattle": [-122.490062, 47.4438321, -122.170062, 47.7638321],  # 60cm/px
        # "Washington D.C.": [-77.1197949, 38.7916303, -76.909366, 38.995968],  # most likely 60cm/px
        # "Detroit": [-83.2066403, 42.1715509, -82.8866403, 42.4915509],  # 60cm/px
        # "San Francisco": [-122.579906, 37.6190262, -122.259906, 37.9390262],  # 60cm/px
    }

    if os.path.exists("dataset"):
        shutil.rmtree("dataset")
    os.makedirs("dataset", exist_ok=True)
    os.makedirs(os.path.join("dataset", "splits"), exist_ok=True)

    # Set number of samples per city
    SAMPLES = 100

    # Mapillary API token
    MLY_KEY = "MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9"

    # In meters
    R_EARTH = 6378000

    # Side length of desired aerial image in meters (~100-125 is zoom level 18)
    SIDE_LENGTH = 125

    num_lines = mp.Value("i", 0)

    total_target_samples = len(cities) * SAMPLES
    total_successful_samples = 0

    with tqdm(total=total_target_samples, desc="Dataset progress", unit="successful samples") as pbar:
        for city, bbox in cities.items():
            tqdm.write(f"Processing {city}...")

            west, south, east, north = bbox
            os.makedirs(os.path.join("dataset", city), exist_ok=True)
            os.makedirs(os.path.join("dataset", city, "aerial"), exist_ok=True)
            os.makedirs(os.path.join("dataset", city, "ground"), exist_ok=True)
            os.makedirs(os.path.join("dataset", "splits", city), exist_ok=True)

            samples_path = os.path.join("dataset", "splits", city, "samples.csv")
            metadata_path = os.path.join("dataset", "splits", city, "ground_metadata.csv")

            lock = mp.Lock()

            successful_samples = 0
            active_tasks = []

            NUM_PROCESSES = 12
            
            with mp.Pool(processes=NUM_PROCESSES, initializer=init_worker, initargs=(lock, num_lines)) as pool:
                while successful_samples < SAMPLES:
                    # Submit new tasks if we have room
                    while len(active_tasks) < NUM_PROCESSES + 2 and successful_samples + len(active_tasks) < SAMPLES:
                        task_args = (
                            city, west, south, east, north, samples_path, metadata_path,
                            MLY_KEY, R_EARTH, SIDE_LENGTH,
                        )
                        async_result = pool.apply_async(task, task_args)
                        active_tasks.append(async_result)
                    
                    # Check for completed tasks
                    completed_tasks = []
                    for async_result in active_tasks:
                        if async_result.ready():
                            result = async_result.get()
                            if result is True:
                                successful_samples += 1
                                total_successful_samples += 1
                                pbar.update(1)  # Update overall progress
                            completed_tasks.append(async_result)
                    
                    # Remove completed tasks
                    for completed in completed_tasks:
                        active_tasks.remove(completed)
                    
            # Remove duplicate metadata rows
            if os.path.exists(metadata_path):
                with open(metadata_path, mode="r+", newline="") as file:
                    reader = list(csv.reader(file))
                    saved = set(tuple(row) for row in reader[1:])
                    file.seek(0)
                    
                    writer = csv.writer(file)
                    writer.writerow(reader[0])
                    writer.writerows(saved)
                    file.truncate()

            tqdm.write(f"Completed {city}!")
    print("Dataset complete!")