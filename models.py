from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, JSON, ForeignKey, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    garmin_id = Column(String, unique=True, index=True) # Unique Garmin User ID or email
    email = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Simple profile metrics for caching
    vo2_max_running = Column(Integer, nullable=True)
    resting_hr = Column(Integer, nullable=True)
    
    activities = relationship("Activity", back_populates="user")
    shoes = relationship("Shoe", back_populates="user")


class Shoe(Base):
    __tablename__ = "shoes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    name = Column(String)  # e.g. "Nike Pegasus 40"
    brand = Column(String, nullable=True)
    initial_distance = Column(Float, default=0.0)  # Starting km for used shoes
    is_active = Column(Integer, default=1)  # 1 = active, 0 = retired
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="shoes")
    activities = relationship("Activity", back_populates="shoe")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(BigInteger, unique=True, index=True) # Garmin Activity ID
    
    user_id = Column(Integer, ForeignKey("users.id"))
    
    activity_name = Column(String)
    start_time_local = Column(DateTime)
    local_start_date = Column(Date, index=True) # For easier joins with daily logs
    activity_type = Column(String)    # Activity Metrics
    distance = Column(Float)
    duration = Column(Float)
    elapsed_duration = Column(Float, nullable=True)  # Total time including pauses
    average_hr = Column(Integer)
    max_hr = Column(Integer)
    calories = Column(Integer)
    elevation_gain = Column(Float)
    avg_speed = Column(Float)
    max_speed = Column(Float)
    
    # Advanced Metrics
    training_effect = Column(Float, nullable=True)
    anaerobic_te = Column(Float, nullable=True)
    aerobic_te = Column(Float, nullable=True)
    vo2_max = Column(Integer, nullable=True) # VO2 Max *detected* during this activity
    recovery_time = Column(Integer, nullable=True) # Hours
    rpe = Column(Integer, nullable=True) # Garmin User Evaluation (0-10 or 0-100)
    
    # Power & Dynamics
    avg_power = Column(Integer, nullable=True)
    avg_cadence = Column(Integer, nullable=True)
    avg_stride_length = Column(Float, nullable=True)
    avg_vertical_oscillation = Column(Float, nullable=True)
    avg_ground_contact_time = Column(Float, nullable=True)
    
    # Weather
    weather_temp = Column(Float, nullable=True)
    weather_condition = Column(String, nullable=True)
    weather_humidity = Column(Integer, nullable=True)
    weather_wind_speed = Column(Float, nullable=True)

    # Data
    raw_json = Column(JSON)
    metadata_blob = Column(JSON)
    
    # Shoe Tracking
    shoe_id = Column(Integer, ForeignKey("shoes.id"), nullable=True)
    
    user = relationship("User", back_populates="activities")
    shoe = relationship("Shoe", back_populates="activities")
    # Relations
    streams = relationship("ActivityStream", back_populates="activity", cascade="all, delete-orphan")

class ActivityStream(Base):
    __tablename__ = "activity_streams"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(BigInteger, ForeignKey("activities.activity_id"), index=True)
    
    timestamp = Column(DateTime)
    
    # Metrics
    heart_rate = Column(Integer, nullable=True)
    speed = Column(Float, nullable=True)     # m/s
    cadence = Column(Integer, nullable=True) # rpm
    altitude = Column(Float, nullable=True)  # meters
    power = Column(Integer, nullable=True)   # watts
    grade = Column(Float, nullable=True)     # % slope
    
    # Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Running Dynamics Stream (Optional/Sparse)
    vertical_oscillation = Column(Float, nullable=True)
    stance_time = Column(Float, nullable=True)
    step_length = Column(Float, nullable=True)
    stance_time_balance = Column(Float, nullable=True) # % Left/Right? or 50.1 etc.

    activity = relationship("Activity", back_populates="streams")


class SleepLog(Base):
    __tablename__ = "sleep_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    calendar_date = Column(Date, index=True) # YYYY-MM-DD
    
    duration_seconds = Column(Integer)
    deep_seconds = Column(Integer)
    light_seconds = Column(Integer)
    rem_seconds = Column(Integer)
    awake_seconds = Column(Integer)
    
    sleep_score = Column(Integer, nullable=True)
    quality_score = Column(String, nullable=True) # e.g. "good", "fair"
    
    raw_json = Column(JSON)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'calendar_date', name='uq_sleep_user_date'),
    )


class HRVLog(Base):
    __tablename__ = "hrv_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    calendar_date = Column(Date, index=True)
    
    last_night_avg = Column(Integer)
    last_night_5min_high = Column(Integer, nullable=True)
    
    baseline_low = Column(Integer, nullable=True)
    baseline_high = Column(Integer, nullable=True)
    status = Column(String, nullable=True) # e.g. "BALANCED"
    
    raw_json = Column(JSON)

    __table_args__ = (
        UniqueConstraint('user_id', 'calendar_date', name='uq_hrv_user_date'),
    )


class StressLog(Base):
    __tablename__ = "stress_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    calendar_date = Column(Date, index=True)
    
    avg_stress = Column(Integer)
    max_stress = Column(Integer)
    min_stress = Column(Integer, nullable=True)
    status = Column(String, nullable=True)  # "Low", "Medium", "High", "Very High"
    
    raw_json = Column(JSON)

    __table_args__ = (
        UniqueConstraint('user_id', 'calendar_date', name='uq_stress_user_date'),
    )
