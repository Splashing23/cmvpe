import os
import random

cities = {
    # Dense ground mapillary data
    "Colorado Springs": [-104.985348, 38.6739578, -104.665348, 38.9939578],  # 30cm/px
    "Montpelier": [-72.7351208, 44.1002164, -72.4151208, 44.4202164],  # 30cm/px

    # Major cities in each 30cm/px state (generally ordered from west to east) (FOCUS ON THESE)
    "Portland": [-70.4172642, 43.4992687, -70.0972642, 43.8192687],  # 30cm/px OR
    "Phoenix": [-112.234141, 33.2884367, -111.914141, 33.6084367],  # 30cm/px AZ
    "Denver": [-105.144862, 39.5792364, -104.824862, 39.8992364],  # 30cm/px CO
    "Oklahoma City": [-97.830948,35.290695,-97.124718,35.6748662],  # 30cm/px OK
    "Des Moines": [-93.7091411,41.4796389,-93.4936911,41.6589106],  # 30cm/px IA
    "Little Rock": [-92.5215905,34.6256657,-92.1506554,34.8218226],  # 30cm/px AR
    "New Orleans": [-90.1399307,29.8654809,-89.6251763,30.1994687],  # 30cm/px LA
    "Cleveland": [-81.8536772, 41.3396574, -81.5336772, 41.6596574],  # 30cm/px OH
    "Miami": [-80.35362, 25.6141728, -80.03362, 25.9341728],  # 30cm/px FL
    "Baltimore": [-76.770759, 39.1308816, -76.450759, 39.4508816],  # 30cm/px MD
    "Dover": [-71.0339761, 43.0381117, -70.7139761, 43.3581117],  # 30cm/px DE
    "Jersey City": [-74.1166865,40.661622,-74.0206386,40.7689376],  # 30cm/px NJ
    "Hartford": [-72.8508547, 41.604582, -72.5308547, 41.924582],  # 30cm/px CT
    "Providence": [-71.5728343, 41.6639891, -71.2528343, 41.9839891],  # 30cm/px RI
    "Boston": [-71.220511, 42.1954334, -70.900511, 42.5154334],  # 30cm/px MA
    "Burlington": [-73.372906, 44.3161601, -73.052906, 44.6361601],  # 30cm/px VT
    "Nashua": [-71.6277032, 42.6056251, -71.3077032, 42.9256251],  # 30cm/px NH

    # Major cities in 60cm/px states
    "Houston": [-95.5276974, 29.5989382, -95.2076974, 29.9189382],  # 60cm/px
    "Seattle": [-122.490062, 47.4438321, -122.170062, 47.7638321],  # 60cm/px
    "Washington D.C.": [-77.1197949, 38.7916303, -76.909366, 38.995968],  # most likely 60cm/px
    "Detroit": [-83.2066403, 42.1715509, -82.8866403, 42.4915509],  # 60cm/px
    "San Francisco": [-122.579906, 37.6190262, -122.259906, 37.9390262],  # 60cm/px
}

TRAIN_TEST_SPLIT = 0.8

N_REGIONS_SIDE = 10

regions = [(i, j) for i in range(N_REGIONS_SIDE) for j in range(N_REGIONS_SIDE)]
random.shuffle(regions)
train = set(regions[:int(len(regions) * TRAIN_TEST_SPLIT)])

for city in os.listdir(os.path.join("dataset", "splits")):
    unused_count = 0
    city_splits_path = os.path.join("dataset", "splits", city)
    with open(os.path.join(city_splits_path, "samples.csv"), "r") as f_samples, open(os.path.join(city_splits_path, "train.csv"), "w") as f_train, open(os.path.join(city_splits_path, "test.csv"), "w") as f_test:
        long_unit = (cities[city][2] - cities[city][0]) / N_REGIONS_SIDE
        lat_unit = cities[city][3] - cities[city][1] / N_REGIONS_SIDE
        lines = f_samples.readlines()
        for line in lines[1:]:
            aer_image_name = line.strip().split(',')[0]
            bbox = aer_image_name[:-4].split("_")[1:]
            bbox = [float(edge) for edge in bbox]

            long_gl_diff = (bbox[2] - bbox[0]) / 4
            lat_gl_diff = (bbox[3] - bbox[1]) / 4

            left_region = int((bbox[0] + long_gl_diff - cities[city][0]) / long_unit)
            bottom_region = int((bbox[3] + lat_gl_diff - cities[city][1]) / lat_unit)
            right_region = int((bbox[2] - long_gl_diff - cities[city][0]) / long_unit)
            top_region = int((bbox[1] - lat_gl_diff - cities[city][1]) / lat_unit)
            
            if left_region != right_region or top_region != bottom_region:
                unused_count += 1
                continue
            else:
                if (left_region, top_region) in train:
                    f_train.write(line)
                else:
                    f_test.write(line)

    print(f"Unused percentage in {city}: {unused_count / len(lines[1:]) * 100:.2f}%")