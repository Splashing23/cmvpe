from owslib.wms import WebMapService

# Connect to GIBS WMS Service
wms = WebMapService('https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?', version='1.1.1')

# Configure request for MODIS_Terra_CorrectedReflectance_TrueColor
img = wms.getmap(layers=['MODIS_Terra_CorrectedReflectance_TrueColor'],  # Layers
                 srs='epsg:4326',  # Map projection
                 bbox=(-100, 29, -90, 30),  # Bounds
                 size=(5000, 5000),  # Image size
                 time='2024-09-21',  # Time of data
                 format='image/png',  # Image format
                 transparent=True)  # Nodata transparency

# Save output PNG to a file
out = open('MODIS_Terra_CorrectedReflectance_TrueColor.png', 'wb')
out.write(img.read())
out.close()

# # View image
# Image('python-examples/MODIS_Terra_CorrectedReflectance_TrueColor.png')