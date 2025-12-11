import requests
import json

try:
    response = requests.get('http://localhost:8000/ingestion/activities?limit=5')
    if response.status_code == 200:
        data = response.json()
        print(f"Got {len(data)} activities.")
        for i, act in enumerate(data):
            print(f"Activity {i}: ID={act.get('activityId')}, RPE={act.get('perceivedEffort')}, Eval={act.get('userEvaluation')}")
            if i >= 2: break
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Exception: {e}")
