import fitparse
import sys
import tempfile
import os
from auth_service import get_garmin_client

# Activity ID provided by user context involves 21211964840
ACTIVITY_ID = 21211964840

def inspect_fit():
    try:
        client = get_garmin_client()
        print(f"Downloading activity {ACTIVITY_ID}...")
        zip_data = client.download_activity(ACTIVITY_ID, dl_fmt=client.ActivityDownloadFormat.ORIGINAL)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            tmp_zip.write(zip_data)
            tmp_zip_path = tmp_zip.name
            
        import zipfile
        with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
            fit_filename = zip_ref.namelist()[0]
            zip_ref.extract(fit_filename, path=tempfile.gettempdir())
            fit_path = os.path.join(tempfile.gettempdir(), fit_filename)
            
        print(f"Parsing FIT file: {fit_path}")
        fitfile = fitparse.FitFile(fit_path)
        
        # Get first record to see available fields
        for record in fitfile.get_messages("record"):
            print("\nAvailable Fields in 'record' message:")
            for data in record:
                print(f" - {data.name}: {data.value} (units: {data.units})")
            break # Only need first one
            
        # Clean up
        if os.path.exists(tmp_zip_path):
            os.remove(tmp_zip_path)
        if os.path.exists(fit_path):
            os.remove(fit_path)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_fit()
