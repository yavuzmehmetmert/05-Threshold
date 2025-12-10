from fastapi import APIRouter, HTTPException, BackgroundTasks
import pandas as pd
import fitparse
import os
import tempfile
import logging
import json
from datetime import date
from auth_service import get_garmin_client

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Valid MOCK_MODE location
MOCK_MODE = True

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
                return json.load(f)
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
            return json.loads(df.to_json(orient="records"))
        else:
            raise HTTPException(status_code=404, detail="Aktivite verisi işlenemedi veya boş.")

    except Exception as e:
        logger.error(f"Detay Çekme Hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))
