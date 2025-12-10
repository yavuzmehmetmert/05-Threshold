from fastapi import APIRouter, HTTPException
from garminconnect import Garmin, GarminConnectAuthenticationError
import logging
import os
from config import Settings
import garth

# Logger yapılandırması
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def get_garmin_client():
    """
    Garmin istemcisini başlatır ve oturum açar.
    Token'ları ~/.garth dizininde saklar/okur.
    """
    try:
        # Garth varsayılan olarak ~/.garth dizinini kullanır
        # garth.configure(repo=Settings.TOKEN_DIR) # Hata verdiği için kaldırıldı
        
        client = Garmin(Settings.GARMIN_EMAIL, Settings.GARMIN_PASSWORD)
        
        try:
            # Önce kayıtlı session ile girmeyi dene
            client.login()
        except (FileNotFoundError, GarminConnectAuthenticationError, Exception):
            # Session yoksa veya geçersizse, tekrar login ol (Bu işlem MFA sorabilir!)
            # MFA durumunda terminalden input bekler (garminconnect kütüphanesi özelliği)
            # Production ortamında bu input'u API üzerinden almak zordur, 
            # bu yüzden ilk login'in terminalden yapılması önerilir.
            logger.info("Session bulunamadı veya geçersiz, yeniden giriş yapılıyor...")
            client.login()
            
        return client
        
    except Exception as e:
        logger.error(f"Garmin Login Hatası: {e}")
        # MFA hatası veya yanlış şifre
        raise HTTPException(status_code=401, detail=f"Garmin Giriş Hatası: {str(e)}")

@router.get("/login-check")
async def login_check():
    """
    Sistemin Garmin'e bağlanıp bağlanamadığını test eder.
    """
    try:
        client = get_garmin_client()
        return {"status": "connected", "display_name": client.display_name}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
