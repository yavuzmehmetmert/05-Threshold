import garth
from auth_service import get_garmin_client
import json
import os

from config import Settings

def debug_garth_profile():
    try:
        print("Initializing Garth...")
        garth.login(Settings.GARMIN_EMAIL, Settings.GARMIN_PASSWORD)
        
        print("Garth User:", garth.client.username)
        
        # Endpoint 1: User Settings (Units, etc.)
        try:
            print("\n--- FETCHING USER SETTINGS ---")
            settings = garth.client.connectapi(
                f"/userprofile-service/userprofile/user-settings"
            )
            print(json.dumps(settings, indent=2))
        except Exception as e:
            print(f"Failed User Settings: {e}")

        # Endpoint 2: Personal Information (Weight, Height, etc.)
        try:
            print("\n--- FETCHING PERSONAL INFO ---")
            # Note: The endpoint might need the username or be generic
            # Trying generic first
            personal_info = garth.client.connectapi(
                f"/userprofile-service/userprofile/personal-information"
            )
            print(json.dumps(personal_info, indent=2))
        except Exception as e:
            print(f"Failed Personal Info (Generic): {e}")

        # Endpoint 3: User Profile (Biometrics)
        try:
            print("\n--- FETCHING BIOMETRICS ---")
            biometrics = garth.client.connectapi(
                f"/biometrics-service/biometrics/user/{garth.client.username}"
            )
            print(json.dumps(biometrics, indent=2))
        except Exception as e:
            print(f"Failed Biometrics: {e}")

    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    debug_garth_profile()
