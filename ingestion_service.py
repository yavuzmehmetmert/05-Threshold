from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
import pandas as pd
import fitparse
import os
import tempfile
import logging
import json
import random
import math
from datetime import date, datetime, timedelta
import requests
from auth_service import get_garmin_client
from config import MOCK_MODE, MOCK_BIOMETRICS
from sqlalchemy.orm import Session
from database import get_db
import crud
import models
import training_load

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def process_fit_file(fit_path: str):
    """
    FIT dosyasını parse eder ve DataFrame'e çevirir.
    """
    try:
        fitfile = fitparse.FitFile(fit_path)
        data_points = []
        laps_data = []
        
        # 1. Parse Records
        for record in fitfile.get_messages("record"):
            point = {}
            for record_data in record:
                if record_data.name in [
                    'timestamp', 'heart_rate', 'power', 'cadence', 
                    'speed', 'enhanced_speed', 'distance',
                    'position_lat', 'position_long', 
                    'altitude', 'enhanced_altitude', 'grade',
                    'vertical_oscillation', 'vertical_ratio', 'step_length', 'stance_time', 'stance_time_balance', 'left_right_balance'
                ]:
                    # 1. Handle Special Transformations
                    if record_data.name == 'enhanced_speed':
                        point['speed'] = record_data.value
                    elif record_data.name == 'enhanced_altitude':
                        point['altitude'] = record_data.value
                    elif record_data.name == 'position_lat':
                        if record_data.value is not None:
                             point['latitude'] = record_data.value * (180 / 2**31)
                    elif record_data.name == 'position_long':
                        if record_data.value is not None:
                             point['longitude'] = record_data.value * (180 / 2**31)
                    
                    # 2. Save Standard Fields
                    if record_data.name not in point and record_data.name not in ['enhanced_speed', 'enhanced_altitude', 'position_lat', 'position_long']:
                         point[record_data.name] = record_data.value
            
            if 'timestamp' in point:
                data_points.append(point)
        
        # 2. Parse Session (for RPE)
        for session in fitfile.get_messages("session"):
            logger.info(f"SESSION FIELDS: {[f.name for f in session]}")
            
        # 3. Parse Laps
        for lap in fitfile.get_messages("lap"):
            lap_obj = {}
            for lap_data in lap:
                 if lap_data.value is not None:
                     val = lap_data.value
                     if isinstance(val, (datetime, date)):
                         val = val.isoformat()
                     lap_obj[lap_data.name] = val
            laps_data.append(lap_obj)

        df = pd.DataFrame(data_points)
        
        if not df.empty:
            # 3. Calculate Grade if missing
            # Grade = (dAlt / dDist) * 100
            if 'grade' not in df.columns or df['grade'].isnull().all():
                if 'altitude' in df.columns and 'distance' in df.columns:
                     df['d_alt'] = df['altitude'].diff()
                     df['d_dist'] = df['distance'].diff()
                     # Filter noise: d_dist must be > 0.5m
                     # Grade = d_alt / d_dist * 100
                     df['grade'] = df.apply(
                         lambda row: (row['d_alt'] / row['d_dist'] * 100) 
                         if (row['d_dist'] and row['d_dist'] > 0.5 and abs(row['d_alt']) < 50) 
                         else 0.0, axis=1
                     )
                     # Smooth Grade? Optional but recommended. Rolling mean 5s
                     df['grade'] = df['grade'].rolling(window=5, center=True).mean().fillna(0.0)

        if 'speed' in df.columns:
                df = df[df['speed'] > 0]

        # 4. Extract Session Level Metrics (RPE)
        session_rpe = None
        for session in fitfile.get_messages("session"):
            
            # Check for unknown fields that might be RPE
            # Field 193 is commonly "Level" or RPE * 10
            # Field 192 is "Feeling" (0-100)
            
            val_193 = None
            for field in session:
                if field.def_num == 193:
                    val_193 = field.value
            
            if val_193 is not None:
                # Garmin stores RPE * 10 (e.g., 10 = RPE 1, 80 = RPE 8)
                session_rpe = int(val_193 / 10)
            elif session.get_value('perceived_effort'):
                 session_rpe = session.get_value('perceived_effort')
        
        return df, laps_data, session_rpe
    except Exception as e:
        logger.error(f"FIT Parse Hatası: {e}")
        return None, [], None

# --- Weather Service ---

def get_weather_condition(code: int) -> str:
    """Map WMO Weather Code to String"""
    if code == 0: return "Clear"
    if code in [1, 2, 3]: return "Partly Cloudy"
    if code in [45, 48]: return "Fog"
    if 51 <= code <= 55: return "Drizzle"
    if 61 <= code <= 67: return "Rain"
    if 71 <= code <= 77: return "Snow"
    if 80 <= code <= 82: return "Showers"
    if 85 <= code <= 86: return "Snow Showers"
    if code >= 95: return "Thunderstorm"
    return "Unknown"

def fetch_historical_weather(lat, lon, start_time_str) -> dict:
    """
    Fetch historical weather from Open-Meteo for a specific location and time.
    start_time_str: "YYYY-MM-DD HH:MM:SS" or ISO
    """
    try:
        # Parse start time
        if "T" in start_time_str:
             dt = datetime.fromisoformat(start_time_str)
        else:
             dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        
        date_str = dt.strftime("%Y-%m-%d")
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": date_str,
            "end_date": date_str,
            "hourly": "temperature_2m,relativehumidity_2m,weathercode,windspeed_10m"
        }
        
        # Open-Meteo accepts requests without key but rate limited.
        # We are doing this sequentially in sync loop so it should be fine.
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            hourly = data.get('hourly', {})
            times = hourly.get('time', [])
            
            # Find closest hour
            # API returns ISO strings "2023-12-01T00:00"
            target_iso = dt.strftime("%Y-%m-%dT%H:00")
            
            # Simple match for the exact hour
            idx = -1
            if target_iso in times:
                idx = times.index(target_iso)
            else:
                # Fallback: just take the hour index (0-23) if timezone matches UTC?
                # Open-Meteo expects local time if timezone not specified? No, defaults to GMT.
                # Garmin `startTimeLocal` is local. Open-Meteo allows `timezone=auto` or `timezone=offset`.
                # Let's try to match simply by hour index if list length is 24.
                hour_idx = dt.hour
                if 0 <= hour_idx < len(times):
                     idx = hour_idx

            if idx != -1:
                temp = hourly['temperature_2m'][idx]
                hum = hourly['relativehumidity_2m'][idx]
                code = hourly['weathercode'][idx]
                wind = hourly['windspeed_10m'][idx]
                
                return {
                    "weather_temp": temp,
                    "weather_humidity": hum,
                    "weather_condition": get_weather_condition(code),
                    "weather_wind_speed": wind
                }
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
    
    return {}

