import requests
import json

base = "http://127.0.0.1:5000/api/cases"

print(">> 1. Creating new Case...")
payload = {
    "company": "Test Case Corp",
    "sector": "Manufacturing",
    "loan_amount": 100000000,
    "annual_turnover": 450000000
}
try:
    r1 = requests.post(base, json=payload, timeout=5)
    print("POST", r1.status_code, r1.json())
    case_id = r1.json().get('case_id')
    
    print(f"\n>> 2. Fetching {case_id}...")
    r2 = requests.get(f"{base}/{case_id}", timeout=5)
    print("GET by ID", r2.status_code, r2.json()['status'], r2.json()['company'])
    
    print("\n>> 3. Listing all cases...")
    r3 = requests.get(base, timeout=5)
    print("GET all", r3.status_code, f"Count: {len(r3.json())}")

except Exception as e:
    print(f"Test failed: {e}")
