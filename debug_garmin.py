from auth_service import get_garmin_client
from datetime import date
import json

def debug_garmin():
    try:
        print("Connecting to Garmin...")
        client = get_garmin_client()
        today = date.today().isoformat()
        
        print(f"Fetching data for {today}...")
        
        # 1. User Summary
        try:
            summary = client.get_user_summary(today)
            print("\n--- USER SUMMARY ---")
            print(json.dumps(summary, indent=2))
        except Exception as e:
            print(f"Error fetching summary: {e}")

        # 2. Body Composition
        try:
            body = client.get_body_composition(today)
            print("\n--- BODY COMPOSITION ---")
            print(json.dumps(body, indent=2))
        except Exception as e:
            print(f"Error fetching body composition: {e}")

        # 3. User Settings (Maybe weight is here?)
        try:
            settings = client.get_user_settings() # Note: Method name might vary, checking common ones
            print("\n--- USER SETTINGS ---")
            print(json.dumps(settings, indent=2))
        except Exception as e:
            print(f"Error fetching settings: {e}")

    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    debug_garmin()