async def sync_garmin_stats_background():
    """
    Arka planda günlük biyometrik verileri (uyku vs) günceller.
    Şimdilik sadece logluyor, DB'ye biyometrik yazmıyor.
    """
    try:
        logger.info("Biyometrik senkronizasyon başlıyor...")
        client = get_garmin_client()
        today = date.today()
        # İleride burası da DB'ye yazacak.
        logger.info("Biyometrik senkronizasyon tamamlandı (Mock/Pass).")
    except Exception as e:
        logger.error(f"Biyo-Sync Hatası: {e}")

# --- LIGHTWEIGHT SYNC ENDPOINTS FOR DEVELOPMENT ---

@router.post("/sync/stress")
async def sync_stress_only(days: int = 7, db: Session = Depends(get_db)):
    """Sync only stress data for last N days (default: 7)"""
    try:
        client = get_garmin_client()
        user_id = 1
        synced = 0
        
        for i in range(days):
            d = date.today() - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            try:
                stress_data = client.get_stress_data(date_str)
                if stress_data:
                    values = stress_data.get('stressValuesArray', [])
                    valid = [v[1] for v in values if v[1] is not None and v[1] >= 0]
                    if valid:
                        avg = sum(valid) / len(valid)
                        crud.upsert_stress_log(db, user_id, d, {
                            'avgStress': round(avg),
                            'maxStress': max(valid),
                            'minStress': min(valid),
                            'status': "Low" if avg < 25 else "Medium" if avg < 50 else "High" if avg < 75 else "Very High"
                        })
                        synced += 1
            except Exception as e:
                logger.warning(f"Stress sync failed for {date_str}: {e}")
        
        return {"status": "ok", "synced_days": synced}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/sync/sleep")
async def sync_sleep_only(days: int = 7, db: Session = Depends(get_db)):
    """Sync only sleep data for last N days (default: 7)"""
    try:
        client = get_garmin_client()
        user_id = 1
        synced = 0
        
        for i in range(days):
            d = date.today() - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            try:
                sleep_data = client.get_sleep_data(date_str)
                if sleep_data and 'dailySleepDTO' in sleep_data:
                    crud.upsert_sleep_log(db, user_id, d, sleep_data['dailySleepDTO'])
                    synced += 1
            except Exception as e:
                logger.warning(f"Sleep sync failed for {date_str}: {e}")
        
        return {"status": "ok", "synced_days": synced}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/sync/hrv")
async def sync_hrv_only(days: int = 7, db: Session = Depends(get_db)):
    """Sync only HRV data for last N days (default: 7)"""
    try:
        client = get_garmin_client()
        user_id = 1
        synced = 0
        
        for i in range(days):
            d = date.today() - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            try:
                hrv_data = client.get_hrv_data(date_str)
                if hrv_data and 'hrvSummary' in hrv_data:
                    crud.upsert_hrv_log(db, user_id, d, hrv_data['hrvSummary'])
                    synced += 1
            except Exception as e:
                logger.warning(f"HRV sync failed for {date_str}: {e}")
        
        return {"status": "ok", "synced_days": synced}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/sync/profile")
async def sync_profile_only(days: int = 7, db: Session = Depends(get_db)):
    """
    Sync physiological profile metrics for last N days.
    Captures: weight, resting HR, max HR, VO2max, lactate threshold, stress, FTP.
    This creates a historical log that AI agents can analyze for trends.
    """
    if MOCK_MODE:
        # In mock mode, just log a single entry with mock data
        today = date.today()
        mock_data = {
            "weight": 70.0,
            "resting_hr": 50,
            "max_hr": 190,
            "lactate_threshold_hr": 170,
            "vo2_max": 50,
            "avg_stress": 25,
            "ftp": 250
        }
        crud.upsert_physiological_log(db, 1, today, mock_data)
        return {"status": "ok", "synced_days": 1, "mode": "mock"}
    
    try:
        client = get_garmin_client()
        user_id = 1
        synced = 0
        
        # --- Fetch STATIC metrics once (don't change daily) ---
        static_data = {}
        
        # 1. User Profile - contains weight, VO2max, LTHR
        try:
            user_profile = client.get_user_profile()
            if user_profile and 'userData' in user_profile:
                ud = user_profile['userData']
                # Weight in grams -> kg
                if ud.get('weight'):
                    static_data['weight'] = ud['weight'] / 1000.0
                static_data['vo2_max'] = ud.get('vo2MaxRunning')
                static_data['lactate_threshold_hr'] = ud.get('lactateThresholdHeartRate')
                # Save birth_date to user record
                if ud.get('birthDate'):
                    try:
                        birth_date = datetime.strptime(ud['birthDate'], '%Y-%m-%d').date()
                        user = db.query(models.User).filter(models.User.id == user_id).first()
                        if user:
                            user.birth_date = birth_date
                            db.commit()
                            logger.info(f"Birth date saved: {birth_date}")
                    except Exception as e:
                        logger.warning(f"Birth date parse failed: {e}")
            logger.info(f"User profile fetched: weight={static_data.get('weight')}kg, VO2max={static_data.get('vo2_max')}, LTHR={static_data.get('lactate_threshold_hr')}")
        except Exception as e:
            logger.warning(f"User profile fetch failed: {e}")
        
        # 2. Lactate Threshold endpoint - contains FTP
        try:
            lt_data = client.get_lactate_threshold()
            if lt_data and 'power' in lt_data:
                static_data['ftp'] = lt_data['power'].get('functionalThresholdPower')
                logger.info(f"FTP fetched: {static_data.get('ftp')}W")
            if lt_data and 'speed_and_heart_rate' in lt_data:
                # Backup LTHR from this endpoint if not from user profile
                if not static_data.get('lactate_threshold_hr'):
                    static_data['lactate_threshold_hr'] = lt_data['speed_and_heart_rate'].get('heartRate')
        except Exception as e:
            logger.warning(f"Lactate threshold fetch failed: {e}")
        
        # 3. Max Metrics - VO2max (backup)
        try:
            today_str = date.today().strftime("%Y-%m-%d")
            max_metrics = client.get_max_metrics(today_str)
            if max_metrics and len(max_metrics) > 0 and 'generic' in max_metrics[0]:
                if not static_data.get('vo2_max'):
                    static_data['vo2_max'] = max_metrics[0]['generic'].get('vo2MaxValue')
        except Exception as e:
            logger.warning(f"Max metrics fetch failed: {e}")
        
        # --- Now sync DAILY metrics for each day ---
        for i in range(days):
            d = date.today() - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            
            # Start with static data (same for all days)
            physio_data = static_data.copy()
            summary = None
            
            try:
                # Get daily summary for resting HR and stress
                summary = client.get_user_summary(date_str)
                if summary:
                    physio_data['resting_hr'] = summary.get('restingHeartRate')
                    physio_data['avg_stress'] = summary.get('averageStressLevel')
                    # Note: Not saving daily max HR - will calculate from age (220 - age)
            except Exception as e:
                logger.warning(f"User summary fetch failed for {date_str}: {e}")
            
            # Get VO2max from activities for this specific day (VO2max changes over time)
            try:
                day_activity = db.query(models.Activity).filter(
                    models.Activity.local_start_date == d,
                    models.Activity.vo2_max.isnot(None)
                ).order_by(models.Activity.start_time_local.desc()).first()
                if day_activity and day_activity.vo2_max:
                    physio_data['vo2_max'] = day_activity.vo2_max
            except Exception as e:
                logger.warning(f"Activity VO2max fetch failed for {date_str}: {e}")
            
            # Only save if we have some data
            if any(v is not None for v in physio_data.values()):
                physio_data['raw_json'] = {
                    'summary': summary,
                    'date': date_str
                }
                crud.upsert_physiological_log(db, user_id, d, physio_data)
                synced += 1
                logger.info(f"Physiological log saved for {date_str}: weight={physio_data.get('weight')}, rhr={physio_data.get('resting_hr')}, vo2max={physio_data.get('vo2_max')}")
            else:
                logger.info(f"No physiological data available for {date_str}")
        
        return {"status": "ok", "synced_days": synced, "static_metrics": {
            "weight": static_data.get('weight'),
            "vo2_max": static_data.get('vo2_max'),
            "lthr": static_data.get('lactate_threshold_hr'),
            "ftp": static_data.get('ftp')
        }}
    except Exception as e:
        logger.error(f"Profile sync error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/profile/history")
