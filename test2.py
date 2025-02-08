import bpy
import json
import mathutils

# Load the JSON data (replace with your actual file path)
with open('C:\\Users\\medev\\CSProjects\\cmvpe\\pc.json', 'r') as file:
    data = json.load(file)[0]

# Clear the existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Add the point cloud
points = data['points']
for point_id, point_data in points.items():
    coordinates = point_data['coordinates']
    color = point_data['color']
    
    # Create a sphere to represent the point (small scale for visualization)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=coordinates)
    point_obj = bpy.context.object
    point_obj.name = f"Point_{point_id}"
    
    # Set the color of the point (simple material)
    mat = bpy.data.materials.new(name=f"PointMaterial_{point_id}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)  # RGBA
    point_obj.data.materials.append(mat)

# Add the cameras
shots = data['shots']
for shot_id, shot_data in shots.items():
    # Get the camera's position and rotation
    translation = shot_data['translation']
    rotation = shot_data['rotation']
    
    # Create a camera
    bpy.ops.object.camera_add(location=translation)
    camera_obj = bpy.context.object
    camera_obj.name = f"Camera_{shot_id}"
    
    # Set the rotation (convert to radians)
    camera_obj.rotation_euler = (
        mathutils.Euler([rotation[0], rotation[1], rotation[2]], 'XYZ')
    )
    
    # Set camera properties (e.g., focal length)
    camera_obj.data.lens = 18.0  # Example focal length, adjust as needed
    
    # Set the camera as the active camera in the scene
    bpy.context.scene.camera = camera_obj
