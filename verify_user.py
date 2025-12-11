from database import SessionLocal
from models import User, Activity
from sqlalchemy import func

def verify():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if user:
            print(f"User Found: {user.full_name} (Garmin ID: {user.garmin_id})")
            print(f"Email: {user.email}")
        else:
            print("No User found.")
            
        act_count = db.query(func.count(Activity.id)).scalar()
        print(f"Activities Count: {act_count}")
        
        if act_count > 0:
            first = db.query(Activity).first()
            print(f"Sample Activity: {first.activity_name} (ID: {first.activity_id})")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify()
