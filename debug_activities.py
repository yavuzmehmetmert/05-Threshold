import logging
from auth_service import get_garmin_client
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_activities():
    try:
        print("Connecting to Garmin...")
        client = get_garmin_client()
        print("Connected. Fetching last 3 activities...")
        
        activities = client.get_activities(0, 3)
        
        if not activities:
            print("No activities found.")
            return

        print(f"Found {len(activities)} activities.")
        
        processed_activities = []
        for act in activities:
            processed_activities.append({
                "activityId": act['activityId'],
                "activityName": act['activityName'],
                "startTimeLocal": act['startTimeLocal'],
                "activityType": act['activityType']['typeKey'],
                "distance": act['distance'],
                "duration": act['duration']
            })
            
        print(json.dumps(processed_activities, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_activities()
