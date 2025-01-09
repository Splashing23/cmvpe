from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from PIL import Image
from io import BytesIO

client_id = "sh-c67860da-c051-4f35-9cb0-1f350737c4bc"
client_secret = "TGbiLloPYOu7Op3DZi3eO6TvGvHMOrHq"

# Create a session
client = BackendApplicationClient(client_id=client_id)
oauth = OAuth2Session(client=client)

# Get token for the session
token = oauth.fetch_token(token_url='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
                          client_secret=client_secret, include_client_id=True)

evalscript = """
//VERSION=3
function setup() {
  return {
    input: ["VV"],
    output: { id: "default", bands: 1 },
  }
}

function evaluatePixel(samples) {
  return [2 * samples.VV]
}
"""

request = {
    "input": {
        "bounds": {
            "bbox": [
                100000,
                5000000,
                200000,
                6000000,
            ],
            "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/3857"},
        },
        "data": [
            {
                "type": "sentinel-1-grd",
                "dataFilter": {
                    "timeRange": {
                        "from": "2019-02-02T00:00:00Z",
                        "to": "2019-04-02T23:59:59Z",
                    }
                },
                "processing": {"orthorectify": "true"},
            }
        ],
    },
    "output": {
        "width": 512,
        "height": 512,
        "responses": [
            {
                "identifier": "default",
                "format": {"type": "image/png"},
            }
        ],
    },
    "evalscript": evalscript,
}

url = "https://sh.dataspace.copernicus.eu/api/v1/process"
response = oauth.post(url, json=request)
image = Image.open(BytesIO(response.content))
image.convert('RGB').save("test.jpeg", 'JPEG')

# image_bytes_response = oauth.get("https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/collections/sentinel-1-grd/items/S1B_IW_GRDH_1SDV_20191210T051027_20191210T051052_019298_0246FE_ED7D_COG.SAFE")
# print(image_bytes_response.content)
# image = Image.open(BytesIO(image_bytes_response.content))