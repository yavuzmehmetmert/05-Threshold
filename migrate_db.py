from database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE activity_streams ADD COLUMN stance_time_balance FLOAT"))
            print("Added stance_time_balance to activity_streams")
        except Exception as e:
            print(f"Error adding stance_time_balance: {e}")

        try:
            conn.execute(text("ALTER TABLE activities ADD COLUMN rpe INTEGER"))
            print("Added rpe to activities")
        except Exception as e:
            print(f"Error adding rpe: {e}")
            
        conn.commit()

if __name__ == "__main__":
    migrate()
