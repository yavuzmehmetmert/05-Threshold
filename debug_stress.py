from auth_service import get_garmin_client
from datetime import date, timedelta
import json

def debug_stress():
    try:
        print("Connecting to Garmin...")
        client = get_garmin_client()
        today = date.today()
        
        print(f"Fetching stress data for last 7 days...")
        
        # Garmin Connect usually provides stress in daily summary or specific stress endpoint
        # Let's try get_user_summary for the last 7 days to see if 'averageStressLevel' is there
        
        for i in range(7):
            d = (today - timedelta(days=i)).isoformat()
            try:
                summary = client.get_user_summary(d)
                print(f"\n--- {d} ---")
                if 'averageStressLevel' in summary:
                    print(f"Avg Stress: {summary['averageStressLevel']}")
                else:
                    print("No stress data in summary.")
                    # Let's print keys to see if it's named differently
                    # print(summary.keys()) 
            except Exception as e:
                print(f"Error for {d}: {e}")

    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    debug_stress()
