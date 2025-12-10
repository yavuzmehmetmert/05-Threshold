import requests
import json
import os
import time

BASE_URL = "http://localhost:8000"
MOCK_DIR = "mock_data"

if not os.path.exists(MOCK_DIR):
    os.makedirs(MOCK_DIR)

def save_json(filename, data):
    path = os.path.join(MOCK_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved {path}")

def capture():
    print("Capturing Profile...")
    try:
        resp = requests.get(f"{BASE_URL}/ingestion/profile")
        if resp.ok:
            save_json("profile.json", resp.json())
        else:
            print(f"Failed to fetch profile: {resp.status_code}")
    except Exception as e:
        print(f"Error fetching profile: {e}")

    print("Capturing Activities...")
    activities = []
    try:
        resp = requests.get(f"{BASE_URL}/ingestion/activities")
        if resp.ok:
            activities = resp.json()
            save_json("activities.json", activities)
        else:
            print(f"Failed to fetch activities: {resp.status_code}")
    except Exception as e:
        print(f"Error fetching activities: {e}")

    # Capture details for top 5 activities
    for activity in activities[:5]:
        act_id = activity.get('activityId')
        if act_id:
            print(f"Capturing Activity Details: {act_id}...")
            try:
                resp = requests.get(f"{BASE_URL}/ingestion/activity/{act_id}")
                if resp.ok:
                    save_json(f"activity_{act_id}.json", resp.json())
                else:
                    print(f"Failed to fetch activity {act_id}: {resp.status_code}")
            except Exception as e:
                print(f"Error fetching activity {act_id}: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    capture()
