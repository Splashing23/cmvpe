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
from typing import Optional, List, Tuple
from tqdm import tqdm


def generate_grid_samples(west: float, south: float, east: float, north: float, 
                         side_length: float, overlap_ratio: float = 0.5) -> List[Tuple[float, float]]:
    """
    Generate grid-based sample points with specified overlap.
    
    Args:
        west, south, east, north: Bounding box coordinates
        side_length: Side length of each sample area in meters
        overlap_ratio: Overlap ratio between neighboring samples (0.0 to 1.0)
    
    Returns:
        List of (latitude, longitude) tuples for sample centers
    """
    # Convert side length from meters to degrees
    # Approximate conversion: 1 degree latitude ≈ 111,000 meters
    # 1 degree longitude ≈ 111,000 * cos(latitude) meters
    center_lat = (south + north) / 2
    center_lng = (west + east) / 2
    
    # Calculate step size to achieve desired overlap
    # If samples have side_length and overlap_ratio, then step = side_length * (1 - overlap_ratio)
    step_size_meters = side_length * (1 - overlap_ratio)
    
    # Convert step size to degrees
    lat_step = step_size_meters / 111000  # 1 degree latitude ≈ 111,000 meters
    lng_step = step_size_meters / (111000 * np.cos(np.radians(center_lat)))  # Adjust for longitude
    
    # Generate grid points
    samples = []
    current_lat = south
    while current_lat <= north:
        current_lng = west
        while current_lng <= east:
            samples.append((current_lat, current_lng))
            current_lng += lng_step
        current_lat += lat_step
    
    return samples


def count_grid_samples(west: float, south: float, east: float, north: float, 
                       side_length: float, overlap_ratio: float = 0.5) -> int:
    """
    Count how many grid sample points would be generated for the given bbox and parameters
    without materializing all coordinates.
    """
    center_lat = (south + north) / 2
    step_size_meters = side_length * (1 - overlap_ratio)
    lat_step = step_size_meters / 111000
    lng_step = step_size_meters / (111000 * np.cos(np.radians(center_lat)))

    if lat_step <= 0 or lng_step <= 0:
        return 0

    n_lat = int(np.floor((north - south) / lat_step)) + 1
    n_lng = int(np.floor((east - west) / lng_step)) + 1
    return max(0, n_lat) * max(0, n_lng)


def task(
    city,
    latitude,
    longitude,
    samples_path,
    metadata_path,
    MLY_KEY,
    R_EARTH,
    SIDE_LENGTH,
):
    # Use the provided latitude and longitude instead of random sampling
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
            return None
        try:
            response = requests.get(url, params=params, timeout=6)
            if save_to is None:
                return response.json()
            else:
                save_to.append(Image.open(BytesIO(response.content)))
                return None
        except Exception as e:
            # print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    return None


def init_worker(shared_lock, shared_num_lines):
    global lock
    global num_lines
    lock = shared_lock
    num_lines = shared_num_lines


