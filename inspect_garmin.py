from garminconnect import Garmin
from config import Settings
import garth

try:
    # garth.configure(repo=Settings.TOKEN_DIR) # Removed as per previous fix
    client = Garmin(Settings.GARMIN_EMAIL, Settings.GARMIN_PASSWORD)
    client.login()
    
    print("Methods:")
    for method in dir(client):
        if not method.startswith("_"):
            print(method)
            
except Exception as e:
    print(f"Error: {e}")
