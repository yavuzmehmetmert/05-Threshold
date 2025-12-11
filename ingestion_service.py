from fastapi import APIRouter, HTTPException, BackgroundTasks
import pandas as pd
import fitparse
import os
import tempfile
import logging
import json
from datetime import date, datetime
import requests
from auth_service import get_garmin_client

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Valid MOCK_MODE location
MOCK_MODE = True
MOCK_BIOMETRICS = True # User requested to switch back to Mock mode


router = APIRouter()

def process_fit_file(fit_path: str):
    """
    FIT dosyasını parse eder ve DataFrame'e çevirir.
    """
    try:
        fitfile = fitparse.FitFile(fit_path)
        data_points = []
        
        for record in fitfile.get_messages("record"):
            point = {}
            for record_data in record:
                if record_data.name in [
                    'timestamp', 'heart_rate', 'power', 'cadence', 
                    'speed', 'enhanced_speed', 'distance',
                    'position_lat', 'position_long', 
                    'altitude', 'enhanced_altitude',
                    'vertical_oscillation', 'vertical_ratio', 'step_length', 'stance_time', 'stance_time_balance'
                ]:
                    # Map enhanced fields to standard names
                    if record_data.name == 'enhanced_speed':
                        point['speed'] = record_data.value
                    elif record_data.name == 'enhanced_altitude':
                        point['altitude'] = record_data.value
                    elif record_data.name not in point: 
                         point[record_data.name] = record_data.value
            
            if 'timestamp' in point:
                data_points.append(point)
                
        df = pd.DataFrame(data_points)
        
        if not df.empty and 'speed' in df.columns:
            # Duraklama anlarını (Speed=0) temizle
            df = df[df['speed'] > 0]
            
        return df
    except Exception as e:
        logger.error(f"FIT Parse Hatası: {e}")
        return None

async def sync_garmin_data():
    """
    Garmin'den bugünün verilerini ve son aktiviteyi çeker.
    """
    try:
        logger.info("Garmin senkronizasyonu başlıyor...")
        client = get_garmin_client()
        today = date.today()
        
        # 1. Günlük İstatistikleri Çek (HRV, Body Battery, Uyku)
        try:
            stats = client.get_stats_and_body(today.isoformat())
        except AttributeError:
             # Alternatif metotlar denenebilir
             logger.warning("get_stats_and_body bulunamadı, get_user_summary deneniyor...")
             stats = client.get_user_summary(today.isoformat())
             
        logger.info(f"Günlük İstatistikler Çekildi: {stats.keys() if stats else 'None'}")
        
        # 2. Son Aktiviteleri Çek
        activities = client.get_activities(0, 1) # Son 1 aktivite
        if activities:
            last_activity = activities[0]
            activity_id = last_activity['activityId']
            activity_name = last_activity['activityName']
            logger.info(f"Son Aktivite Bulundu: {activity_name} (ID: {activity_id})")
            
            # 3. Aktivite Dosyasını İndir (.zip olarak gelir)
            zip_data = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.ORIGINAL)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                tmp_zip.write(zip_data)
                tmp_zip_path = tmp_zip.name
                
            # Zip içinden FIT dosyasını çıkar
            import zipfile
            with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                # Genellikle tek bir .fit dosyası vardır
                fit_filename = zip_ref.namelist()[0]
                zip_ref.extract(fit_filename, path=tempfile.gettempdir())
                fit_path = os.path.join(tempfile.gettempdir(), fit_filename)
                
            # 4. FIT Dosyasını İşle
            df = process_fit_file(fit_path)
            if df is not None:
                logger.info(f"Aktivite Verisi İşlendi: {len(df)} satır")
                print(df.head())
                # Veritabanına kaydetme işlemi burada yapılabilir.
            
            # Temizlik
            if os.path.exists(tmp_zip_path):
                os.remove(tmp_zip_path)
            if os.path.exists(fit_path):
                os.remove(fit_path)
                
        else:
            logger.info("Son aktivite bulunamadı.")
            
    except Exception as e:
        logger.error(f"Senkronizasyon Hatası: {e}")

@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """
    Manuel olarak senkronizasyonu tetikler.
    """
    background_tasks.add_task(sync_garmin_data)
    return {"status": "Sync triggered", "message": "Senkronizasyon arka planda başlatıldı."}

