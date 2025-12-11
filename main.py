from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth_service import router as auth_router
from ingestion_service import router as ingestion_router

from database import engine
import models

# Veritabanı tablolarını oluştur (Yoksa)
# !!! DİKKAT: Schema değişikliği için Drop All ekliyoruz.
# Canlıya alırken bunu kaldırmalıyız.
# Veritabanı tablolarını oluştur (Yoksa)
# !!! DİKKAT: Drop All kaldırıldı. Artık kalıcı.
models.Base.metadata.create_all(bind=engine)

# FastAPI Uygulamasını Başlat
app = FastAPI(
    title="Garmin Entegrasyon Servisi",
    description="Garmin Connect ile OAuth 1.0a entegrasyonu ve veri alımı sağlayan mikroservis.",
    version="1.0.0"
)

# CORS Ayarları (Frontend bağlantısı için)
# Production'da allow_origins kısmına sadece frontend domainini ekleyin.
origins = [
    "http://localhost",
    "http://localhost:3000",  # React/Next.js varsayılan portu
    "http://localhost:8000",
    "http://localhost:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ları Bağla
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])

@app.get("/")
async def health_check():
    """
    Sistem Sağlık Durumu Kontrolü
    """
    return {
        "status": "healthy",
        "service": "Garmin Integration Service",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
