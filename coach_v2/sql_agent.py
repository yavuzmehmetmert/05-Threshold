"""
SQL Agent for AI Coach
========================

Gives the LLM direct knowledge of the database schema and lets it write
SQL queries to answer ANY question about the athlete's data.

This replaces hardcoded query patterns with dynamic SQL generation.
The LLM acts as a data analyst that can:
- Understand the full schema
- Write complex JOINs, GROUP BY, aggregations
- Correlate multiple metrics (weather, HR, VO2max, sleep, HRV)
- Provide fitness-normalized analysis

SAFETY: Uses READ-ONLY operations. No DELETE/UPDATE/INSERT.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging
import re


# =============================================================================
# COMPLETE DATABASE SCHEMA CONTEXT
# =============================================================================

FULL_SCHEMA_CONTEXT = """
# ATHLETE DATABASE SCHEMA

Sen bir SQL uzmanısın. Aşağıdaki veritabanını kullanarak sporcu sorularını cevapla.

## TABLOLAR VE KOLONLAR

### 1. activities (Koşu/Antrenman verileri)
```
activity_id: BigInteger (Garmin ID, unique)
user_id: Integer (FK to users)
activity_name: String (örn: "Kadıköy Koşusu", "Morning Run")
start_time_local: DateTime
local_start_date: Date (YYYY-MM-DD)
activity_type: String (running, trail_running, etc.)

-- Temel Metrikler
distance: Float (METRE cinsinden!)
duration: Float (SANİYE cinsinden!)
elapsed_duration: Float (duraklamalar dahil, saniye)
average_hr: Integer (bpm)
max_hr: Integer (bpm)
calories: Integer
elevation_gain: Float (metre)
avg_speed: Float (m/s)
max_speed: Float (m/s)

-- İleri Metrikler
training_effect: Float (1.0-5.0)
aerobic_te: Float
anaerobic_te: Float
vo2_max: Integer (aktivite sırasında ölçülen VO2max)
recovery_time: Integer (saat)
rpe: Integer (kullanıcının verdiği zorluk puanı, 0-10)

-- Koşu Dinamikleri
avg_power: Integer (watt)
avg_cadence: Integer (spm - adım/dakika)
avg_stride_length: Float (metre)
avg_vertical_oscillation: Float (cm)
avg_ground_contact_time: Float (ms)

-- Hava Durumu
weather_temp: Float (Celsius)
weather_condition: String ("Sunny", "Cloudy", "Rain" vb.)
weather_humidity: Integer (%)
weather_wind_speed: Float (km/h)

-- Ayakkabı
shoe_id: Integer (FK to shoes)
```

### 2. activity_streams (Saniye saniye GPS verileri)
```
activity_id: BigInteger (FK to activities.activity_id)
timestamp: DateTime
heart_rate: Integer
speed: Float (m/s)
cadence: Integer
altitude: Float (METRE - gerçek GPS rakımı!)
power: Integer (watt)
grade: Float (% eğim)
latitude: Float
longitude: Float
vertical_oscillation: Float
stance_time: Float
step_length: Float
```

### 3. sleep_logs (Uyku verileri)
```
user_id: Integer
calendar_date: Date
duration_seconds: Integer
deep_seconds: Integer
light_seconds: Integer
rem_seconds: Integer
awake_seconds: Integer
sleep_score: Integer (0-100)
quality_score: String ("good", "fair", "poor")
```

### 4. hrv_logs (Nabız değişkenliği)
```
user_id: Integer
calendar_date: Date
last_night_avg: Integer (ms)
last_night_5min_high: Integer
baseline_low: Integer
baseline_high: Integer
status: String ("BALANCED", "LOW", "HIGH")
```

### 5. stress_logs (Stres verileri)
```
user_id: Integer
calendar_date: Date
avg_stress: Integer (0-100)
max_stress: Integer
min_stress: Integer
status: String ("Low", "Medium", "High", "Very High")
```

