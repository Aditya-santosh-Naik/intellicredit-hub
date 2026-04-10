import requests

files_to_upload = [
    'test_alm.xlsx',
    'test_shareholding.xlsx',
    'test_borrowing.xlsx',
    'test_annual.xlsx',
    'test_portfolio.xlsx'
]

url = 'http://127.0.0.1:5000/api/upload'

for file_name in files_to_upload:
    try:
        with open(file_name, 'rb') as f:
            files = {'file': (file_name, f)}
            print(f"Uploading {file_name}...")
            response = requests.post(url, files=files)
            print("Status Code:", response.status_code)
            print("Response:", response.json())
            print("-" * 40)
    except Exception as e:
        print(f"Error testing {file_name}: {e}")
