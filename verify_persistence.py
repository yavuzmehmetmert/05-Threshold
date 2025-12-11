from database import SessionLocal
from models import Activity, SleepLog, HRVLog

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
        # Get an activity that is likely to have weather (recent real data)
        act = db.query(Activity).filter(Activity.weather_temp.isnot(None)).first()
        if act:
            print(f"Activity with Weather: {act.activity_name} ({act.activity_id})")
            print(f"Temp: {act.weather_temp}, Hum: {act.weather_humidity}")
            print(f"Local Start Date: {act.local_start_date} (Type: {type(act.local_start_date)})")
        else:
            print("No activity with weather found (yet).")
            # Print raw keys of one activity to see if minTemperature exists
            act = db.query(Activity).first()
            if act and act.raw_json:
                 print(f"First Act Keys: {list(act.raw_json.keys())}")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify_persistence()
