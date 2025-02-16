import os
# import zlib
# import json
# import random
# import shutil
from io import BytesIO

import numpy as np
import requests
from PIL import Image

aer_data_url = "https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/exportImage"

latitude = 42.3601
longitude = -71.0589

# In meters
R_EARTH = 6378000

# Side length of desired aerial image in meters (~100-125 is zoom level 18)
SIDE_LENGTH = 125

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


aer_params = {
    "bbox": ",".join(map(str, aer_bbox)),
    "bboxsr": 4326,
    "size": ",".join(map(str, [256, 256])),
    "adjustAspectRatio": False,
    "format": "png32",
    "interpolation": "RSP_NearestNeighbor",
    "f": "image",
}

# Retrieve aerial image
aer_bytes_response = requests.get(aer_data_url, params=aer_params)
if aer_bytes_response.status_code == 200:
    aer_image = Image.open(BytesIO(aer_bytes_response.content))
    output_path = f"aerial_{latitude}_{longitude}_256.png"
    aer_image.convert("RGB").save(output_path, "PNG")
else:
    print(f"NAIP API Error: {aer_bytes_response.status_code}")
    print(aer_bytes_response.text)