### 6. physiological_logs (Günlük fizyolojik metrikler)
```
user_id: Integer
calendar_date: Date
weight: Float (kg)
resting_hr: Integer (bpm)
max_hr: Integer (bpm)
lactate_threshold_hr: Integer (bpm)
vo2_max: Integer (günlük VO2max değeri)
threshold_pace: Float (min/km)
ftp: Integer (watt)
body_fat_pct: Float
avg_stress: Integer
```

### 7. shoes (Ayakkabılar)
```
id: Integer
user_id: Integer
name: String (örn: "Nike Pegasus 40")
brand: String
initial_distance: Float (km)
is_active: Integer (1=aktif, 0=emekli)
```

## JOIN İLİŞKİLERİ

```sql
-- Aktivite + Uyku (önceki gece)
SELECT a.*, s.sleep_score
FROM activities a
LEFT JOIN sleep_logs s ON a.user_id = s.user_id 
    AND a.local_start_date = s.calendar_date

-- Aktivite + HRV
SELECT a.*, h.last_night_avg as hrv
FROM activities a
LEFT JOIN hrv_logs h ON a.user_id = h.user_id 
    AND a.local_start_date = h.calendar_date

-- Aktivite + Stres
SELECT a.*, st.avg_stress
FROM activities a
LEFT JOIN stress_logs st ON a.user_id = st.user_id 
    AND a.local_start_date = st.calendar_date

-- Aktivite + Günlük Fizyoloji (tarihsel VO2max)
SELECT a.*, p.vo2_max as daily_vo2max
FROM activities a
LEFT JOIN physiological_logs p ON a.user_id = p.user_id 
    AND a.local_start_date = p.calendar_date

-- Aktivite + Ayakkabı
SELECT a.activity_name, sh.name as shoe_name
FROM activities a
LEFT JOIN shoes sh ON a.shoe_id = sh.id
```

## ÖNEMLİ HESAPLAMALAR (PostgreSQL)

```sql
-- Pace hesaplama (min/km)
-- distance METRE, duration SANİYE
(duration / 60.0) / (distance / 1000.0) as pace_min_per_km

-- Saat formatında duration
duration / 3600.0 as hours

-- Çeyrek (quarter) hesaplama - PostgreSQL
EXTRACT(QUARTER FROM local_start_date) as quarter

-- Yıl-Çeyrek - PostgreSQL
TO_CHAR(local_start_date, 'YYYY') || '-Q' || EXTRACT(QUARTER FROM local_start_date) as year_quarter

-- Ay çıkarmak
EXTRACT(MONTH FROM local_start_date) as month

-- Yıl çıkarmak
EXTRACT(YEAR FROM local_start_date) as year
```

## ÖRNEK SORGULAR (PostgreSQL)

### Sıcak hava performansı (VO2max normalized)
```sql
SELECT 
    TO_CHAR(local_start_date, 'YYYY') || '-Q' || EXTRACT(QUARTER FROM local_start_date) as quarter,
    COUNT(*) as run_count,
    AVG(average_hr) as avg_hr,
    AVG(vo2_max) as avg_vo2max,
    AVG(weather_temp) as avg_temp
FROM activities
WHERE user_id = :user_id 
    AND weather_temp > 25
GROUP BY quarter
ORDER BY quarter
LIMIT 100
```

### Uyku kalitesi vs performans korelasyonu
```sql
SELECT 
    CASE WHEN s.sleep_score >= 80 THEN 'İyi Uyku (80+)'
         WHEN s.sleep_score >= 60 THEN 'Orta Uyku (60-79)'
         ELSE 'Kötü Uyku (<60)' END as sleep_category,
    COUNT(*) as run_count,
    AVG(a.average_hr) as avg_hr,
    AVG((a.duration / 60.0) / (a.distance / 1000.0)) as avg_pace
FROM activities a
JOIN sleep_logs s ON a.user_id = s.user_id 
    AND a.local_start_date = s.calendar_date
WHERE a.user_id = :user_id
GROUP BY sleep_category
LIMIT 100
```

