from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import models
import json
from datetime import datetime

# --- User CRUD ---
def upsert_user(db: Session, garmin_id: str, email: str = None, full_name: str = None):
    user = db.query(models.User).filter(models.User.garmin_id == garmin_id).first()
    if not user:
        user = models.User(garmin_id=garmin_id, email=email, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update if changed
        if email and user.email != email:
            user.email = email
            db.commit()
    return user

# --- Activity CRUD ---

def upsert_activity(db: Session, activity_data: dict, user_id: int, raw_json: dict = None):
    """
    Inserts or updates an activity.
    Matches primarily on activity_id.
    """
    # parse timestamp if string
    # Parse start time
    start_local_str = activity_data.get('startTimeLocal')
    start_dt = None
    local_date = None
    
    if start_local_str:
        try:
            if isinstance(start_local_str, str):
                try:
                    start_dt = datetime.strptime(start_local_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    if "T" in start_local_str:
                        start_dt = datetime.fromisoformat(start_local_str)
            elif isinstance(start_local_str, datetime):
                start_dt = start_local_str
            
            if start_dt:
                local_date = start_dt.date()
        except:
            pass

    # Helper for deep get
    def get_val(keys, default=None):
        curr = activity_data
        for k in keys:
            if isinstance(curr, dict):
                 curr = curr.get(k)
            else:
                return default
        return curr if curr is not None else default

    db_obj = models.Activity(
        activity_id=activity_data['activityId'],
        user_id=user_id,
        activity_name=activity_data['activityName'],
        start_time_local=start_dt,
        local_start_date=local_date,
        activity_type=activity_data.get('activityType', {}).get('typeKey') if isinstance(activity_data.get('activityType'), dict) else activity_data.get('activityType'),
        distance=activity_data.get('distance'),
        duration=activity_data.get('duration'),
        
        average_hr=activity_data.get('averageHR') or activity_data.get('averageHeartRate'),
        max_hr=activity_data.get('maxHR') or activity_data.get('maxHeartRate'),
        
        calories=activity_data.get('calories'),
        elevation_gain=activity_data.get('totalElevationGain') or activity_data.get('elevationGain'),
        
        avg_speed=activity_data.get('averageSpeed') or activity_data.get('avgSpeed'),
        max_speed=activity_data.get('maxSpeed'),
        
        # New Metrics
        training_effect=activity_data.get('trainingEffect') or activity_data.get('aerobicTrainingEffect'), # Fallback to aerobic if main missing
        anaerobic_te=activity_data.get('anaerobicTrainingEffect'),
        aerobic_te=activity_data.get('aerobicTrainingEffect'),
        vo2_max=activity_data.get('vO2MaxValue') or activity_data.get('vo2MaxValue'), # Handle case sensitivity
        
        # Running Dynamics / Power
        avg_power=activity_data.get('averagePower') or activity_data.get('avgPower'),
        avg_cadence=activity_data.get('averageRunningCadenceInStepsPerMinute'),
        avg_stride_length=activity_data.get('avgStrideLength') or activity_data.get('averageStrideLength'),
        avg_vertical_oscillation=activity_data.get('avgVerticalOscillation') or activity_data.get('averageVerticalOscillation'),
        avg_ground_contact_time=activity_data.get('avgGroundContactTime') or activity_data.get('averageGroundContactTime'),

        # Weather
        weather_temp=activity_data.get('weather_temp') or get_val(['minTemperature']),
        weather_condition=activity_data.get('weather_condition'),
        weather_humidity=activity_data.get('weather_humidity'),
        weather_wind_speed=activity_data.get('weather_wind_speed'),

        raw_json=raw_json or activity_data,
        metadata_blob=activity_data.get('metadata', {})
    )

    # Weather fallback from raw_json if it's detail
    if raw_json:
        # Check for specific weather keys if available in detail
        pass

    existing = db.query(models.Activity).filter(models.Activity.activity_id == db_obj.activity_id).first()
    if existing:
        # Update fields
        for key, value in db_obj.__dict__.items():
            if key != '_sa_instance_state' and key != 'id' and value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

def get_activities(db: Session, limit: int = 50):
    return db.query(models.Activity).order_by(models.Activity.start_time_local.desc()).limit(limit).all()

def get_activity(db: Session, activity_id: int):
    return db.query(models.Activity).filter(models.Activity.activity_id == activity_id).first()

def update_activity_metadata(db: Session, activity_id: int, metadata: dict):
    activity = get_activity(db, activity_id)
    if activity:
        current_meta = activity.metadata_blob or {}
        current_meta.update(metadata)
        activity.metadata_blob = current_meta
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(activity, "metadata_blob")
        
        db.commit()
        db.refresh(activity)
    return activity

# --- Sleep & HRV CRUD ---

def upsert_sleep_log(db: Session, user_id: int, date_obj, data: dict):
    # data is dailySleepDTO
    existing = db.query(models.SleepLog).filter(
        models.SleepLog.user_id == user_id,
        models.SleepLog.calendar_date == date_obj
    ).first()
    
    score = data.get('sleepScores', {}).get('overall', {}).get('value')
    
    obj_in = models.SleepLog(
        user_id=user_id,
        calendar_date=date_obj,
        duration_seconds=data.get('sleepTimeSeconds'),
        deep_seconds=data.get('deepSleepSeconds'),
        light_seconds=data.get('lightSleepSeconds'),
        rem_seconds=data.get('remSleepSeconds'),
        awake_seconds=data.get('awakeSleepSeconds'),
        sleep_score=score,
        raw_json=data
    )
    
    if existing:
        for k, v in obj_in.__dict__.items():
            if k != '_sa_instance_state' and k != 'id' and v is not None:
                setattr(existing, k, v)
    else:
        db.add(obj_in)
    
    db.commit()
    if existing: db.refresh(existing)
    else: db.refresh(obj_in)
    return existing or obj_in

def upsert_hrv_log(db: Session, user_id: int, date_obj, data: dict):
    # data is hrvSummary
    existing = db.query(models.HRVLog).filter(
        models.HRVLog.user_id == user_id,
        models.HRVLog.calendar_date == date_obj
    ).first()
    
    obj_in = models.HRVLog(
        user_id=user_id,
        calendar_date=date_obj,
        last_night_avg=data.get('lastNightAvg'),
        last_night_5min_high=data.get('lastNight5MinHigh'),
        baseline_low=data.get('baseline', {}).get('low'),
        baseline_high=data.get('baseline', {}).get('high'),
        status=data.get('status'),
        raw_json=data
    )
    
    if existing:
        for k, v in obj_in.__dict__.items():
            if k != '_sa_instance_state' and k != 'id' and v is not None:
                setattr(existing, k, v)
    else:
        db.add(obj_in)
    
    db.commit()
    return existing or obj_in

# --- Stream CRUD ---

def save_activity_streams_batch(db: Session, activity_id: int, streams: list):
    """
    Deletes existing streams for activity and bulk inserts new ones.
    streams: list of dicts {'timestamp': ..., 'heart_rate': ...}
    """
    # 1. Clear old streams
    db.query(models.ActivityStream).filter(models.ActivityStream.activity_id == activity_id).delete()
    
    # 2. Bulk Insert
    # Use SQLAlchemy bulk_insert_mappings for speed
    if not streams:
        return
        
    db.bulk_insert_mappings(models.ActivityStream, streams)
    db.commit()
