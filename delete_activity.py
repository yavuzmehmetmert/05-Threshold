from database import SessionLocal
from models import Activity, ActivityStream

def delete_activity(activity_id):
    db = SessionLocal()
    try:
        print(f"Deleting Activity {activity_id}...")
        
        # Delete Streams
        deleted_streams = db.query(ActivityStream).filter(ActivityStream.activity_id == activity_id).delete()
        print(f"Deleted {deleted_streams} streams.")
        
        # Delete Activity
        deleted_act = db.query(Activity).filter(Activity.activity_id == activity_id).delete()
        print(f"Deleted {deleted_act} activity record.")
        
        db.commit()
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Latest Activity ID found in verification: 21230575987
    delete_activity(21230575987)