async def get_profile_history(days: int = 30, db: Session = Depends(get_db)):
    """
    Get historical physiological profile data for the last N days.
    Returns: list of daily physiological snapshots for AI analysis.
    """
    user_id = 1
    logs = crud.get_physiological_history(db, user_id, days)
    
    return [
        {
            "date": log.calendar_date.isoformat(),
            "weight": log.weight,
            "restingHr": log.resting_hr,
            "maxHr": log.max_hr,
            "lthr": log.lactate_threshold_hr,
            "vo2max": log.vo2_max,
            "thresholdPace": log.threshold_pace,
            "ftp": log.ftp,
            "bodyFatPct": log.body_fat_pct,
            "avgStress": log.avg_stress
        }
        for log in logs
    ]


@router.get("/profile/latest")
async def get_latest_profile(db: Session = Depends(get_db)):
    """
    Get the most recent physiological profile data.
    Used by frontend ProfileScreen to display current metrics.
    Max HR is calculated from age using formula: 220 - age
    """
    user_id = 1
    log = crud.get_latest_physiological_log(db, user_id)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # Calculate Max HR from age (220 - age formula)
    max_hr = 190  # default
    birth_date_str = None
    if user and user.birth_date:
        today = date.today()
        age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
        max_hr = 220 - age
        birth_date_str = user.birth_date.isoformat()
    
    if not log:
        # Return defaults if no log exists
        return {
            "weight": 70,
            "restingHr": 50,
            "maxHr": max_hr,
            "lthr": 170,
            "vo2max": 50,
            "stressScore": 25,
            "birthDate": birth_date_str
        }
    
    return {
        "date": log.calendar_date.isoformat(),
        "weight": log.weight or 70,
        "restingHr": log.resting_hr or 50,
        "maxHr": max_hr,  # Calculated from age (220 - age)
        "lthr": log.lactate_threshold_hr or 170,
        "vo2max": log.vo2_max or 50,
        "thresholdPace": log.threshold_pace,
        "ftp": log.ftp,
        "bodyFatPct": log.body_fat_pct,
        "stressScore": log.avg_stress or 25,
        "birthDate": birth_date_str
    }

