from database import SessionLocal
from models import Activity
import crud

db = SessionLocal()
act = crud.get_activities(db, limit=1)[0]
print(f"ID: {act.activity_id}")
print(f"Name: {act.activity_name}")
print(f"RPE Column: {act.rpe}")
print(f"Raw JSON UserEval: {(act.raw_json or {}).get('userEvaluation')}")
