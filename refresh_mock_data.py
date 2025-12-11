import json
import os
from garminconnect import Garmin
from config import Settings
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def refresh_mock_data():
    try:
        print("Authenticating with Garmin...")
        client = Garmin(Settings.GARMIN_EMAIL, Settings.GARMIN_PASSWORD)
        client.login()
        print("Authentication successful.")

        # 1. Fetch Summary (Activities)
        print("Fetching recent activities...")
        activities = client.get_activities(0, 50)
        
        processed_activities = []
        for act in activities:
            # Extract RPE safely
            user_eval = act.get('userEvaluation', {})
            rpe = user_eval.get('perceivedEffort', None) if user_eval else None
            feeling = user_eval.get('feeling', None) if user_eval else None

            processed_activities.append({
                "activityId": act['activityId'],
                "activityName": act['activityName'],
                "startTimeLocal": act['startTimeLocal'],
                "activityType": act['activityType']['typeKey'],
                "distance": act['distance'],
                "duration": act['duration'],
                "averageHeartRate": act.get('averageHR'),
                "calories": act.get('calories'),
                "elevationGain": act.get('totalElevationGain'),
                "avgSpeed": act.get('averageSpeed'),
                # Capture Real RPE
                "perceivedEffort": rpe,
                "feeling": feeling,
                # Keep original struct for reference if needed
                "userEvaluation": user_eval
            })

        # Save to mock_data/activities.json
        with open("mock_data/activities.json", "w") as f:
            json.dump(processed_activities, f, indent=4)
        print(f"Saved {len(processed_activities)} activities to mock_data/activities.json")

        # 2. Fetch Details for Top 3 Activities (For Detail Screen Mocks)
        for i in range(min(3, len(processed_activities))):
            act_id = processed_activities[i]['activityId']
            print(f"Fetching details for activity {act_id}...")
            try:
                # Get FIT data (this usually requires downloading FIT and parsing, 
                # but for now let's see if we can get the JSON details usually returned by modern endpoints.
                # Garmin 'get_activity_details' usually returns summary. 
                # We need the FIT points. 
                # Since 'ingestion_service.py' downloads FIT, let's skip complex detail fetching here 
                # unless we copy that logic.
                # For now, updating the LIST is the priority for RPE.
                pass 
            except Exception as e:
                print(f"Failed to fetch detail for {act_id}: {e}")

    except Exception as e:
        print(f"Error refreshing mock data: {e}")

if __name__ == "__main__":
    refresh_mock_data()
