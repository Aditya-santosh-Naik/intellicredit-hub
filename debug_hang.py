import requests
import json
from pymongo import MongoClient

print("Checking MongoDB for Case LC-000005...")
client = MongoClient("mongodb://localhost:27017/")
db = client["intellicredit"]
case = db["cases"].find_one({"case_id": "LC-000005"})
if case:
    print(json.dumps(case, default=str, indent=2))
else:
    print("Case not found")

print("\n--- Sending request to extract endpoint ---")
try:
    r = requests.post("http://127.0.0.1:5000/api/cases/LC-000005/extract", timeout=10)
    print(r.status_code)
    print(r.text)
except Exception as e:
    print("Request failed or timed out:", e)
