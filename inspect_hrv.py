import requests
import json

try:
    # Use the date from the logs which seemed to have data
    resp = requests.get("http://localhost:8000/ingestion/hrv/2025-12-09")
    data = resp.json()
    
    print("Keys:", data.keys() if isinstance(data, dict) else "List")
    
    if isinstance(data, dict):
        if "hrvSummary" in data:
            print("hrvSummary keys:", data["hrvSummary"].keys())
            print("hrvSummary:", json.dumps(data["hrvSummary"], indent=2))
        else:
            print("No hrvSummary found at root.")
            # Print first level keys with type
            for k, v in data.items():
                print(f"{k}: {type(v)}")

except Exception as e:
    print(e)
