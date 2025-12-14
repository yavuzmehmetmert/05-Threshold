from database import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE activity_streams ADD COLUMN latitude FLOAT;"))
            conn.execute(text("ALTER TABLE activity_streams ADD COLUMN longitude FLOAT;"))
            conn.commit()
            print("Columns added successfully.")
        except Exception as e:
            print(f"Error (maybe columns exist): {e}")

if __name__ == "__main__":
    add_columns()
