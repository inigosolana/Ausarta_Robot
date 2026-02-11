import requests

API_URL = "http://localhost:8001/api/ai/limits" # Try 8001 (local) or 8002 (docker)
try:
    resp = requests.get(API_URL)
    print(f"Status: {resp.status_code}")
    print(f"Keys in response: {resp.json().keys()}")
    print(f"Data: {resp.json()}")
except Exception as e:
    print(f"Error connecting to 8001: {e}")

API_URL_8002 = "http://localhost:8002/api/ai/limits"
try:
    resp = requests.get(API_URL_8002)
    print(f"Status 8002: {resp.status_code}")
    print(f"Keys 8002: {resp.json().keys()}")
except Exception as e:
    print(f"Error connecting to 8002: {e}")
