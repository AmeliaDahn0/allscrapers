import asyncio
from playwright.async_api import async_playwright
from decouple import config
import os
import csv
from typing import List, Dict
import json
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from urllib.parse import quote

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

async def login_to_membean(page):
    """Login to Membean using credentials from environment variables"""
    try:
        await page.goto('https://membean.com/login')
        await page.wait_for_load_state('networkidle')
        
        # Get credentials from environment variables
        username = config('MEMBEAN_USERNAME')
        password = config('MEMBEAN_PASSWORD')
        
        # Fill in login credentials
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        
        # Click login button
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')
        
        # Wait for the dashboard to load and find the SAT Blitz class
        try:
            # Wait for the class element to be visible
            sat_blitz_link = await page.wait_for_selector('a.js-tclass-name[data-id="345817"]', timeout=10000)
            if sat_blitz_link:
                await sat_blitz_link.click()
                # Wait for the class page to load
                await page.wait_for_load_state('networkidle')
                print("Successfully navigated to SAT Blitz class")
                return True
            else:
                print("Could not find SAT Blitz class link")
                return False
        except Exception as e:
            print(f"Error finding or clicking SAT Blitz class: {e}")
            return False
            
    except Exception as e:
        print(f"Login failed: {e}")
        return False

async def scrape_single_day(page, target_date):
    """Scrape data for a single day by navigating directly to the URL with date parameters"""
    try:
        print(f"Scraping data for {target_date.strftime('%Y-%m-%d')}")
        
        # Format dates for URL parameters (UTC timezone)
        # Membean expects start_date at 05:00:00 UTC and end_date at 04:59:59 UTC next day
        start_datetime = target_date.replace(hour=5, minute=0, second=0, microsecond=0)
        end_datetime = (target_date + timedelta(days=1)).replace(hour=4, minute=59, second=59, microsecond=999000)
        
        # Format for URL encoding
        start_iso = start_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end_iso = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # URL encode the dates
        start_encoded = quote(start_iso)
        end_encoded = quote(end_iso)
        
        # Navigate directly to the reports URL with date parameters
        reports_url = f"https://membean.com/tclasses/345817?start_date={start_encoded}&end_date={end_encoded}#reports"
        print(f"Navigating to: {reports_url}")
        
        await page.goto(reports_url)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(3000)  # Give extra time for data to load
        
        # Wait for the reports table
        print("Looking for reports table...")
        try:
            await page.wait_for_selector('table#report-table', timeout=15000)
            print("✓ Reports table found!")
        except:
            print("Reports table not found")
            return False
        
        # Verify we're on the correct date
        try:
            # Look for date display on page
            date_elements = await page.query_selector_all('.date-display, .report-date, span:has-text("2025")')
            for elem in date_elements:
                date_text = await elem.text_content()
                if date_text and target_date.strftime('%b') in date_text:
                    print(f"✓ Confirmed date on page: {date_text}")
                    break
        except:
            pass
        
        # Extract student data
        students_data = await extract_student_data(page)
        
        if students_data:
            print(f"Found data for {len(students_data)} students on {target_date.strftime('%Y-%m-%d')}")
            
            # Show sample data for verification
            print(f"Sample data for {target_date.strftime('%Y-%m-%d')}:")
            for i, student in enumerate(students_data[:3]):
                print(f"  {student['name']}: {student['minutes_trained']} min, {student['fifteen_min_days']} days, {student['new_words']} new words")
            
            # Save to Supabase
            await save_to_supabase(students_data, target_date)
            return True
        else:
            print(f"No student data found for {target_date.strftime('%Y-%m-%d')}")
            return False
            
    except Exception as e:
        print(f"Error scraping {target_date.strftime('%Y-%m-%d')}: {e}")
        return False

