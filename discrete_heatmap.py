import os
import folium
import geopandas as gpd
from shapely.geometry import box
import numpy as np
from collections import defaultdict

# Use the same cities dictionary from your original script
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

N_REGIONS_SIDE = 100

def create_discrete_heatmap(city_name):
    """Create a discrete heatmap showing image count per grid cell for a city."""
    
    city_bounds = cities[city_name]
    long_unit = (city_bounds[2] - city_bounds[0]) / N_REGIONS_SIDE
    lat_unit = (city_bounds[3] - city_bounds[1]) / N_REGIONS_SIDE
    
    # Dictionary to store image counts for each grid cell
    cell_counts = defaultdict(int)
    
    # Read samples and count images per cell
    city_splits_path = os.path.join("dataset", "splits", city_name)
    samples_file = os.path.join(city_splits_path, "samples.csv")
    
    if not os.path.exists(samples_file):
        print(f"Samples file not found for {city_name}")
        return
    
    with open(samples_file, "r") as f_samples:
        lines = f_samples.readlines()
        for line in lines[1:]:  # Skip header
            aer_image_name = line.strip().split(',')[0]
            bbox = aer_image_name[:-4].split("_")[1:]
            bbox = [float(edge) for edge in bbox]
            
            # Calculate which grid cells this image covers
            long_gl_diff = (bbox[2] - bbox[0]) / 4
            lat_gl_diff = (bbox[3] - bbox[1]) / 4
            
            left_region = int((bbox[0] + long_gl_diff - city_bounds[0]) / long_unit)
            bottom_region = int((bbox[1] + lat_gl_diff - city_bounds[1]) / lat_unit)
            right_region = int((bbox[2] - long_gl_diff - city_bounds[0]) / long_unit)
            top_region = int((bbox[3] - lat_gl_diff - city_bounds[1]) / lat_unit)
            
            # Count this image for all cells it covers
            for i in range(left_region, right_region + 1):
                for j in range(bottom_region, top_region + 1):
                    if 0 <= i < N_REGIONS_SIDE and 0 <= j < N_REGIONS_SIDE:
                        cell_counts[(i, j)] += 1
    
    # Create grid cells for visualization
    grid_cells = []
    grid_values = []
    max_count = max(cell_counts.values()) if cell_counts else 0
    
    for i, x in enumerate(np.arange(city_bounds[0], city_bounds[2], long_unit)):
        for j, y in enumerate(np.arange(city_bounds[1], city_bounds[3], lat_unit)):
            grid_cells.append(box(x, y, x + long_unit, y + lat_unit))
            count = cell_counts.get((i, j), 0)
            grid_values.append(count)
    
    grid = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:4326")
    grid['count'] = grid_values
    
    # Create folium map
    m = folium.Map(
        location=[(city_bounds[3] + city_bounds[1]) / 2, (city_bounds[2] + city_bounds[0]) / 2], 
        zoom_start=11
    )
    
    # Create discrete heatmap overlay
    heatmap_overlay = folium.FeatureGroup(name='Image Count Heatmap')
    
    # Add polygons to heatmap overlay with color based on count
    for _, row in grid.iterrows():
        sim_geo = gpd.GeoSeries([row['geometry']]).__geo_interface__['features'][0]['geometry']
        
        # Color gradient from white (0) to red (max_count)
        count = row['count']
        if max_count > 0:
            intensity = count / max_count
        else:
            intensity = 0
        
        # Create color gradient: white -> yellow -> orange -> red
        if intensity == 0:
            color_hex = '#FFFFFF'  # white
        elif intensity < 0.33:
            # White to yellow
            r = int(255)
            g = int(255 * (intensity / 0.33))
            b = int(255 * (1 - intensity / 0.33))
            color_hex = f'#{r:02x}{g:02x}{b:02x}'
        elif intensity < 0.66:
            # Yellow to orange
            r = 255
            g = int(255 * (1 - (intensity - 0.33) / 0.33))
            b = 0
            color_hex = f'#{r:02x}{g:02x}{b:02x}'
        else:
            # Orange to red
            r = 255
            g = int(255 * (1 - intensity))
            b = 0
            color_hex = f'#{r:02x}{g:02x}{b:02x}'
        
        folium.GeoJson(
            sim_geo,
            style_function=lambda feature, color=color_hex: {
                'fillColor': color,
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0.7,
            },
            tooltip=f"Image Count: {row['count']}"
        ).add_to(heatmap_overlay)
    
    heatmap_overlay.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save the map
    output_path = os.path.join(city_splits_path, "discrete_heatmap.html")
    m.save(output_path)
    
    print(f"Discrete heatmap created for {city_name}")
    print(f"Max images per cell: {max_count}")
    print(f"Total cells with images: {len([v for v in cell_counts.values() if v > 0])}")
    print(f"Output saved to: {output_path}")

def main():
    """Create discrete heatmaps for all cities."""
    for city in cities.keys():
        city_splits_path = os.path.join("dataset", "splits", city)
        if os.path.exists(city_splits_path):
            print(f"\nProcessing {city}...")
            create_discrete_heatmap(city)
        else:
            print(f"Skipping {city} - no dataset found")

if __name__ == "__main__":
    main() 