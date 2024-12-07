import requests
  
mly_key = 'MLY|9042214512506386|3607fa048afce1dfb774b938cbf843f9'
map_feature_id = '241757724395351'
url = f'https://graph.mapillary.com/{map_feature_id}?access_token={mly_key}&fields=images&limit=2'
image_ids = []

response = requests.get(url)

if response.status_code == 200: 
    json = response.json()
    image_ids = [obj['id'] for obj in json['images']['data']]

print(image_ids)
# get and print the URL of each image, to access the JPEG
# for image_id in image_ids:
#     image_url = f'https://graph.mapillary.com/{image_id}?access_token={mly_key}&fields=thumb_original_url'
#     response = requests.get(image_url)
#     image_data = response.json()
#     jpeg_url = image_data['thumb_original_url']
#     print(jpeg_url)