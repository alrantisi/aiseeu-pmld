import requests

url = "http://127.0.0.1:5000/api/cameras/cam_test/roi"

data = {
    "roi_zones": [
        {
            "zone_id": "z1",
            "zone_name": "Utara",
            "points": [
                [100, 100],
                [500, 100],
                [500, 400],
                [100, 400]
            ]
        },
        {
            "zone_id": "z2",
            "zone_name": "Selatan",
            "points": [
                [600, 100],
                [1000, 100],
                [1000, 400],
                [600, 400]
            ]
        }
    ]
}

response = requests.post(url, json=data)

print("Status:", response.status_code)
print("Response:")

try:
    print(response.json())
except:
    print(response.text)