def main():
    # Sourced from OSM data:https://www.geoapify.com/download-all-the-cities-towns-villages/ - more specifically: https://www.geoapify.com/data-share/localities/us.zip
    cities = {
        # Dense ground mapillary data
        # "Colorado Springs": [-104.985348, 38.6739578, -104.665348, 38.9939578],  # 30cm/px
        # "Montpelier": [-72.7351208, 44.1002164, -72.4151208, 44.4202164],  # 30cm/px

        # # Major cities in each 30cm/px state (generally ordered from west to east) (FOCUS ON THESE)
        # "Portland": [-70.4172642, 43.4992687, -70.0972642, 43.8192687],  # 30cm/px OR
        # "Phoenix": [-112.234141, 33.2884367, -111.914141, 33.6084367],  # 30cm/px AZ
        # "Denver": [-105.144862, 39.5792364, -104.824862, 39.8992364],  # 30cm/px CO
        # "Oklahoma City": [-97.830948,35.290695,-97.124718,35.6748662],  # 30cm/px OK
        # "Tulsa": [-96.1527516,35.9963122,-95.8327516,36.3163122] # 30cm/px OK
        # "Des Moines": [-93.7091411,41.4796389,-93.4936911,41.6589106],  # 30cm/px IA
        # "Little Rock": [-92.5215905,34.6256657,-92.1506554,34.8218226],  # 30cm/px AR
        # "Fayetteville": [-94.2978481,35.9893558,-94.0267113,36.1489329] # 30cm/px AR
        # "New Orleans": [-90.1399307,29.8654809,-89.6251763,30.1994687],  # 30cm/px LA
        # "Cleveland": [-81.8536772, 41.3396574, -81.5336772, 41.6596574],  # 30cm/px OH
        "Miami": [-80.35362, 25.6141728, -80.03362, 25.9341728],  # 30cm/px FL
        "Baltimore": [-76.770759, 39.1308816, -76.450759, 39.4508816],  # 30cm/px MD
        # "Dover": [-71.0339761, 43.0381117, -70.7139761, 43.3581117],  # 30cm/px DE
        # "Wilmington": [-75.706589,39.5859468,-75.386589,39.9059468] # 30cm/px DE
        # "Jersey City": [-74.1166865,40.661622,-74.0206386,40.7689376],  # 30cm/px NJ
        # "Hartford": [-72.8508547, 41.604582, -72.5308547, 41.924582],  # 30cm/px CT
        # "Providence": [-71.5728343, 41.6639891, -71.2528343, 41.9839891],  # 30cm/px RI
        # "Boston": [-71.220511, 42.1954334, -70.900511, 42.5154334],  # 30cm/px MA
        # "Burlington": [-73.372906, 44.3161601, -73.052906, 44.6361601],  # 30cm/px VT
        # "Nashua": [-71.6277032, 42.6056251, -71.3077032, 42.9256251],  # 30cm/px NH
        # "Keene": [-72.4384264,42.773597,-72.1184264,43.093597] # 30cm/px NH

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

    # Mapillary API token
    MLY_KEY = "MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9"

    # In meters
    R_EARTH = 6378000

    # Side length of desired aerial image in meters (~100-125 is zoom level 18)
    SIDE_LENGTH = 125

    # Overlap ratio between neighboring samples (0.5 = 50% overlap)
    OVERLAP_RATIO = 0.5

    num_lines = mp.Value("i", 0)

    # Pre-compute total number of planned grid samples across all cities for the progress denominator
    total_target_samples = 0
    for bbox in cities.values():
        west, south, east, north = bbox
        total_target_samples += count_grid_samples(west, south, east, north, SIDE_LENGTH, OVERLAP_RATIO)

    total_successful_samples = 0

    with tqdm(total=total_target_samples, desc="Dataset progress", unit="sample") as pbar:
        for city, bbox in cities.items():
            tqdm.write(f"\nProcessing {city}...")

            west, south, east, north = bbox
            
            # Generate grid-based sample points
            sample_points = generate_grid_samples(west, south, east, north, SIDE_LENGTH, OVERLAP_RATIO)
            tqdm.write(f"Generated {len(sample_points)} grid sample points for {city}")
            
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
            
            # Create a progress bar for this specific city
            with tqdm(total=len(sample_points), desc=f"{city} progress", unit="sample", leave=False) as city_pbar:
                with mp.Pool(processes=NUM_PROCESSES, initializer=init_worker, initargs=(lock, num_lines)) as pool:
                    # Process sample points with proper task management to prevent overloading
                    sample_index = 0
                    
                    while sample_index < len(sample_points) or active_tasks:
                        # Submit new tasks if we have room and more samples to process
                        while (len(active_tasks) < NUM_PROCESSES + 2 and 
                               sample_index < len(sample_points)):
                            lat, lng = sample_points[sample_index]
                            task_args = (
                                city, lat, lng, samples_path, metadata_path,
                                MLY_KEY, R_EARTH, SIDE_LENGTH,
                            )
                            async_result = pool.apply_async(task, task_args)
                            active_tasks.append(async_result)
                            sample_index += 1
                        
                        # Check for completed tasks
                        completed_tasks = []
                        for async_result in active_tasks:
                            if async_result.ready():
                                result = async_result.get()
                                if result is True:
                                    successful_samples += 1
                                    total_successful_samples += 1
                                pbar.update(1)  # Update overall progress
                                city_pbar.update(1)  # Update city progress
                                completed_tasks.append(async_result)
                        
                        # Remove completed tasks
                        for completed in completed_tasks:
                            active_tasks.remove(completed)
                        
            # Calculate success percentage
            success_percentage = (successful_samples / len(sample_points)) * 100 if len(sample_points) > 0 else 0
            
            # Calculate city bounding box area in square kilometers
            # Convert degrees to approximate kilometers
            lat_span_km = (north - south) * 111  # 1 degree latitude ≈ 111 km
            lng_span_km = (east - west) * 111 * np.cos(np.radians((south + north) / 2))  # Adjust for longitude
            city_area_km2 = lat_span_km * lng_span_km
            
            # Calculate success density (successful samples per square kilometer)
            success_density = successful_samples / city_area_km2 if city_area_km2 > 0 else 0
            
            tqdm.write(f"Completed {city} with {successful_samples}/{len(sample_points)} successful samples!")
            tqdm.write(f"  Success rate: {success_percentage:.4f}%")
            tqdm.write(f"  Success density: {success_density:.4f} samples/km²")
            tqdm.write(f"  City area: {city_area_km2:.4f} km²")
    print(f"Dataset complete! Total successful samples: {total_successful_samples}")


if __name__ == "__main__":
    main()