@router.get("/profile")
async def get_user_profile():
    if MOCK_MODE:
        try:
            with open("mock_data/profile.json", "r") as f:
                print("Serving MOCK profile")
                return json.load(f)
        except Exception as e:
            print(f"Mock profile missing: {e}")

    # Real implementation follows...
    """
    Garmin'den kullanıcının gerçek profil verilerini çeker.
    """
    try:
        client = get_garmin_client()
        
        # Varsayılan değerler
        profile_data = {
            "name": client.display_name,
            "weight": 70,
            "restingHr": 50,
            "maxHr": 190,
            "lthr": 170,
            "vo2max": 50,
            "stressScore": 25,
            "email": "Connected via Garmin",
            "hrZones": [100, 120, 140, 160, 180] # Default Fallback (Floors z1-z5)
        }

        # 1. Personal Information
        try:
            import garth
            from config import Settings
            
            garth.login(Settings.GARMIN_EMAIL, Settings.GARMIN_PASSWORD)
            
            personal_info = garth.client.connectapi(
                "/userprofile-service/userprofile/personal-information"
            )
            
            if 'biometricProfile' in personal_info:
                bio = personal_info['biometricProfile']
                if 'weight' in bio and bio['weight']:
                    profile_data["weight"] = round(bio['weight'] / 1000, 1)
                if 'lactateThresholdHeartRate' in bio and bio['lactateThresholdHeartRate']:
                    profile_data["lthr"] = int(bio['lactateThresholdHeartRate'])
                if 'vo2Max' in bio and bio['vo2Max']:
                    profile_data["vo2max"] = int(bio['vo2Max'])
            
            if 'email' in personal_info:
                 profile_data["email"] = personal_info['email']

            # 4. Fetch Heart Rate Zones
            try:
                zones_data = garth.client.connectapi("/biometric-service/heartRateZones")
                if zones_data:
                    # Look for DEFAULT sport or first available
                    zone_config = next((z for z in zones_data if z['sport'] == 'DEFAULT'), zones_data[0])
                    
                    profile_data["hrZones"] = [
                        zone_config['zone1Floor'],
                        zone_config['zone2Floor'],
                        zone_config['zone3Floor'],
                        zone_config['zone4Floor'],
                        zone_config['zone5Floor'],
                         # Max is handled separately but good to know
                    ]
                    if 'maxHeartRateUsed' in zone_config:
                         profile_data["maxHr"] = zone_config['maxHeartRateUsed']

            except Exception as e:
                logger.warning(f"Could not extract HR Zones: {e}")

        except Exception as e:
            logger.warning(f"Personal Info çekilemedi: {e}")
            # This is the original catch for personal_info, now also covers VO2Max and HR Zones if they fail within this block.

        # 2. RHR ve Max HR
        try:
            today = date.today()
            summary = client.get_user_summary(today.isoformat())
            if 'restingHeartRate' in summary:
                profile_data["restingHr"] = summary['restingHeartRate']
            if 'maxHeartRate' in summary:
                profile_data["maxHr"] = summary['maxHeartRate']
                
            # 3. Stress Score
            total_stress = 0
            days_with_stress = 0
            from datetime import timedelta
            
            for i in range(7):
                d = (today - timedelta(days=i)).isoformat()
                try:
                    s = client.get_user_summary(d)
                    if 'averageStressLevel' in s and s['averageStressLevel'] is not None:
                        total_stress += s['averageStressLevel']
                        days_with_stress += 1
                except:
                    pass
            
            if days_with_stress > 0:
                profile_data["stressScore"] = int(total_stress / days_with_stress)
                
        except Exception as e:
            logger.warning(f"Summary verisi çekilemedi: {e}")

        return profile_data

    except Exception as e:
        logger.error(f"Profil Çekme Hatası: {e}")
        return {
            "name": "Runner",
            "weight": 70,
            "restingHr": 50,
            "maxHr": 190,
            "lthr": 170
        }

