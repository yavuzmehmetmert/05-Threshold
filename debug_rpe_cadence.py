
import sys
import os
from sqlalchemy import text
from database import SessionLocal

# Add current dir to path to find modules
sys.path.append(os.getcwd())

def debug_db():
    try:
        db = SessionLocal()
        print("Connected to PostgreSQL via SQLAlchemy")
        
        print("--- RECENT ACTIVITIES (RPE CHECK) ---")
        # Use simple text query to avoid importing full models if not needed, 
        # but models import is safer for mapping. Let's use raw SQL for speed.
        result = db.execute(text("SELECT id, activity_id, activity_name, rpe, raw_json FROM activities ORDER BY start_time_local DESC LIMIT 3"))
        rows = result.fetchall()
        
        target_activity_id = None
        target_garmin_id = None

        for row in rows:
            print(f"DB ID: {row[0]}, Garmin ID: {row[1]}, Name: {row[2]}, RPE Column: {row[3]}")
            
            if not target_activity_id:
                target_activity_id = row[0]
                target_garmin_id = row[1] # BigInt

        if target_garmin_id:
            print(f"\n--- STREAMS FOR Garmin ID: {target_garmin_id} (CADENCE CHECK) ---")
            result = db.execute(text("SELECT timestamp, cadence, heart_rate FROM activity_streams WHERE activity_id = :aid LIMIT 5"), {"aid": target_garmin_id})
            streams = result.fetchall()
            if not streams:
                print("  -> No streams found for this activity_id!")
            for s in streams:
                print(f"  -> {s}")

            result = db.execute(text("SELECT count(*) FROM activity_streams WHERE activity_id = :aid AND cadence > 0"), {"aid": target_garmin_id})
            count = result.scalar()
            print(f"  -> Count of streams with cadence > 0: {count}")

        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_db()
