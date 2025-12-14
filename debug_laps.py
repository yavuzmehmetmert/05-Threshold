
import sys
import os
import json
from sqlalchemy import text
from database import SessionLocal

# Add current dir to path to find modules
sys.path.append(os.getcwd())

def debug_laps():
    try:
        db = SessionLocal()
        print("Connected to PostgreSQL via SQLAlchemy")
        
        # Get the most recent activity with native laps
        print("--- INSPECTING NATIVE LAPS ---")
        # We need to find an activity that actually has native_laps in raw_json
        result = db.execute(text("SELECT id, activity_id, activity_name, raw_json FROM activities ORDER BY start_time_local DESC LIMIT 5"))
        rows = result.fetchall()
        
        found_laps = False
        for row in rows:
            db_id, garmin_id, name, raw_json = row
            if not raw_json:
                continue
                
            native_laps = raw_json.get('native_laps')
            if native_laps and len(native_laps) > 0:
                print(f"\nFOUND LAPS in Activity: {name} (ID: {garmin_id})")
                print(f"Number of Laps: {len(native_laps)}")
                print("First Lap Object Keys & Values:")
                first_lap = native_laps[0]
                for k, v in first_lap.items():
                    print(f"  {k}: {v} (Type: {type(v)})")
                
                # Check for distance specifically
                dist = first_lap.get('distance')
                total_dist = first_lap.get('total_distance')
                print(f"\nSpecific Checks:")
                print(f"  distance: {dist}")
                print(f"  total_distance: {total_dist}")
                
                found_laps = True
                break
        
        if not found_laps:
            print("No activities found with 'native_laps' in the last 5 activities.")

        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_laps()
