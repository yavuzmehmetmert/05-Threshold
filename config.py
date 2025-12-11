import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class Settings:
    """
    Uygulama ayarlarını ve çevresel değişkenleri yöneten sınıf.
    """
    # Garmin Kimlik Bilgileri (Unofficial API için)
    GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
    GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
    
    # Webhook/Sync Güvenliği (Opsiyonel)
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

    # Token Saklama Dizini (Garth için)
    TOKEN_DIR = os.path.expanduser("~/.garth")

    @classmethod
    def validate(cls):
        """
        Kritik değişkenlerin yüklendiğini doğrular.
        """
        missing = []
        if not cls.GARMIN_EMAIL:
            missing.append("GARMIN_EMAIL")
        if not cls.GARMIN_PASSWORD:
            missing.append("GARMIN_PASSWORD")
        
        if missing:
            raise ValueError(f"Eksik çevresel değişkenler: {', '.join(missing)}")

# Ayarları doğrula (Import edildiğinde çalışır)
try:
    Settings.validate()
except ValueError as e:
    print(f"UYARI: {e}")

# Global Flags
MOCK_MODE = False
MOCK_BIOMETRICS = False