@router.get("/sleep/{date_str}")
async def get_sleep_by_date(date_str: str):
    """
    Belirli bir tarihteki uyku verisini çeker.
    Format: YYYY-MM-DD
    """
    if MOCK_BIOMETRICS:
        # Generate deterministic mock data based on date hash
        import random
        # Seed random with date string ASCII sum to get consistent results for same date
        seed = sum(ord(c) for c in date_str)
        random.seed(seed)
        
        # Randomize Sleep Time (6h - 9h range)
        sleep_time = random.randint(21600, 32400) 
        
        # Calculate stages roughly
        deep = int(sleep_time * random.uniform(0.15, 0.25))
        rem = int(sleep_time * random.uniform(0.20, 0.30))
        awake = random.randint(300, 1800)
        light = sleep_time - deep - rem - awake
        
        score = random.randint(45, 98)
        
        return {
            "dailySleepDTO": {
                "id": seed * 100,
                "userProfileId": 12345,
                "calendarDate": date_str,
                "sleepTimeSeconds": sleep_time,
                "napTimeSeconds": 0,
                "sleepScores": {
                    "overall": {
                        "value": score,
                        "qualifierKey": "EXCELLENT" if score > 90 else "GOOD" if score > 80 else "FAIR" if score > 60 else "POOR"
                    }
                },
                "deepSleepSeconds": deep, 
                "lightSleepSeconds": light, 
                "remSleepSeconds": rem, 
                "awakeSleepSeconds": awake, 
                "unmeasurableSleepSeconds": 0
            }
        }

    try:
        client = get_garmin_client()
        # Garmin API expects YYYY-MM-DD
        sleep_data = client.get_sleep_data(date_str)
        return sleep_data
    except Exception as e:
        logger.error(f"Uyku Verisi Çekme Hatası ({date_str}): {e}")
        return {}

@router.get("/hrv/{date_str}")
async def get_hrv_by_date(date_str: str):
    """
    Belirli bir tarihteki HRV (gece) verisini çeker.
    """
    if MOCK_BIOMETRICS:
        import random
        seed = sum(ord(c) for c in date_str) + 50 # Diff seed from sleep
        random.seed(seed)
        hrv_val = random.randint(35, 85)
        status = "Balanced" if hrv_val > 50 else "Unbalanced" if hrv_val > 40 else "Low"
        return {
            "hrvSummary": {
                "weeklyAvg": hrv_val,
                "lastNightAvg": hrv_val,
                "status": status
            }
        }

    try:
        client = get_garmin_client()
        logger.info(f"Fetching HRV for {date_str}...")
        
        # DEBUG: Log available methods
        # with open("debug_backend.log", "a") as f:
        #    f.write(f"Methods: {dir(client)}\n")

        try:
             # Try main method
             hrv_data = client.get_hrv_data(date_str)
             logger.info(f"HRV Data keys: {hrv_data.keys() if hrv_data else 'None'}")
             return hrv_data
        except AttributeError:
             logger.warning("get_hrv_data not found in client.")
             # Fallback
             try:
                stats = client.get_user_summary(date_str)
                logger.info("Fetched user summary as fallback.")
                # Map summary to expected structure if possible
                return stats
             except Exception as e2:
                 logger.error(f"Fallback summary failed: {e2}")
                 raise e2

    except Exception as e:
        logger.error(f"HRV Çekme Hatası ({date_str}): {e}")
        return {}

@router.get("/activities")
async def get_recent_activities(limit: int = 50):
    if MOCK_MODE:
        try:
            with open("mock_data/activities.json", "r") as f:
                print("Serving MOCK activities")
                return json.load(f)
        except Exception as e:
            print(f"Mock activities missing: {e}")

    """
    Son aktiviteleri çeker.
    """
    try:
        client = get_garmin_client()
        activities = client.get_activities(0, limit)
        
        processed_activities = []
        for act in activities:
            processed_activities.append({
                "activityId": act['activityId'],
                "activityName": act['activityName'],
                "startTimeLocal": act['startTimeLocal'],
                "activityType": act['activityType']['typeKey'],
                "distance": act['distance'],
                "duration": act['duration'],
                "averageHeartRate": act.get('averageHR'),
                "calories": act.get('calories'),
                "elevationGain": act.get('totalElevationGain'),
                "avgSpeed": act.get('averageSpeed')
            })
            
        return processed_activities
    except Exception as e:
        logger.error(f"Aktivite Çekme Hatası: {e}")
        return []

