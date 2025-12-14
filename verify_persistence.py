from database import SessionLocal
from models import Activity, SleepLog, HRVLog, ActivityStream

def verify_persistence():
    db = SessionLocal()
    try:
        # Check Sleep
        sleep_count = db.query(SleepLog).count()
        hrv_count = db.query(HRVLog).count()
        
        print(f"Sleep Logs: {sleep_count}")
        print(f"HRV Logs: {hrv_count}")
        
        if sleep_count > 0:
            s = db.query(SleepLog).first()
            print(f"Sample Sleep: Date={s.calendar_date}, Duration={s.duration_seconds}, Score={s.sleep_score}")

        # Check Weather in Activity
        # Check Latest Activity
        act = db.query(Activity).order_by(Activity.start_time_local.desc()).first()
        if act:
             print(f"Checking Latest Activity: {act.activity_name} ({act.activity_id})")
             if act.raw_json and 'native_laps' in act.raw_json:
                 laps = act.raw_json['native_laps']
                 print(f"SUCCESS: Found native_laps (Count: {len(laps)})")
                 if len(laps) > 0:
                     print(f"Sample Lap: {laps[0]}")
             else:
                 print("FAIL: No native_laps in raw_json.")
        
        # Check Streams for THIS activity
        if act:
            stream_count = db.query(ActivityStream).filter(ActivityStream.activity_id == act.activity_id).count()
            print(f"Stream Count for {act.activity_id}: {stream_count}")
            
            if stream_count > 0:
                grade_count = db.query(ActivityStream).filter(ActivityStream.activity_id == act.activity_id, ActivityStream.grade.isnot(None)).count()
                print(f"Grade populated count: {grade_count}/{stream_count}")
                
                if grade_count > 0:
                    from sqlalchemy import func
                    stats = db.query(func.min(ActivityStream.grade), func.max(ActivityStream.grade), func.avg(ActivityStream.grade)).filter(ActivityStream.activity_id == act.activity_id).first()
                    print(f"Grade Stats -> Min: {stats[0]}, Max: {stats[1]}, Avg: {stats[2]}")
                
                first_s = db.query(ActivityStream).filter(ActivityStream.activity_id == act.activity_id).first()
                print(f"Sample Stream: Grade={first_s.grade}, Alt={first_s.altitude}, Dist={first_s.distance}")
            else:
                print("CRITICAL FAIL: No streams found for latest activity.")

    finally:
        db.close()

if __name__ == "__main__":
    verify_persistence()