async def extract_student_data(page):
    """Extract data from the training report table"""
    students_data = []
    
    try:
        # Wait for the reports table to be visible (same as regular scraper)
        table = await page.wait_for_selector('table#report-table', timeout=10000)
        if not table:
            print("Could not find reports table")
            return students_data
        
        # Get all student rows from tbody (same as regular scraper)
        rows = await page.query_selector_all('table#report-table tbody tr')
        print(f"Found {len(rows)} rows in table")
        
        for row in rows:
            try:
                # Get student ID from the row ID (similar to membean_scraper.py)
                row_id = await row.get_attribute('id')
                student_id = None
                
                if row_id:
                    # Handle different possible row ID formats
                    if row_id.startswith('report_student_'):
                        student_id = row_id.replace('report_student_', '')
                    elif row_id.startswith('student_'):
                        student_id = row_id.replace('student_', '')
                    else:
                        student_id = row_id
                
                # Get all cells in the row
                cells = await row.query_selector_all('td')
                
                if len(cells) < 2:  # Skip rows with too few cells
                    continue
                
                # Get student name (first column)
                name_element = cells[0]
                name = await name_element.text_content() if name_element else "Unknown"
                name = name.strip()
                
                # Skip if this is a header row, empty, or looks like a date
                if (not name or 
                    name.lower() in ['name', 'student'] or 
                    len(name) < 2 or
                    any(day in name for day in ['Sun,', 'Mon,', 'Tue,', 'Wed,', 'Thu,', 'Fri,', 'Sat,']) or
                    any(month in name for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) or
                    name.count(',') >= 2):  # Skip entries that look like dates
                    print(f"Skipping row: {name} (appears to be date or header)")
                    continue
                
                # Skip if we don't have a valid student ID
                if not student_id:
                    print(f"Skipping row: {name} (no valid student ID found)")
                    continue
                
                print(f"Processing student: {name} (ID: {student_id})")
                
                # Initialize student data with defaults (including real student ID)
                student_data = {
                    'id': student_id,  # Use the real Membean student ID
                    'name': name,
                    'goal_met': False,
                    'goal_progress': '0%',
                    'fifteen_min_days': 0,
                    'minutes_trained': 0,
                    'accuracy': '0%',
                    'dubious_minutes': 0,
                    'skipped_words': 0,
                    'new_words': 0,
                    'assessment_score': ''
                }
                
                # Use the same data extraction approach as the regular scraper
                
                # Goal Met (check for success/fail icon)
                goal_met_cell = await row.query_selector('td.goal-met-cell i')
                if goal_met_cell:
                    goal_met_class = await goal_met_cell.get_attribute('class')
                    student_data['goal_met'] = 'success' in goal_met_class
                
                # Goal Progress
                progress_cell = await row.query_selector('td[data-mode="goal_progress"] span.modal-link-content')
                if progress_cell:
                    student_data['goal_progress'] = await progress_cell.text_content()
                
                # 15-minute days
                days_cell = await row.query_selector('td[data-mode="n_min_days"]')
                if days_cell:
                    days_text = await days_cell.text_content()
                    student_data['fifteen_min_days'] = int(days_text.split('*')[0]) if days_text.strip() else 0
                
                # Minutes trained
                minutes_cell = await row.query_selector('td[data-mode="minutes_trained"]')
                if minutes_cell:
                    minutes_text = await minutes_cell.text_content()
                    student_data['minutes_trained'] = int(minutes_text) if minutes_text.strip() else 0
                
                # Accuracy
                accuracy_cell = await row.query_selector('td[data-mode="accuracy"]')
                if accuracy_cell:
                    accuracy_text = await accuracy_cell.text_content()
                    student_data['accuracy'] = accuracy_text.strip() if accuracy_text.strip() else '0%'
                
                # Dubious minutes
                dubious_cell = await row.query_selector('td[data-mode="dubious_minutes"]')
                if dubious_cell:
                    dubious_text = await dubious_cell.text_content()
                    student_data['dubious_minutes'] = int(dubious_text) if dubious_text.strip() else 0
                
                # Skipped words
                skipped_cell = await row.query_selector('td[data-mode="skipped_words"]')
                if skipped_cell:
                    skipped_text = await skipped_cell.text_content()
                    student_data['skipped_words'] = int(skipped_text) if skipped_text.strip() else 0
                
                # New words
                new_words_cell = await row.query_selector('td:nth-child(9)')
                if new_words_cell:
                    new_words_text = await new_words_cell.text_content()
                    student_data['new_words'] = int(new_words_text) if new_words_text.strip() else 0
                
                # Assessment score
                assessment_cell = await row.query_selector('td:nth-child(10)')
                if assessment_cell:
                    student_data['assessment_score'] = (await assessment_cell.text_content()).strip()
                
                students_data.append(student_data)
                
            except Exception as e:
                print(f"Error extracting data for a student row: {e}")
                continue
        
    except Exception as e:
        print(f"Error extracting student data: {e}")
    
    return students_data

async def save_to_supabase(students_data, report_date):
    """Save student data to Supabase with the specific report date"""
    for student_data in students_data:
        # Get current times
        now_utc = datetime.now(tz=ZoneInfo("UTC"))
        now_central = now_utc.astimezone(ZoneInfo("America/Chicago"))
        
        # Use the real Membean student ID from the extracted data
        student_id = student_data['id']
        
        # Prepare the data for Supabase (including report_date to track which day this data represents)
        student_record = {
            'student_id': student_id,
            'name': student_data['name'],
            'level': '',  # Will be empty for historical data unless we can extract it
            'level_sort': 0,
            'words_seen': 0,
            'last_trained': parse_date(report_date.strftime("%b %d, %Y")),  # Use report date as last trained
            'goal_met': student_data['goal_met'],
            'goal_progress': student_data['goal_progress'],
            'fifteen_min_days': student_data['fifteen_min_days'],
            'minutes_trained': student_data['minutes_trained'],
            'accuracy': student_data['accuracy'],
            'dubious_minutes': student_data.get('dubious_minutes', 0),
            'skipped_words': student_data.get('skipped_words', 0),
            'new_words': student_data.get('new_words', 0),
            'assessment_score': student_data.get('assessment_score', ''),
            'created_at': now_utc.isoformat(),
            'report_date': report_date.isoformat()  # Add the specific day this data represents
        }
        
        try:
            # Insert new record
            result = supabase.table('membean_students').insert(student_record).execute()
            print(f"Successfully saved data for {student_data['name']} on {report_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"Error saving to Supabase for {student_data['name']} on {report_date.strftime('%Y-%m-%d')}: {str(e)}")

async def main():
    """Main function to scrape historical data"""
    # Define date range - full historical range
    start_date = datetime(2025, 5, 1)
    end_date = datetime(2025, 6, 20)  # Full range as originally requested
    current_date = start_date
    
    print(f"Starting historical scrape from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"This will collect data for {(end_date - start_date).days + 1} days")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            # Login to Membean and navigate to class
            print("Logging in to Membean...")
            if not await login_to_membean(page):
                print("Failed to login to Membean")
                return
            
            # Loop through each date
            while current_date <= end_date:
                success = await scrape_single_day(page, current_date)
                
                if success:
                    print(f"✓ Successfully scraped {current_date.strftime('%Y-%m-%d')}")
                else:
                    print(f"✗ Failed to scrape {current_date.strftime('%Y-%m-%d')}")
                
                # Move to next day
                current_date += timedelta(days=1)
                
                # Add a delay between requests
                await page.wait_for_timeout(3000)
            
            print("Historical scraping complete!")
            
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 