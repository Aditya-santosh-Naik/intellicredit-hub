import requests
import json

url = "http://127.0.0.1:5000/api/verify-mca"
payload = {
    "company": "Tata Motors Ltd",
    "cin": "L28920MH1945PLC004520",
    "pan": "AAACT2727Q"
}
try:
    response = requests.post(url, json=payload, timeout=5)
    print("Status:", response.status_code)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Flask endpoint failed: {e}")