# --- INCREMENTAL SYNC ENDPOINT ---
@router.post("/sync/incremental")
def sync_incremental(db: Session = Depends(get_db)):
    """
    Smart incremental sync that only fetches new data:
    1. Activities: Only fetch activities newer than the last synced activity
    2. Biometrics: Refresh sleep/stress/HRV/profile for last 7 days
    
    This is the production sync used by the app - much faster than full sync.
    """
    try:
        logger.info("Starting Incremental Sync...")
        
        # Get or create user
        if MOCK_MODE:
            garmin_id = "mock_user_123"
            email = "mock@user.com"
            full_name = "Mock Runner"
        else:
            client = get_garmin_client()
            garmin_id = client.username
            email = "real@garmin.com"
            full_name = client.display_name
            
        user_db = crud.upsert_user(db, garmin_id, email, full_name)
        user_id = user_db.id
        
        # 1. Determine sync range based on last activity
        last_activity = db.query(models.Activity).filter(
            models.Activity.user_id == user_id
        ).order_by(models.Activity.local_start_date.desc()).first()
        
        today = date.today()
        if last_activity and last_activity.local_start_date:
            days_to_sync = (today - last_activity.local_start_date).days + 1
            # Minimum 1 day, maximum 30 days for incremental
            days_to_sync = max(1, min(days_to_sync, 30))
            logger.info(f"Last activity: {last_activity.local_start_date}. Syncing last {days_to_sync} days.")
        else:
            days_to_sync = 30  # Default to 30 days if no activities
            logger.info("No activities found. Syncing last 30 days.")
        
        # 2. Fetch activities for the sync range
        synced_activities = 0
        new_activities = 0
        
        if not MOCK_MODE:
            client = get_garmin_client()
            
            # Fetch recent activities (start=0, limit based on expected count)
            # Typically 1-2 activities per day max, so fetch 2x days worth
            batch_size = min(days_to_sync * 3, 100)
            activities = client.get_activities(0, batch_size)
            
            logger.info(f"Fetched {len(activities)} recent activities from Garmin")
            
            for act in activities:
                activity_id = act.get('activityId')
                
                # Check if activity already exists
                existing = db.query(models.Activity).filter(
                    models.Activity.activity_id == activity_id
                ).first()
                
                if existing:
                    continue  # Skip existing activities
                
                # New activity - fetch full details
                logger.info(f"NEW Activity: {act.get('activityName')} ({activity_id})")
                
                # Weather enrichment
                lat = act.get('startLatitude')
                lon = act.get('startLongitude')
                start_local = act.get('startTimeLocal')
                if lat and lon and start_local:
                    w_data = fetch_historical_weather(lat, lon, start_local)
                    if w_data:
                        act.update(w_data)
                
                # Fetch detailed data
                try:
                    details_json = client.connectapi(f"/activity-service/activity/{activity_id}/details")
                    if details_json:
                        act.update(details_json)
                except Exception as e:
                    logger.warning(f"Failed to fetch details: {e}")
                
                # Upsert activity
                crud.upsert_activity(db, act, user_id)
                new_activities += 1
                synced_activities += 1
                
                # Sync biometrics for activity date
                if start_local:
                    date_str = start_local.split(' ')[0]
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    # Sleep
                    try:
                        sleep_data = client.get_sleep_data(date_str)
                        if sleep_data:
                            crud.upsert_sleep_log(db, user_id, date_obj, sleep_data)
                    except Exception as e:
                        logger.warning(f"Sleep sync error: {e}")
                    
                    # HRV
                    try:
                        hrv_data = client.get_hrv_data(date_str)
                        if hrv_data:
                            crud.upsert_hrv_log(db, user_id, date_obj, hrv_data)
                    except Exception as e:
                        logger.warning(f"HRV sync error: {e}")
        
        # 3. Sync biometrics for last 7 days (even if no new activities)
        logger.info("Syncing biometrics for last 7 days...")
        if not MOCK_MODE:
            client = get_garmin_client()
            for i in range(7):
                check_date = today - timedelta(days=i)
                date_str = check_date.isoformat()
                
                try:
                    # Stress
                    stress_data = client.get_stress_data(date_str)
                    if stress_data and 'overallStressLevel' in stress_data:
                        crud.upsert_stress_log(db, user_id, check_date, stress_data)
                    
                    # Sleep
                    sleep_data = client.get_sleep_data(date_str)
                    if sleep_data:
                        crud.upsert_sleep_log(db, user_id, check_date, sleep_data)
                    
                    # HRV
                    hrv_data = client.get_hrv_data(date_str)
                    if hrv_data:
                        crud.upsert_hrv_log(db, user_id, check_date, hrv_data)
                        
                except Exception as e:
                    logger.warning(f"Biometric sync error for {date_str}: {e}")
        
        # 4. Sync profile (latest physiological metrics)
        logger.info("Syncing profile...")
        try:
            if not MOCK_MODE:
                profile = client.get_user_profile()
                user_summary = client.get_user_summary(today.isoformat())
                
                # Update physiological log for today
                log_data = {
                    'weight': profile.get('userData', {}).get('weight', 0) / 1000 if profile.get('userData', {}).get('weight') else None,
                    'resting_hr': user_summary.get('restingHeartRate') if user_summary else None,
                    'avg_stress': user_summary.get('averageStressLevel') if user_summary else None,
                    'vo2_max': profile.get('vo2MaxRunning'),
                    'lactate_threshold_hr': profile.get('lactateThresholdHeartRate'),
                }
                
                try:
                    lt_data = client.get_lactate_threshold()
                    if lt_data:
                        log_data['ftp'] = lt_data.get('functionalThresholdPower')
                except:
                    pass
                
                crud.upsert_physiological_log(db, user_id, today, log_data)
        except Exception as e:
            logger.warning(f"Profile sync error: {e}")
        
        db.commit()
        
        logger.info(f"Incremental Sync Complete: {new_activities} new activities, {synced_activities} total processed")
        
        return {
            "status": "success",
            "new_activities": new_activities,
            "total_processed": synced_activities,
            "days_synced": days_to_sync,
            "last_sync": today.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Incremental Sync Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
def sync_all(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Tüm verileri senkronize eder:
    1. User Profile -> DB
    2. Aktiviteler (DB'ye yazılır)
    3. Streamler (FIT üzerinden okunup DB'ye yazılır)
    """
    try:
        logger.info("Starting Full Sync...")
        
        # 1. Sync User
        if MOCK_MODE:
            garmin_id = "mock_user_123"
            email = "mock@user.com"
            full_name = "Mock Runner"
        else:
            client = get_garmin_client()
            garmin_id = client.username # or display_name
            email = "real@garmin.com" 
            full_name = client.display_name
            
        user_db = crud.upsert_user(db, garmin_id, email, full_name)
        user_id = user_db.id
        logger.info(f"User Synced: {user_db.full_name} (ID: {user_id})")

        # 2. Sync Activities
        synced_count = 0
        
        if MOCK_MODE:
            # Sync from Mock File
            with open("mock_data/activities.json", "r") as f:
                activities = json.load(f)
        else:
            # Fetch ALL activities using pagination
            client = get_garmin_client()
            activities = []
            start = 0
            batch_size = 100  # Garmin API typically allows up to 100 per request
            
            logger.info("Fetching ALL activities from Garmin (this may take a while)...")
            while True:
                batch = client.get_activities(start, batch_size)
                if not batch:
                    break
                activities.extend(batch)
                logger.info(f"Fetched {len(activities)} activities so far... (batch {start//batch_size + 1})")
                start += batch_size
                
                # Safety limit to prevent infinite loops (adjust if you have more than 5000 activities)
                if start > 5000:
                    logger.warning("Reached 5000 activity limit - stopping pagination")
                    break
            
            logger.info(f"Total activities fetched: {len(activities)}")
        
        for act in activities:
            # RPE: Use existing userEvaluation from Garmin API directly
            # DO NOT generate synthetic values - they overwrite real user input!
            # The userEvaluation object from Garmin API already contains the real data

            # --- WEATHER ENRICHMENT ---
            # Do this before Upsert so columns are populated
            if not MOCK_MODE:
                 lat = act.get('startLatitude')
                 lon = act.get('startLongitude')
                 start_local = act.get('startTimeLocal') # "2024-12-09 18:30:00"
                 
                 # Only fetch if we have location and time, and maybe check if already has weather?
                 # (Optimization: if act['weather_temp'] is already in DB? but we overwrite here)
                 if lat and lon and start_local:
                      logger.info(f"Fetching Weather for {act.get('activityName')} at {start_local}...")
                      w_data = fetch_historical_weather(lat, lon, start_local)
                      if w_data:
                          act.update(w_data) # Inject into dict for CRUD
                          logger.info(f"Weather: {w_data}")

            # DEBUG: Check keys
            if act.get('activityId') == 21211964840:
                 logger.info(f"Target Activity Keys: {list(act.keys())}")
                 logger.info(f"Has avgStrideLength: {'avgStrideLength' in act}")
                 logger.info(f"Has averageStrideLength: {'averageStrideLength' in act}")

            # --- ENRICH WITH DETAILS (Polyline, Splits, Metrics) ---
            if not MOCK_MODE:
                try:
                    logger.info(f"Fetching Details JSON for {act.get('activityId')}...")
                    details_json = client.connectapi(f"/activity-service/activity/{act.get('activityId')}/details")
                    if details_json:
                        # Merge details into activity dict (so it goes into raw_json)
                        act.update(details_json)
                        # Also merge summaryDTO if useful? Usually redundancy is fine.
                        logger.info("Details merged (Polyline/Splits obtained).")
                except Exception as e:
                    logger.warning(f"Failed to fetch detailed JSON: {e}")

            # Upsert Activity
            db_act = crud.upsert_activity(db, act, user_id)
            synced_count += 1

            # 2.2 Sync Daily Biometrics (Sleep & HRV)
            # Use activity date
            try:
                # Parse date assuming "YYYY-MM-DD HH:MM:SS" or ISO
                start_local = act.get('startTimeLocal')
                if start_local:
                    date_str = start_local.split(' ')[0] # YYYY-MM-DD
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                    # Optimize: Check if exists? (Optional, CRUD handles upsert)
                    # But fetching from Garmin is slow, so check DB first? 
                    # For now, let's fetch if we are in Full Sync or if it's recent? 
                    # Let's just fetch to ensure fresh data.

                    if not MOCK_MODE:
                         # SLEEP
                         try:
                             logger.info(f"Fetching Sleep Data for {date_str}...")
                             sleep_data = client.get_sleep_data(date_str)
                             logger.info(f"Sleep Data Result: {sleep_data.keys() if sleep_data else 'None'}")
                             if sleep_data and 'dailySleepDTO' in sleep_data:
                                 crud.upsert_sleep_log(db, user_id, date_obj, sleep_data['dailySleepDTO'])
                                 logger.info("Sleep Data Upserted.")
                         except Exception as e:
                             logger.warning(f"Sleep fetch failed for {date_str}: {e}")

                         # HRV
                         try:
                             logger.info(f"Fetching HRV Data for {date_str}...")
                             hrv_data = client.get_hrv_data(date_str)
                             logger.info(f"HRV Data Result: {hrv_data.keys() if hrv_data else 'None'}")
                             if hrv_data and 'hrvSummary' in hrv_data:
                                 crud.upsert_hrv_log(db, user_id, date_obj, hrv_data['hrvSummary'])
                                 logger.info("HRV Data Upserted.")
                         except Exception as e:
                              logger.warning(f"HRV fetch failed for {date_str}: {e}")
                         
                         # Stress
                         try:
                             logger.info(f"Fetching Stress Data for {date_str}...")
                             stress_data = client.get_stress_data(date_str)
                             if stress_data:
                                 values = stress_data.get('stressValuesArray', [])
                                 if values:
                                     valid_values = [v[1] for v in values if v[1] is not None and v[1] >= 0]
                                     if valid_values:
                                         stress_summary = {
                                             'avgStress': round(sum(valid_values) / len(valid_values)),
                                             'maxStress': max(valid_values),
                                             'minStress': min(valid_values),
                                             'status': "Low" if sum(valid_values)/len(valid_values) < 25 else 
                                                       "Medium" if sum(valid_values)/len(valid_values) < 50 else 
                                                       "High" if sum(valid_values)/len(valid_values) < 75 else "Very High"
                                         }
                                         crud.upsert_stress_log(db, user_id, date_obj, stress_summary)
                                         logger.info("Stress Data Upserted.")
                         except Exception as e:
                              logger.warning(f"Stress fetch failed for {date_str}: {e}")

            except Exception as bio_e:
                logger.error(f"Biometrics Sync Error: {bio_e}")

            # 3. Sync Streams (FIT)
            streams_data = [] # Reset for this activity

            if MOCK_MODE:
                # Look for specific mock file
                mock_file = f"mock_data/activity_{db_act.activity_id}.json"
                if not os.path.exists(mock_file):
                     # Fallback for streams
                     continue # or generate synthetic?
                     
                with open(mock_file, "r") as mf:
                    flat_records = json.load(mf)
                    # mock_data is list of records
                    for rec in flat_records:
                         if 'timestamp' in rec:
                             streams_data.append({
                                 "activity_id": db_act.activity_id,
                                 "timestamp": rec['timestamp'], # format check needed?
                                 "heart_rate": rec.get('heart_rate'),
                                 "speed": rec.get('speed'),
                                 "cadence": rec.get('cadence'),
                                 "altitude": rec.get('altitude'),
                                 "power": rec.get('power'),
                                 "grade": None # calc later
                             })
            else:
                # REAL MODE STREAM
                # Download FIT
                try:
                    zip_data = client.download_activity(db_act.activity_id, dl_fmt=client.ActivityDownloadFormat.ORIGINAL)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                        tmp_zip.write(zip_data)
                        tmp_zip_path = tmp_zip.name
                    
                    import zipfile
                    with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                        fit_filename = zip_ref.namelist()[0]
                        zip_ref.extract(fit_filename, path=tempfile.gettempdir())
                        fit_path = os.path.join(tempfile.gettempdir(), fit_filename)
                        
                    df, laps_data, session_rpe = process_fit_file(fit_path) # Returns DataFrame AND Laps AND RPE
                    
                    if session_rpe is not None:
                        db_act.rpe = int(session_rpe)
                    
                    if laps_data:
                        # Store Native Laps in raw_json
                        if not db_act.raw_json: db_act.raw_json = {}
                        db_act.raw_json['native_laps'] = laps_data
                        # Trigger update for this new field
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(db_act, "raw_json")
                        db.commit()

                    if os.path.exists(tmp_zip_path): os.remove(tmp_zip_path)
                    if os.path.exists(fit_path): os.remove(fit_path)
                    
                    if df is not None and not df.empty:
                        # Convert DF to List of Dicts for DB
                        # SANITIZE: Handle NaNs and Numpy Types
                        df = df.where(pd.notnull(df), None)
                        
                        records = df.to_dict('records')
                        for i, rec in enumerate(records):
                             # Helper function to safe int cast
                             def safe_int(val):
                                 if val is None: return None
                                 try:
                                     return int(val)
                                 except:
                                     return None

                             # GCT Balance Normalization
                             # If values are raw (>128 or huge), normalize them.
                             # Fitparse *usually* converts to float % if profile is known.
                             # If we get e.g. 51.2, it's % Left.
                             stb = rec.get('stance_time_balance') or rec.get('left_right_balance')
                             
                             if stb is not None:
                                 # Heuristic: If > 100, might be encoded
                                 if stb > 1000: # e.g. 5123 = 51.23%
                                     stb = stb / 100.0
                                 elif stb > 128: # e.g. 128 + 50 = 178 (50% Right?)
                                     # Bit 0x80 usually means Right? Or 128 offset.
                                     # Garmin Connect displays "Left 49.8% / Right 50.2%"
                                     # If raw is 0x8000 masked...
                                     # Let's assume fitparse handles it OR it's just raw float.
                                     # For safety, if > 100, try to reduce.
                                     stb = stb - 128 if stb < 256 else stb
                             
                             streams_data.append({
                                 "activity_id": db_act.activity_id,
                                 "timestamp": rec.get('timestamp'),
                                 "heart_rate": safe_int(rec.get('heart_rate')),
                                 "speed": rec.get('speed'),
                                 "cadence": safe_int(rec.get('cadence')),
                                 "altitude": rec.get('altitude'),
                                 "power": safe_int(rec.get('power')),
                                 "grade": rec.get('grade'),
                                 "latitude": rec.get('latitude'),
                                 "longitude": rec.get('longitude'),
                                 "vertical_oscillation": rec.get('vertical_oscillation'),
                                 "stance_time": rec.get('stance_time'),
                                 "stance_time_balance": stb, 
                                 "step_length": rec.get('step_length')
                             })
                except Exception as e:
                    logger.error(f"Error processing FIT for {db_act.activity_id}: {e}")
                    pass

            if streams_data:
                crud.save_activity_streams_batch(db, db_act.activity_id, streams_data)

        result = {"status": "success", "synced_activities": synced_count, "source": "mock_file" if MOCK_MODE else "garmin_api"}
    except Exception as e:
        logger.error(f"Activity Sync Failed: {e}")
        result = {"status": "partial_error", "error": str(e)}

    # 2. Trigger Background Biometrics
    background_tasks.add_task(sync_garmin_stats_background)
    
    return result

@router.get("/profile")
async def get_user_profile():
    if MOCK_MODE:
        try:
            with open("mock_data/profile.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Mock profile missing: {e}")
            return {}

    try:
        client = get_garmin_client()
        profile_data = {
            "name": client.display_name,
            "weight": 70,
            "restingHr": 50,
            "maxHr": 190,
            "lthr": 170,
            "vo2max": 50,
            "stressScore": 25,
            "email": "Connected via Garmin",
            "hrZones": [100, 120, 140, 160, 180]
        }
        # Simplified profile fetching for stability
        try:
            today = date.today()
            summary = client.get_user_summary(today.isoformat())
            if 'restingHeartRate' in summary:
                profile_data["restingHr"] = summary['restingHeartRate']
        except:
            pass
            
        return profile_data
    except Exception as e:
        logger.error(f"Profil Çekme Hatası: {e}")
        return {}

@router.get("/sleep/{date_str}")
async def get_sleep_by_date(date_str: str, db: Session = Depends(get_db)):
    # 1. Try Mock in Biometrics Mode
    if MOCK_BIOMETRICS:
        import random
        seed = sum(ord(c) for c in date_str)
        random.seed(seed)
        sleep_time = random.randint(21600, 32400) 
        deep = int(sleep_time * random.uniform(0.15, 0.25))
        rem = int(sleep_time * random.uniform(0.20, 0.30))
        awake = random.randint(300, 1800)
        light = sleep_time - deep - rem - awake
        score = random.randint(45, 98)
        return {
            "dailySleepDTO": {
                "id": seed * 100,
                "sleepTimeSeconds": sleep_time,
                "sleepScores": {"overall": {"value": score}},
                "deepSleepSeconds": deep, 
                "lightSleepSeconds": light, 
                "remSleepSeconds": rem, 
                "awakeSleepSeconds": awake
            }
        }
    
    # 2. Try DB only - no API fallback for speed
    try:
        user_id = 1
        clean_date_str = date_str.split('T')[0]
        date_obj = datetime.strptime(clean_date_str, "%Y-%m-%d").date()
        
        log = crud.get_sleep_log(db, user_id, date_obj)
        if log and log.raw_json:
            return {"dailySleepDTO": log.raw_json} 
    except Exception as e:
        logger.warning(f"DB Sleep Read Error: {e}")
    
    return {}  # DB only - sync first!

@router.get("/hrv/{date_str}")
async def get_hrv_by_date(date_str: str, db: Session = Depends(get_db)):
    if MOCK_BIOMETRICS:
        import random
        seed = sum(ord(c) for c in date_str) + 50
        random.seed(seed)
        hrv_val = random.randint(35, 85)
        status = "Balanced" if hrv_val > 50 else "Unbalanced"
        return {"hrvSummary": {"weeklyAvg": hrv_val, "lastNightAvg": hrv_val, "status": status}}

    # Try DB only - no API fallback for speed
    try:
        user_id = 1
        clean_date_str = date_str.split('T')[0]
        date_obj = datetime.strptime(clean_date_str, "%Y-%m-%d").date()
        log = crud.get_hrv_log(db, user_id, date_obj)
        if log and log.raw_json:
            return {"hrvSummary": log.raw_json}
    except Exception as e:
         logger.warning(f"DB HRV Read Error: {e}")
    
    return {}  # DB only - sync first!

@router.get("/stress/{date_str}")
async def get_stress_data(date_str: str, db: Session = Depends(get_db)):
    """Get stress data for a given date - reads from DB first, then Garmin API"""
    clean_date_str = date_str.split('T')[0]
    
    # Try DB first
    try:
        user_id = 1
        date_obj = datetime.strptime(clean_date_str, "%Y-%m-%d").date()
        log = crud.get_stress_log(db, user_id, date_obj)
        if log:
            return {
                "avgStress": log.avg_stress,
                "maxStress": log.max_stress,
                "minStress": log.min_stress,
                "status": log.status
            }
    except Exception as e:
        logger.warning(f"DB Stress Read Error: {e}")
    
    # DB only - sync first!
    return {"avgStress": None, "maxStress": None, "status": "Unknown"}

# --- NEW DB-BACKED PRECIS ENDPOINTS ---

@router.get("/activities")
async def get_recent_activities(limit: int = 50, db: Session = Depends(get_db)):
    """
    Reads activities from Database.
    If empty, triggers auto-sync.
    """
    db_activities = crud.get_activities(db, limit)
    
    if not db_activities:
        logger.info("DB empty, triggering auto-sync...")
        # We can't await sync_all easily here because of background tasks and dependency structure
        # Just call inner logic or return empty and let frontend trigger sync?
        # Better: just return empty list to avoid blocking, frontend can handle empty state or user presses Sync.
        # But user wants "Seamless".
        # Let's try to call crud manually if empty? Or just return [] for now.
        return []

    result = []
    for db_act in db_activities:
        meta = db_act.metadata_blob or {}
        act_dict = {
            "activityId": db_act.activity_id,
            "activityName": db_act.activity_name,
            "startTimeLocal": db_act.start_time_local.isoformat() if db_act.start_time_local else None,
            "activityType": db_act.activity_type,
            "distance": db_act.distance,
            "duration": db_act.duration,
            "elapsedDuration": db_act.elapsed_duration,
            "averageHeartRate": db_act.average_hr,
            "calories": db_act.calories,
            "elevationGain": db_act.elevation_gain,
            "avgSpeed": db_act.avg_speed,
            "shoe": meta.get("shoe"),
            "workoutType": meta.get("workoutType"),
            # Weather fields
            "weather_temp": db_act.weather_temp,
            "weather_humidity": db_act.weather_humidity,
            "weather_condition": db_act.weather_condition,
            "weather_wind_speed": db_act.weather_wind_speed,
        }
        raw = db_act.raw_json or {}
        act_dict["perceivedEffort"] = raw.get('userEvaluation', {}).get('perceivedEffort')
        act_dict["feeling"] = raw.get('userEvaluation', {}).get('feeling')
        result.append(act_dict)
            
    return result

@router.get("/activity/{activity_id}")
async def get_activity_details(activity_id: int, db: Session = Depends(get_db)):
    act = crud.get_activity(db, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # 1. Fetch Streams from DB
    streams = db.query(models.ActivityStream).filter(models.ActivityStream.activity_id == activity_id).order_by(models.ActivityStream.timestamp.asc()).all()
    
    # Helper to prevent JSON NaN errors
    def safe_float(val):
        if val is None: return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f): return None
            return f
        except:
            return None

    stream_data = []
    for s in streams:
        # Calculate ratio safely
        v_ratio = None
        if s.vertical_oscillation and s.step_length and s.step_length > 0:
             v_ratio = (s.vertical_oscillation / s.step_length * 100)
             
        stream_data.append({
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "heart_rate": s.heart_rate,
            "speed": safe_float(s.speed),
            "cadence": s.cadence,
            "altitude": safe_float(s.altitude),
            "power": s.power,
            "grade": safe_float(s.grade),
            "latitude": safe_float(s.latitude),
            "longitude": safe_float(s.longitude),
            # Running Dynamics
            "vertical_oscillation": safe_float(s.vertical_oscillation),
            "stance_time": safe_float(s.stance_time),
            "stance_time_balance": safe_float(s.stance_time_balance), # New
            "step_length": safe_float(s.step_length),
            "vertical_ratio": safe_float(v_ratio)
        })
    
    # Construct Response
    response = {
        "activityId": act.activity_id,
        "data": stream_data,
        "metadata": act.metadata_blob,
        "geoPolylineDTO": (act.raw_json or {}).get('geoPolylineDTO'),
        "nativeLaps": (act.raw_json or {}).get('native_laps'),
        "summary": {
            "name": act.activity_name,
            "avgHr": act.average_hr,
            "maxHr": act.max_hr,
            "distance": act.distance,
            "duration": act.duration,
            "averageHeartRate": act.average_hr,
            "calories": act.calories,
            "elevationGain": act.elevation_gain,
            "avgSpeed": act.avg_speed,
            "rpe": (act.raw_json or {}).get('userEvaluation', {}).get('perceivedEffort') or act.rpe, # Prioritize Cloud User Eval (e.g. 7) over FIT (e.g. 10/193)
            "vo2Max": act.vo2_max,
            "recoveryTime": act.recovery_time
        }
    }
    
    return response

@router.post("/activity/{activity_id}/metadata")
async def save_activity_metadata(activity_id: int, metadata: dict, db: Session = Depends(get_db)):
    try:
        updated = crud.update_activity_metadata(db, activity_id, metadata)
        if not updated:
             raise HTTPException(status_code=404, detail="Activity not found")
        return {"status": "success", "metadata": updated.metadata_blob}
    except Exception as e:
        logger.error(f"Metadata save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/{activity_id}/metadata")
async def get_activity_metadata(activity_id: int, db: Session = Depends(get_db)):
    act = crud.get_activity(db, activity_id)
    if not act:
         raise HTTPException(status_code=404, detail="Activity not found")
    return act.metadata_blob or {}


# --- Shoe Management Endpoints ---

@router.get("/shoes")
async def get_shoes(db: Session = Depends(get_db)):
    """Get all active shoes for user"""
    user_id = 1  # TODO: Get from auth
    shoes = crud.get_shoes(db, user_id)
    return [
        {
            "id": s.id,
            "name": s.name,
            "brand": s.brand,
            "initialDistance": s.initial_distance,
            "totalDistance": crud.get_shoe_total_distance(db, s.id),
            "isActive": s.is_active == 1,
            "createdAt": s.created_at.isoformat() if s.created_at else None
        }
        for s in shoes
    ]


@router.post("/shoes")
async def create_shoe(shoe_data: dict, db: Session = Depends(get_db)):
    """Create a new shoe"""
    user_id = 1  # TODO: Get from auth
    shoe = crud.create_shoe(
        db, 
        user_id,
        name=shoe_data.get("name"),
        brand=shoe_data.get("brand"),
        initial_distance=shoe_data.get("initialDistance", 0.0)
    )
    return {
        "id": shoe.id,
        "name": shoe.name,
        "brand": shoe.brand,
        "initialDistance": shoe.initial_distance,
        "totalDistance": shoe.initial_distance,
        "isActive": True
    }


@router.put("/shoes/{shoe_id}")
async def update_shoe(shoe_id: int, data: dict, db: Session = Depends(get_db)):
    """Update shoe details"""
    shoe = crud.update_shoe(
        db, shoe_id,
        name=data.get("name"),
        brand=data.get("brand"),
        initial_distance=data.get("initialDistance"),
        is_active=1 if data.get("isActive", True) else 0
    )
    if not shoe:
        raise HTTPException(status_code=404, detail="Shoe not found")
    return {"status": "success", "id": shoe_id}


@router.delete("/shoes/{shoe_id}")
async def delete_shoe(shoe_id: int, db: Session = Depends(get_db)):
    """Retire a shoe (soft delete)"""
    shoe = crud.delete_shoe(db, shoe_id)
    if not shoe:
        raise HTTPException(status_code=404, detail="Shoe not found")
    return {"status": "retired", "id": shoe_id}


@router.post("/activity/{activity_id}/shoe")
async def set_activity_shoe(activity_id: int, data: dict, db: Session = Depends(get_db)):
    """Assign a shoe to an activity"""
    shoe_id = data.get("shoeId")
    if shoe_id is None:
        raise HTTPException(status_code=400, detail="shoeId required")
    
    activity = crud.set_activity_shoe(db, activity_id, shoe_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {"status": "success", "activityId": activity_id, "shoeId": shoe_id}


@router.get("/activity/{activity_id}/shoe")
async def get_activity_shoe(activity_id: int, db: Session = Depends(get_db)):
    """Get the shoe assigned to an activity"""
    act = crud.get_activity(db, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if act.shoe_id:
        shoe = crud.get_shoe(db, act.shoe_id)
        if shoe:
            return {
                "id": shoe.id,
                "name": shoe.name,
                "brand": shoe.brand,
                "totalDistance": crud.get_shoe_total_distance(db, shoe.id)
            }
    return None


# --- Training Load Endpoints ---

@router.get("/training-load")
async def get_training_load(db: Session = Depends(get_db)):
    """Get current PMC data (CTL/ATL/TSB) and history"""
    user_id = 1  # TODO: Get from auth
    
    # Get user's LTHR from profile
    user = db.query(models.User).filter(models.User.id == user_id).first()
    lthr = 165  # Default
    resting_hr = 45  # Default
    
    # Get all activities for PMC calculation
    activities = db.query(models.Activity).filter(
        models.Activity.user_id == user_id
    ).order_by(models.Activity.start_time_local.asc()).all()
    
    # Convert to dict list
    act_list = [
        {
            'local_start_date': a.local_start_date,
            'start_time_local': a.start_time_local,
            'duration': a.duration,
            'average_hr': a.average_hr,
            'distance': a.distance
        }
        for a in activities
    ]
    
    # Calculate PMC
    pmc = training_load.calculate_pmc(act_list, days=365, lthr=lthr, resting_hr=resting_hr)
    
    return pmc


@router.get("/training-load/context/{activity_id}")
async def get_activity_load_context(activity_id: int, db: Session = Depends(get_db)):
    """Get training load context for a specific activity (CTL/ATL/TSB at that time)"""
    user_id = 1
    
    # Get the target activity
    target_act = crud.get_activity(db, activity_id)
    if not target_act:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity_date = target_act.start_time_local
    lthr = 165
    resting_hr = 45
    
    # Get all activities
    activities = db.query(models.Activity).filter(
        models.Activity.user_id == user_id
    ).order_by(models.Activity.start_time_local.asc()).all()
    
    act_list = [
        {
            'local_start_date': a.local_start_date,
            'start_time_local': a.start_time_local,
            'duration': a.duration,
            'average_hr': a.average_hr,
            'distance': a.distance
        }
        for a in activities
    ]
    
    # Calculate context
    context = training_load.get_recent_load_context(act_list, activity_date, lthr, resting_hr)
    
    # Also add this activity's TSS
    this_tss = training_load.get_activity_tss(
        {'duration': target_act.duration, 'average_hr': target_act.average_hr},
        lthr, resting_hr
    )
    context['activity_tss'] = round(this_tss, 1)
    
    return context


@router.get("/training-load/weekly")
async def get_weekly_training_load(db: Session = Depends(get_db)):
    """Get weekly TSS breakdown by calendar weeks (Mon-Sun) with historical trend"""
    user_id = 1
    lthr = 165
    resting_hr = 45
    
    # Get all activities
    activities = db.query(models.Activity).filter(
        models.Activity.user_id == user_id
    ).order_by(models.Activity.start_time_local.asc()).all()
    
    act_list = [
        {
            'local_start_date': a.local_start_date,
            'start_time_local': a.start_time_local,
            'duration': a.duration,
            'average_hr': a.average_hr,
            'distance': a.distance,
            'elevation_gain': a.elevation_gain
        }
        for a in activities
    ]
    
    return training_load.get_weekly_breakdown(act_list, weeks=52, lthr=lthr, resting_hr=resting_hr)
