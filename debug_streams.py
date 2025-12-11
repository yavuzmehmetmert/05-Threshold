from database import SessionLocal
from models import User, Activity, ActivityStream
from sqlalchemy import func

def check_counts():
    db = SessionLocal()
    try:
        user_count = db.query(func.count(User.id)).scalar()
        act_count = db.query(func.count(Activity.id)).scalar()
        stream_count = db.query(func.count(ActivityStream.id)).scalar()
        
        print(f"Users: {user_count}")
        print(f"Activities: {act_count}")
        print(f"Streams: {stream_count}")
        
        if stream_count > 0:
            print("SUCCESS: Streams populated!")
        else:
            print("WARNING: Streams empty.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_counts()
