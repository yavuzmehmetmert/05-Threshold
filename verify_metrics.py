from database import SessionLocal
from models import Activity

def check_metrics():
    db = SessionLocal()
    try:
        # Check specific activity if known, or first one
        act = db.query(Activity).filter(Activity.activity_id == 21211964840).first()
        if not act:
             act = db.query(Activity).first()
             
        if act:
            print(f"Activity: {act.activity_name} ({act.activity_id})")
            print(f"Stride Len: {act.avg_stride_length}")
            print(f"Vert Osc: {act.avg_vertical_oscillation}")
            print(f"GCT: {act.avg_ground_contact_time}")
            
            if act.raw_json:
                 print(f"Raw Stride from JSON: {act.raw_json.get('avgStrideLength')}")
        else:
            print("No activity found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_metrics()