@router.get("/activity/{activity_id}")
async def get_activity_details(activity_id: str):
    if MOCK_MODE:
        # Try specific mock first
        mock_file = f"mock_data/activity_{activity_id}.json"
        
        # Fallback to first available mock if specific one missing? 
        # Or better: check list of mocks.
        # User said "son 3 gunluk". 
        if not os.path.exists(mock_file):
            print(f"Specific mock {mock_file} not found. Trying fallback to first captured activity.")
            # Find any mock activity
            for f_name in os.listdir("mock_data"):
                if f_name.startswith("activity_") and f_name.endswith(".json"):
                    mock_file = f"mock_data/{f_name}"
                    break
        
        try:
            with open(mock_file, "r") as f:
                print(f"Serving MOCK activity details from {mock_file}")
                mock_data = json.load(f)
                
                # --- MOCK ELEVATION INJECTION ---
                # User complaint: "Elevation gain wrong/0". Mock data is too flat.
                # Inject distinct hills to verify calculation.
                import math
                base_alt = 10.0
                for i, record in enumerate(mock_data):
                    if isinstance(record, dict):
                        # Create 3 hills over the activity duration (approx sine wave)
                        # Use index as proxy for time/dist
                        hill_factor = math.sin(i / len(mock_data) * 3 * math.pi) 
                        # Amplitude 30m, shifted up so min is roughly 0 relative to base
                        # hill_factor goes -1 to 1. (hill_factor + 1) goes 0 to 2. * 15 = 0 to 30.
                        altitude_offset = (hill_factor + 1) * 15 
                        
                        # Add some random noise
                        noise = (i % 5) * 0.2
                        
                        record['altitude'] = base_alt + altitude_offset + noise
                
                # --- WEATHER FOR MOCK DATA ---
                # Scan for first valid GPS point
                lat, lon, ts = None, None, None
                for record in mock_data:
                    if isinstance(record, dict) and 'position_lat' in record and 'position_long' in record and record['position_lat'] is not None:
                        lat = record['position_lat']
                        lon = record['position_long']
                        ts = record.get('timestamp')
                        break
                
                if lat and lon and ts:
                    logger.info(f"[MOCK WEATHER] Found GPS: lat={lat}, lon={lon}, ts={ts}")
                    weather_data = fetch_weather_history(lat, lon, ts)
                    logger.info(f"[MOCK WEATHER] Result: {weather_data}")
                    if weather_data:
                        return {
                            "data": mock_data,
                            "weather": weather_data
                        }
                
                return mock_data
        except Exception as e:
            print(f"Mock activity missing: {e}")

    """
    Belirli bir aktivitenin detaylı verilerini (FIT dosyasından) çeker.
    """
    try:
        client = get_garmin_client()
        
        # 1. Aktivite Dosyasını İndir
        logger.info(f"Aktivite İndiriliyor: {activity_id}")
        zip_data = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.ORIGINAL)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            tmp_zip.write(zip_data)
            tmp_zip_path = tmp_zip.name
            
        # 2. Zip içinden FIT dosyasını çıkar
        import zipfile
        with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
            fit_filename = zip_ref.namelist()[0]
            zip_ref.extract(fit_filename, path=tempfile.gettempdir())
            fit_path = os.path.join(tempfile.gettempdir(), fit_filename)
            
        # 3. FIT Dosyasını İşle
        df = process_fit_file(fit_path)
        
        # Temizlik
        if os.path.exists(tmp_zip_path):
            os.remove(tmp_zip_path)
        if os.path.exists(fit_path):
            os.remove(fit_path)
            
        if df is not None and not df.empty:
            # Timestamp'i string'e çevir (JSON serializable olması için)
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].astype(str)
                
            # Semicircles to Degrees conversion for GPS
            # Garmin uses semicircles: degrees = semicircles * (180 / 2^31)
            if 'position_lat' in df.columns and 'position_long' in df.columns:
                factor = 180 / (2**31)
                # Ensure numeric types before calculation
                df['position_lat'] = pd.to_numeric(df['position_lat'], errors='coerce')
                df['position_long'] = pd.to_numeric(df['position_long'], errors='coerce')
                
                df['position_lat'] = df['position_lat'] * factor
                df['position_long'] = df['position_long'] * factor
            
            # Use json.loads(df.to_json()) to handle NaN/Inf/None robustly
            # This converts NaN/Inf to null, which is valid JSON
            activity_data = json.loads(df.to_json(orient="records"))
            
            # --- WEATHER INTEGRATION ---
            # Try to get Lat/Lon and Time from the first valid point containing them
            try:
                lat = None
                lon = None
                ts = None
                
                # Scan for first valid valid GPS point
                for record in activity_data:
                    if 'position_lat' in record and 'position_long' in record and record['position_lat'] is not None:
                        lat = record['position_lat']
                        lon = record['position_long']
                        ts = record.get('timestamp')
                        break
                
                if lat and lon and ts:
                    logger.info(f"[WEATHER DEBUG] Found GPS: lat={lat}, lon={lon}, ts={ts}")
                    weather_data = fetch_weather_history(lat, lon, ts)
                    logger.info(f"[WEATHER DEBUG] Result: {weather_data}")
                    if weather_data:
                        logger.info(f"Weather fetched: {weather_data}")
                        # Inject into the FIRST record or as a separate metadata field?
                        # Frontend expects `activity.weather` on the main object.
                        # BUT `get_activity_details` returns ARRAY of records (FIT data).
                        # Frontend logic: ActivityDetailScreen uses `activity` passed from Calendar.
                        # Wait, `get_activity_details` (this endpoint) returns the TIME SERIES (charts).
                        # The HEADER info comes from `useDashboardStore` -> `activities`.
                        # SO WE NEED TO UPDATE THE `activities` LIST in `/activities` endpoint too?
                        # OR: Update dashboard store to fetch detailed weather when opening screen?
                        
                        # Current Logic:
                        # CalendarScreen -> fetches `/activities` -> populates Store.
                        # ActivityDetailScreen -> uses `route.params.activity` (from Store).
                        # It THEN fetches `/activity/:id` for Charts.
                        
                        # ISSUE: The Weather Strip is in Header. Header uses `activity` object 
                        # which is passed from navigation params (from Store list).
                        # If I add weather in `/activity/:id` (Details), I must update the 
                        # Frontend to look for it in the DETAILS response, OR update the `/activities` list response.
                        
                        # Updating `/activities` (List) to fetch weather for 50 items is too slow/expensive.
                        
                        # SOLUTION: Include weather in THIS response (`/activity/:id`), and 
                        # update Frontend `ActivityDetailScreen` to merge this weather data 
                        # into the existing `activity` state or simple `weather` state.
                        
                        return {
                            "data": activity_data,
                            "weather": weather_data
                        }
            except Exception as w_err:
                logger.warning(f"Weather processing failed: {w_err}")

            return activity_data
        else:
            raise HTTPException(status_code=404, detail="Aktivite verisi işlenemedi veya boş.")

    except Exception as e:
        logger.error(f"Detay Çekme Hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def fetch_weather_history(lat, lon, timestamp_str):
    """
    Open-Meteo Archive API to fetch historical weather.
    timestamp_str example: "2024-10-18 07:00:00"
    """
    try:
        # Parse timestamp
        # FIT timestamp might differ slightly, ensure ISO format YYYY-MM-DD
        dt = pd.to_datetime(timestamp_str)
        date_str = dt.strftime("%Y-%m-%d")
        hour_str = dt.strftime("%H")
        
        # Use Forecast API which covers recent past (up to 90 days?) better than Archive (5 day lag)
        # For very old data, Archive is better, but typical usage is recent runs.
        # api.open-meteo.com/v1/forecast handles both future and recent past if dates are provided.
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": date_str,
            "end_date": date_str,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        }
        
        logger.info(f"[WEATHER API] Calling Open-Meteo: {url} params={params}")
        response = requests.get(url, params=params)
        logger.info(f"[WEATHER API] Response status: {response.status_code}")
        data = response.json()
        logger.info(f"[WEATHER API] Data keys: {data.keys() if isinstance(data, dict) else 'not dict'}")
        
        if "hourly" in data:
            # Find index for the specific hour
            # The API returns 24 hours for the day.
            idx = int(hour_str)
            
            temp = data["hourly"]["temperature_2m"][idx]
            humid = data["hourly"]["relative_humidity_2m"][idx]
            wind = data["hourly"]["wind_speed_10m"][idx]
            code = data["hourly"]["weather_code"][idx]
            
            # Map code to string
            condition = "Unknown"
            if code == 0: condition = "Clear"
            elif code in [1, 2, 3]: condition = "Cloudy"
            elif code in [45, 48]: condition = "Foggy"
            elif code in [51, 53, 55, 61, 63, 65]: condition = "Rainy"
            elif code in [71, 73, 75]: condition = "Snowy"
            
            # AQI is not provided by Open-Meteo Archive Free easily, use mock/default or separate API
            # For now default reasonable AQI
            aqi = 25 
            
            # Elevation from API response
            elevation = data.get("elevation", 0)
            
            return {
                "temp": temp,
                "humidity": humid,
                "windSpeed": wind,
                "aqi": aqi,
                "condition": condition,
                "elevation": elevation
            }
            
    except Exception as e:
        logger.error(f"Weather Fetch Error: {e}")
        return None
