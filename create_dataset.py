import requests, mercantile

east, south, west, north = [-95.462265, 29.676326, -95.262451, 29.815917]

# Mapillary access token -- provide your own, replace this example
mly_key = 'MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9'

# use zoom 18 size map tiles, which are quite small -- see https://mapsam.com/map to understand the sizes
tiles = list(mercantile.tiles(east, south, west, north, 15))
bbox_list = [mercantile.bounds(tile.x, tile.y, tile.z) for tile in tiles]

# loop through each smaller bbox to request data
for bbox in bbox_list[0:1]:
    bbox_str = str(f'{bbox.west},{bbox.south},{bbox.east},{bbox.north}')
    url = f'https://graph.mapillary.com/map_features?access_token={mly_key}&bbox={bbox_str}&limit=100'
    response = requests.get(url)
    if response.status_code == 200:
        json = response.json()
        image_ids = ['4552108954803253']
        image_ids.extend([obj['id'] for obj in json['data']])

for image_id in image_ids:
    image_url = f'https://graph.mapillary.com/{image_id}?access_token={mly_key}&fields=thumb_original_url'
    response = requests.get(image_url)
    image_data = response.json()
    jpeg_url = image_data['thumb_original_url']
    print(jpeg_url)