import garth
from config import Settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_hr_zones():
    try:
        settings = Settings()
        email = settings.GARMIN_EMAIL
        password = settings.GARMIN_PASSWORD
        
        print("Logging in to Garth...")
        garth.login(email, password)
        
        print("Fetching Training Status / User Settings...")
        # Check specific endpoints commonly used for zones
        # Try getting heart rate zones directly if a method exists, or inspect user settings
        
        # 'biometric-service/heartRateZones' is a common path pattern, let's explore
        try:
             zones = garth.client.connectapi("/biometric-service/heartRateZones")
             print("Found Zones (biometric-service):")
             print(zones)
        except Exception as e:
            print(f"Failed biometric-service: {e}")

        # Try internal proxy if above fails or to see structure
        try:
            settings = garth.client.connectapi("/user-settings-service/user/settings")
            print("\nUser Settings keys:", settings.keys())
        except Exception as e:
            print(f"Failed user-settings: {e}")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    debug_hr_zones()
