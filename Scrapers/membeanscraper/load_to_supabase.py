import json
import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def parse_date(date_str):
    """Parse date string to ISO format for Supabase."""
    if not date_str:
        return None
    try:
        # Parse date like "May 07, 2025" to ISO format
        return datetime.strptime(date_str, "%b %d, %Y").isoformat()
    except ValueError:
        return None

def load_membean_data():
    """Load Membean data from JSON file and insert into Supabase."""
    # Read the JSON file
    with open('data/membean_data_latest.json', 'r') as f:
        data = json.load(f)
    
    # Process each student
    for student_id, student_data in data['students'].items():
        current_data = student_data['current_data']
        reports_data = student_data['tabs_data']['Reports']
        
        # Get current times
        now_utc = datetime.now(tz=ZoneInfo("UTC"))
        now_central = now_utc.astimezone(ZoneInfo("America/Chicago"))
        
        # Prepare the data for Supabase
        student_record = {
            'student_id': student_id,
            'name': student_data['name'],
            'level': current_data['level'],
            'level_sort': current_data['level_sort'],
            'words_seen': current_data['words_seen'],
            'last_trained': parse_date(current_data['last_trained']),
            'goal_met': reports_data['goal_met'],
            'goal_progress': reports_data['goal_progress'],
            'fifteen_min_days': reports_data['fifteen_min_days'],
            'minutes_trained': reports_data['minutes_trained'],
            'accuracy': reports_data['accuracy'],
            'dubious_minutes': reports_data['dubious_minutes'],
            'skipped_words': reports_data['skipped_words'],
            'new_words': reports_data['new_words'],
            'assessment_score': reports_data['assessment_score'],
            'created_at': now_utc.isoformat(),
            'updated_at': now_utc.isoformat(),
            'created_at_central': now_central.isoformat(),
            'updated_at_central': now_central.isoformat()
        }
        
        try:
            # Insert new record
            result = supabase.table('membean_students').insert(student_record).execute()
            print(f"Successfully processed student: {student_data['name']}")
        except Exception as e:
            print(f"Error processing student {student_data['name']}: {str(e)}")

if __name__ == "__main__":
    load_membean_data() 