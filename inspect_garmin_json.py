from auth_service import get_garmin_client
import json

def inspect():
    try:
        client = get_garmin_client()
        # Activity ID mentioned by user/logs: 21211964840
        # Try fetching details. Garth usually has `get_activity`? 
        # Or `connectapi` endpoint?
        # client.get_activity(id) might return the JSON.
        
        act_id = 21211964840
        print(f"Fetching {act_id}...")
        
        # Method 1: get_activity (Summary?)
        # Method 2: https://connect.garmin.com/activity-service/activity/{id}
        # Garth exposes `client.connectapi(...)`
        
        data = client.connectapi(f"/activity-service/activity/{act_id}")
        
        if 'summaryDTO' in data:
             print(f"Summary Keys: {list(data['summaryDTO'].keys())}")
             if 'startLatitude' in data['summaryDTO']:
                  print(f"Start Lat: {data['summaryDTO']['startLatitude']}")

        print("Trying Polyline Endpoint...")
        try:
             poly = client.connectapi(f"/activity-service/activity/{act_id}/polyline")
             print("Polyline Endpoint Success!")
             print(str(poly)[:100])
        except Exception as e:
             print(f"Polyline failed: {e}")
             
        print("Trying Details Endpoint (old style)...")
        try:
             details = client.connectapi(f"/activity-service/activity/{act_id}/details")
             print("Details Endpoint Success!")
             print(f"Details Keys: {list(details.keys())}")
             if 'metricDescriptors' in details:
                  print("Found metricDescriptors")
             if 'metricValues' in details:
                  print("Found metricValues")
             if 'geoPolylineDTO' in details:
                  print("Found geoPolylineDTO in details!")
        except Exception as e:
             print(f"Details failed: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
