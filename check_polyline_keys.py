from database import SessionLocal
from models import Activity

def check_keys():
    db = SessionLocal()
    try:
        # Find activity with geoPolylineDTO
        activities = db.query(Activity).all()
        for act in activities:
            if act.raw_json and 'geoPolylineDTO' in act.raw_json:
                dto = act.raw_json['geoPolylineDTO']
                if isinstance(dto, dict) and 'polyline' in dto:
                    points = dto['polyline']
                    if points and len(points) > 0:
                        print(f"Activity: {act.activity_name}")
                        print(f"Point Keys: {list(points[0].keys())}")
                        print(f"Sample Point: {points[0]}")
                        return
                    else:
                        print("Polyline empty list.")
                elif isinstance(dto, list) and len(dto) > 0:
                     print(f"DTO is List. Keys: {list(dto[0].keys())}")
                     return
    finally:
        db.close()

if __name__ == "__main__":
    check_keys()
