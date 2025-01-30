import json

# Load the JSON data
with open('colmap/pc.json', 'r') as f:
    data = json.load(f)

# Print the structure of data to inspect
print(data)

# Extract camera positions (gps_position)
camera_positions = []
for entry in data:  # Iterate through the list
    if 'shots' in entry:  # Check if 'shots' key exists in the current entry
        for shot_key, shot_data in entry['shots'].items():
            gps_position = shot_data.get('gps_position')
            if gps_position:
                camera_positions.append(gps_position)

# Write the .ply file
with open('colmap/output.ply', 'w') as f:
    f.write("ply\n")
    f.write("format ascii 1.0\n")
    f.write(f"element vertex {len(camera_positions)}\n")
    f.write("property float x\n")
    f.write("property float y\n")
    f.write("property float z\n")
    f.write("end_header\n")
    
    for pos in camera_positions:
        f.write(f"{pos[0]} {pos[1]} {pos[2]}\n")

print("PLY file created: output.ply")
