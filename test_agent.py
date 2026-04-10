import requests
import json

url = "http://127.0.0.1:5000/api/intelligence/AcmeCorp"

print(f"Testing Intelligent Data Agent against: {url}")
try:
    response = requests.get(url, timeout=60) # High timeout for testing backoff
    print("\nStatus Code:", response.status_code)
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error testing agent: {e}")