### Yüksek rakım analizi (GPS verisinden)
```sql
SELECT 
    a.activity_name,
    a.local_start_date,
    a.average_hr,
    AVG(st.altitude) as avg_altitude,
    MAX(st.altitude) as max_altitude
FROM activities a
JOIN activity_streams st ON a.activity_id = st.activity_id
WHERE a.user_id = :user_id
GROUP BY a.activity_id, a.activity_name, a.local_start_date, a.average_hr
HAVING AVG(st.altitude) > 1000
ORDER BY a.local_start_date DESC
LIMIT 100
```

## KISITLAMALAR
- Sadece SELECT sorguları yazabilirsin
- user_id = :user_id filtresini MUTLAKA kullan
- Sonuçları LIMIT ile sınırla (max 100)
- raw_json kolonlarını kullanma
"""

SQL_AGENT_PROMPT = """
{schema}

# KULLANICI SORUSU
{question}

# TALİMAT
1. Bu soruyu cevaplamak için gerekli SQL sorgusunu yaz
2. Sadece SELECT sorgusu yazabilirsin
3. user_id = :user_id filtresini MUTLAKA ekle
4. LIMIT 100 ile sınırla
5. Sadece SQL döndür, açıklama yazma

SQL:
"""

INTERPRETATION_PROMPT = """
Sen deneyimli bir koşu koçusun (hOCA). Veritabanından çekilen verileri yorumla.

İLETİŞİM TARZI (Tedesco tarzı):
- Düşünceli ve doğrudan konuş. Her cümlen bir amaca hizmet etsin.
- Sakin ama tutkulu ol. Gereksiz heyecan gösterme.
- Sayıları ezberletme, hikayeleştir. Sayının koşucunun hissettiği acı veya başarıyla bağlantısını kur.
- SORU SORMA - Mesajın sonunda soru ekleme.
- Kısa paragraflar kur, 2-3 cümleyi geçmesin.
- Max 1-2 emoji kullan.

ASLA YAPMA:
- Robotik başlıklar ("VERİ ANALİZİ:", "ÖNERİLER:") kullanma.
- "0", "Null", "None" veriyi yorumlama, pas geç.
- Boş övgü yapma, veriye dayanarak kanıtla.
- "Başka sorun var mı?" gibi klişeler kullanma.

# KULLANICI SORUSU
{question}

# SQL SORGUSU
```sql
{sql}
```

# SORGU SONUÇLARI
{results}

