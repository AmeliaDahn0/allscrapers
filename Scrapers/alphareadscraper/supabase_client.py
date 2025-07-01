import os
from supabase import create_client, Client
from datetime import datetime
import re

# Initialize Supabase client lazily
_supabase_client = None

def get_supabase_client():
    """Get or create Supabase client, handling missing environment variables"""
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("Warning: Supabase credentials not found. Database operations will be skipped.")
            return None
            
        try:
            _supabase_client = create_client(
                supabase_url=supabase_url,
                supabase_key=supabase_key
            )
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            return None
    
    return _supabase_client

def parse_time_to_minutes(time_str):
    """Convert time string (e.g., '8h 38m') to minutes"""
    if not time_str or time_str == '0m':
        return 0
    
    hours = 0
    minutes = 0
    
    # Extract hours
    h_match = re.search(r'(\d+)h', time_str)
    if h_match:
        hours = int(h_match.group(1))
    
    # Extract minutes
    m_match = re.search(r'(\d+)m', time_str)
    if m_match:
        minutes = int(m_match.group(1))
    
    return (hours * 60) + minutes

def parse_percentage(percentage_str):
    """Convert percentage string (e.g., '65.23%') to float"""
    if not percentage_str or percentage_str == '0%':
        return 0.0
    return float(percentage_str.strip('%'))

def parse_last_active(last_active_str):
    """Convert last active string to datetime"""
    if not last_active_str:
        return None
    
    # Get current year
    current_year = datetime.now().year
    
    # Parse the date (e.g., "May 10" or "Jun 3")
    try:
        date_obj = datetime.strptime(f"{last_active_str} {current_year}", "%b %d %Y")
        return date_obj.isoformat()
    except ValueError:
        return None

def upsert_student_data(student_data):
    """Insert new student data row to Supabase"""
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        if supabase is None:
            print("Skipping Supabase upload - client not available")
            return None
        
        # Transform the data to match the Supabase schema
        transformed_data = {
            'student_id': student_data['user_powerpath_id'] or student_data['email'],
            'name': student_data['email'].split('@')[0].replace('.', ' ').title(),
            'level': student_data['reading_level'],
            'progress': student_data['average_score'],
            'last_activity': parse_last_active(student_data['last_active']),
            'words_read': None,  # Not available in current data
            'accuracy': student_data['success_rate'],
            'reading_time': parse_time_to_minutes(student_data['time_reading']),
            'created_at': datetime.now().isoformat(),  # Add timestamp for when this record was created
            'scrape_date': datetime.now().date().isoformat()  # Add date of scrape
        }
        
        # Always insert new row
        result = supabase.table('alpharead_students').insert(
            transformed_data
        ).execute()
        
        return result
    except Exception as e:
        print(f"Error inserting student data: {e}")
        return None 