# TALİMAT
- Gerçek verilere dayalı cevap ver.
- Korelasyonları belirt (uyku, stres, HRV etkileri).
- 80-120 kelime yeterli, uzatma.
"""


class SQLAgent:
    """SQL Agent that writes and executes dynamic queries."""
    
    def __init__(self, db: Session, llm_client):
        self.db = db
        self.llm = llm_client
    
    def analyze_and_answer(self, user_id: int, question: str) -> Tuple[str, Dict]:
        """
        Main entry: Generate SQL, execute, interpret results.
        
        Returns:
            Tuple of (response text, debug info with step-by-step details)
        """
        debug = {
            "handler": "SQLAgent",
            "steps": []
        }
        
        # ============================================================
        # STEP 1: Generate SQL from natural language
        # ============================================================
        sql_prompt = SQL_AGENT_PROMPT.format(
            schema=FULL_SCHEMA_CONTEXT,
            question=question
        )
        
        debug["steps"].append({
            "step": 1,
            "name": "SQL Generation",
            "description": "LLM'e soru gönderildi, SQL yazması istendi",
            "prompt_sent": sql_prompt[:500] + "..." if len(sql_prompt) > 500 else sql_prompt,
            "prompt_length": len(sql_prompt)
        })
        
        try:
            sql_response = self.llm.generate(sql_prompt, max_tokens=600)
            sql = self._extract_sql(sql_response.text)
            
            debug["steps"][-1]["llm_response"] = sql_response.text[:500] + "..." if len(sql_response.text) > 500 else sql_response.text
            debug["steps"][-1]["extracted_sql"] = sql
            debug["steps"][-1]["status"] = "success"
        except Exception as e:
            debug["steps"][-1]["status"] = "error"
            debug["steps"][-1]["error"] = str(e)
            return "SQL oluşturulamadı.", debug
        
        if not sql:
            debug["steps"][-1]["status"] = "failed"
            return "Bu soruyu SQL'e çevirmekte zorlandım.", debug
        
        # ============================================================
        # STEP 2: Validate SQL (safety check)
        # ============================================================
        is_valid = self._validate_sql(sql)
        
        debug["steps"].append({
            "step": 2,
            "name": "SQL Validation",
            "description": "Güvenlik kontrolü (sadece SELECT, user_id zorunlu)",
            "sql": sql,
            "is_valid": is_valid,
            "status": "success" if is_valid else "rejected"
        })
        
        if not is_valid:
            return "Güvenlik kontrolünden geçemedi.", debug
        
        # ============================================================
        # STEP 3: Execute SQL
        # ============================================================
        debug["steps"].append({
            "step": 3,
            "name": "SQL Execution",
            "description": f"Veritabanında sorgu çalıştırılıyor (user_id={user_id})",
            "sql": sql
        })
        
        try:
            results = self._execute_sql(sql, user_id)
            debug["steps"][-1]["result_count"] = len(results)
            debug["steps"][-1]["sample_results"] = results[:5] if results else []
            debug["steps"][-1]["status"] = "success"
        except Exception as e:
            debug["steps"][-1]["status"] = "error"
            debug["steps"][-1]["error"] = str(e)
            return f"SQL hatası: {str(e)[:100]}", debug
        
        if not results:
            debug["steps"][-1]["status"] = "no_data"
            return "Bu kriterlere uyan veri bulunamadı.", debug
        
        # ============================================================
        # STEP 4: Interpret results with LLM
        # ============================================================
        results_text = json.dumps(results[:20], default=str, indent=2, ensure_ascii=False)
        
        interpretation_prompt = INTERPRETATION_PROMPT.format(
            question=question,
            sql=sql,
            results=results_text
        )
        
        debug["steps"].append({
            "step": 4,
            "name": "Result Interpretation",
            "description": "LLM sonuçları yorumluyor",
            "prompt_sent": interpretation_prompt[:500] + "..." if len(interpretation_prompt) > 500 else interpretation_prompt,
            "data_rows": len(results)
        })
        
        try:
            interpretation_response = self.llm.generate(interpretation_prompt, max_tokens=600)
            final_answer = interpretation_response.text
            
            debug["steps"][-1]["llm_response"] = final_answer[:500] + "..." if len(final_answer) > 500 else final_answer
            debug["steps"][-1]["status"] = "success"
        except Exception as e:
            debug["steps"][-1]["status"] = "error"
            debug["steps"][-1]["error"] = str(e)
            return "Sonuçlar yorumlanamadı.", debug
        
        # Final summary
        debug["final_sql"] = sql
        debug["total_results"] = len(results)
        debug["total_llm_calls"] = 2
        
        return final_answer, debug
    
    def _extract_sql(self, text: str) -> Optional[str]:
        """Extract SQL from LLM response."""
        text = text.strip()
        
        if "```sql" in text:
            text = text.split("```sql")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        return text.strip() if text else None
    
    def _validate_sql(self, sql: str) -> bool:
        """Safety validation - only allow SELECT queries."""
        sql_upper = sql.upper().strip()
        
        if not sql_upper.startswith("SELECT"):
            return False
        
        dangerous = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"]
        for d in dangerous:
            if d in sql_upper:
                return False
        
        if ":user_id" not in sql.lower() and "user_id" not in sql.lower():
            return False
        
        return True
    
    def _execute_sql(self, sql: str, user_id: int) -> List[Dict]:
        """Execute SQL and return results as list of dicts."""
        result = self.db.execute(text(sql), {"user_id": user_id})
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows[:100]]
    
    def get_schema_summary(self) -> str:
        """Return a short schema summary for debugging."""
        return """
Tables: activities, activity_streams, sleep_logs, hrv_logs, stress_logs, physiological_logs, shoes
Key Joins: activities.local_start_date = {health_logs}.calendar_date
Key Metrics: distance (m), duration (s), average_hr, vo2_max, weather_temp, altitude
"""
