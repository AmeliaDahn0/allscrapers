import asyncio
from playwright.async_api import async_playwright
from decouple import config
import os
import csv
from typing import List, Dict
import json
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
supabase: Client = create_client(
    config("SUPABASE_URL"),
    config("SUPABASE_KEY")
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

def load_student_list() -> List[str]:
    """Load the list of students to process from students.csv"""
    students = []
    try:
        with open('students.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:  # Removed next(reader) since our file doesn't have a header
                if row and not row[0].startswith('#'):  # Skip empty lines and comments
                    students.append(row[0].strip())
    except FileNotFoundError:
        print("Warning: students.csv not found. Please create it with a list of students to process.")
        print("Format: one student name per line")
        exit(1)
    
    if not students:
        print("No students found in students.csv")
        print("Please add student names to the file (one per line)")
        exit(1)
    
    return students

async def extract_student_data(page) -> List[Dict]:
    """Extract data from the students table"""
    students_data = []
    
    # Wait for the table to be visible
    table = await page.wait_for_selector('table#tclass-students-table')
    if not table:
        print("Could not find students table")
        return students_data
    
    # Get all student rows
    rows = await page.query_selector_all('table#tclass-students-table tbody tr')
    
    for row in rows:
        # Get student name
        name_element = await row.query_selector('td.fs-block.nowrap a')
        name = await name_element.text_content() if name_element else "Unknown"
        
        # Get student ID from the row
        student_id = await row.get_attribute('id')
        student_id = student_id.replace('student_', '') if student_id else None
        
        # Get level information
        level_element = await row.query_selector('td[data-sort]')
        level_text = await level_element.inner_text() if level_element else "Unknown"
        level_sort = await level_element.get_attribute('data-sort') if level_element else "0"
        
        # Get words seen
        words_seen_element = await row.query_selector('td:nth-child(4)')
        words_seen = await words_seen_element.text_content() if words_seen_element else "0"
        
        # Get last trained date
        last_trained_element = await row.query_selector('td:nth-child(5)')
        last_trained = await last_trained_element.text_content() if last_trained_element else ""
        
        student_data = {
            'id': student_id,
            'name': name.strip(),
            'level': level_text.strip(),
            'level_sort': int(level_sort),
            'words_seen': int(words_seen.strip() or 0),
            'last_trained': last_trained.strip()
        }
        
        students_data.append(student_data)
    
    return students_data

async def set_date_range_to_today(page):
    """Set the date range to today in the reports view"""
    try:
        print("Waiting for page load...")
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(2000)  # Give UI time to settle
        
        print("Looking for date range button...")
        # Try different selectors for the date range button
        date_btn = None
        date_selectors = [
            'a.btn.btn-white.btn-outlined-success[data-target="#report-settings-modal"]',
            'a[data-target="#report-settings-modal"]',
            'a.btn:has(i.fa-calendar)',
            'a:has(span.range-begin)',
        ]
        
        for selector in date_selectors:
            print(f"Trying date selector: {selector}")
            try:
                date_btn = await page.wait_for_selector(selector, timeout=5000)
                if date_btn:
                    print(f"Found date button with selector: {selector}")
                    break
            except:
                continue
        
        if not date_btn:
            print("Could not find date range button")
            return False
            
        print("Clicking date range button...")
        await date_btn.click()
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(2000)  # Give UI time to settle
        
        print("Looking for Today button...")
        # Try different selectors for the Today button
        today_btn = None
        today_selectors = [
            'a.mrl.mlm[data-period-key="today"]',
            'a[data-period-key="today"]',
            'a:text("Today")',
            'a:has-text("Today")',
        ]
        
        for selector in today_selectors:
            print(f"Trying today selector: {selector}")
            try:
                today_btn = await page.wait_for_selector(selector, timeout=5000)
                if today_btn:
                    print(f"Found today button with selector: {selector}")
                    break
            except:
                continue
        
        if not today_btn:
            print("Could not find Today button")
            return False
            
        print("Clicking Today button...")
        await today_btn.click()
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(2000)  # Give UI time to settle
        
        print("Looking for Apply button...")
        # Try different selectors for the Apply button
        apply_btn = None
        apply_selectors = [
            'button.btn.btn-secondary[type="submit"]',
            'button[type="submit"]:has-text("Apply")',
            'button:has-text("Apply")',
        ]
        
        for selector in apply_selectors:
            print(f"Trying apply selector: {selector}")
            try:
                apply_btn = await page.wait_for_selector(selector, timeout=5000)
                if apply_btn:
                    print(f"Found apply button with selector: {selector}")
                    break
            except:
                continue
        
        if not apply_btn:
            print("Could not find Apply button")
            return False
            
        print("Clicking Apply button...")
        await apply_btn.click()
        
        print("Waiting for table update...")
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_selector('table#report-table', timeout=30000)
        print("Set date range to today")
        return True
    except Exception as e:
        print(f"Error setting date range: {e}")
        return False

async def extract_report_data(page) -> Dict:
    """Extract data from the reports table"""
    reports_data = {}
    
    # Capture the current URL
    current_url = page.url
    reports_data['url'] = current_url
    
    # Wait for the table to be visible
    table = await page.wait_for_selector('table#report-table')
    if not table:
        print("Could not find reports table")
        return reports_data
    
    # Get all student rows
    rows = await page.query_selector_all('table#report-table tbody tr')
    
    # Store student-specific data in a nested dictionary
    reports_data['students'] = {}
    
    for row in rows:
        # Get student ID from the row ID
        student_id = await row.get_attribute('id')
        student_id = student_id.replace('report_student_', '') if student_id else None
        
        if not student_id:
            continue
            
        # Initialize data dictionary for this student
        student_data = {
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
        
        reports_data['students'][student_id] = student_data
    
    return reports_data

class DataCollector:
    def __init__(self):
        self.data = {
            'timestamp': datetime.now().isoformat(),
            'url': '',
            'students': {}
        }
        self.load_or_create_today_file()
    
    def load_or_create_today_file(self):
        """Load existing data or create new file for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        self.filename = f'data/membean_data_{today}.json'
        self.latest_filename = 'data/membean_data_latest.json'
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Try to load existing data
        try:
            with open(self.filename, 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            # Create new file with initial structure
            self.save_to_file()
    
    def add_student_data(self, students_data: List[Dict]):
        """Add student data to the collection"""
        for student in students_data:
            student_id = student['id']
            if student_id not in self.data['students']:
                self.data['students'][student_id] = {
                    'name': student['name'],
                    'current_data': {
                        'level': student['level'],
                        'level_sort': student['level_sort'],
                        'words_seen': student['words_seen'],
                        'last_trained': student['last_trained']
                    },
                    'tabs_data': {}
                }
    
    def add_tab_data(self, tab_name: str, tab_data: Dict):
        """Add tab data to the collection"""
        if 'url' in tab_data:
            self.data['url'] = tab_data['url']
        
        if 'students' in tab_data:
            for student_id, student_data in tab_data['students'].items():
                if student_id in self.data['students']:
                    self.data['students'][student_id]['tabs_data'][tab_name] = student_data
    
    def save_to_file(self):
        """Save data to both daily and latest files"""
        # Update timestamp
        self.data['timestamp'] = datetime.now().isoformat()
        
        # Save to daily file
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        # Save to latest file
        with open(self.latest_filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        # Save to Supabase
        self.save_to_supabase()
    
    def save_to_supabase(self):
        """Save data to Supabase"""
        # Get today's date for the report_date field
        today = datetime.now().date()
        
        for student_id, student_data in self.data['students'].items():
            current_data = student_data['current_data']
            reports_data = student_data['tabs_data'].get('Reports', {})
            
            # Prepare the data for Supabase
            student_record = {
                'student_id': student_id,
                'name': student_data['name'],
                'level': current_data['level'],
                'level_sort': current_data['level_sort'],
                'words_seen': current_data['words_seen'],
                'last_trained': parse_date(current_data['last_trained']),
                'goal_met': reports_data.get('goal_met', False),
                'goal_progress': reports_data.get('goal_progress', '0%'),
                'fifteen_min_days': reports_data.get('fifteen_min_days', 0),
                'minutes_trained': reports_data.get('minutes_trained', 0),
                'accuracy': reports_data.get('accuracy', '0%'),
                'dubious_minutes': reports_data.get('dubious_minutes', 0),
                'skipped_words': reports_data.get('skipped_words', 0),
                'new_words': reports_data.get('new_words', 0),
                'assessment_score': reports_data.get('assessment_score', ''),
                'created_at': datetime.now().isoformat(),  # Add current timestamp
                'report_date': today.isoformat()  # Add the date this data represents
            }
            
            try:
                # Insert new record instead of upserting
                result = supabase.table('membean_students').insert(student_record).execute()
                print(f"Successfully saved to Supabase: {student_data['name']}")
            except Exception as e:
                print(f"Error saving to Supabase for {student_data['name']}: {str(e)}")

# Global data collector
data_collector = None

async def process_tab_data(page, tab_name: str):
    """Process data from a specific tab"""
    print(f"Processing {tab_name} data...")
    
    if tab_name == "Students":
        students_data = await extract_student_data(page)
        data_collector.add_student_data(students_data)
    
    elif tab_name == "Reports":
        reports_data = await extract_report_data(page)
        data_collector.add_tab_data(tab_name, reports_data)
    
    elif tab_name == "Assessments":
        # TODO: Implement assessments data extraction
        data_collector.add_tab_data(tab_name, {})
    
    elif tab_name == "Writing":
        # TODO: Implement writing data extraction
        data_collector.add_tab_data(tab_name, {})
    
    elif tab_name == "Overview":
        # TODO: Implement overview data extraction
        data_collector.add_tab_data(tab_name, {})

async def navigate_tab(page, tab_id: str, tab_name: str) -> bool:
    """Navigate to a specific tab and wait for it to load"""
    try:
        # Click the tab
        tab_link = await page.wait_for_selector(f"#{tab_id}")
        if tab_link:
            await tab_link.click()
            # Wait for the tab content to load
            await page.wait_for_load_state('networkidle')
            print(f"Navigated to {tab_name} tab")
            return True
        else:
            print(f"Could not find {tab_name} tab")
            return False
    except Exception as e:
        print(f"Error navigating to {tab_name} tab: {e}")
        return False

async def login_to_membean(page):
    """Login to Membean using credentials from .env file"""
    # Navigate to login page
    await page.goto('https://membean.com/login')
    
    # Get credentials from environment variables
    username = config('MEMBEAN_USERNAME')
    password = config('MEMBEAN_PASSWORD')
    
    # Fill in login form
    await page.fill('input[name="username"]', username)
    await page.fill('input[name="password"]', password)
    
    # Click the login button
    await page.click('button[type="submit"]')
    
    # Wait for navigation after login
    await page.wait_for_load_state('networkidle')
    
    # Wait for the dashboard to load and find the SAT Blitz class
    try:
        # Wait for the class element to be visible
        sat_blitz_link = await page.wait_for_selector('a.js-tclass-name[data-id="345817"]')
        if sat_blitz_link:
            await sat_blitz_link.click()
            # Wait for the class page to load
            await page.wait_for_load_state('networkidle')
            print("Successfully navigated to SAT Blitz class")
        else:
            print("Could not find SAT Blitz class link")
            exit(1)
    except Exception as e:
        print(f"Error finding or clicking SAT Blitz class: {e}")
        exit(1)

async def process_student_data(page, student_name: str):
    """Process data for a specific student"""
    print(f"\nProcessing data for student: {student_name}")
    
    # First verify the student exists in the class
    await navigate_tab(page, "students-tab-link", "Students")
    
    # Split the name into parts
    name_parts = student_name.split()
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = name_parts[-1]
        
        # Try different name formats
        name_formats = [
            student_name,  # Original format: "First Last"
            f"{last_name}, {first_name}",  # "Last, First"
            f"{first_name} {last_name}",  # Ensure space is exact
            first_name,  # Just first name
            last_name,  # Just last name
        ]
        
        found = False
        for name_format in name_formats:
            student_row = await page.query_selector(f'tr:has-text("{name_format}")')
            if student_row:
                found = True
                break
        
        if not found:
            print(f"Warning: Could not find student {student_name} in class")
            return
    else:
        print(f"Warning: Invalid student name format: {student_name}")
        return
    
    # Define the tabs to navigate through
    tabs = [
        ("reports-tab-link", "Reports"),
        ("students-tab-link", "Students"),
        ("assessments-tab-link", "Assessments"),
        ("assignments-tab-link", "Writing"),
        ("overview-tab-link", "Overview")
    ]
    
    # Navigate through each tab and collect data
    for tab_id, tab_name in tabs:
        if await navigate_tab(page, tab_id, tab_name):
            await process_tab_data(page, tab_name)
            await page.wait_for_timeout(2000)  # Add delay between tab switches
        await asyncio.sleep(1)  # Small delay between tab switches

async def main():
    global data_collector
    data_collector = DataCollector()
    
    # Load the list of students to process
    students = load_student_list()
    print(f"Found {len(students)} students to process")
    
    # Check if running in CI environment
    is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
    headless_mode = is_ci  # Use headless mode in CI, non-headless locally
    
    async with async_playwright() as p:
        # Launch browser with appropriate headless setting
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection'
        ] if is_ci else []
        
        browser = await p.chromium.launch(
            headless=headless_mode,
            args=browser_args
        )
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            await login_to_membean(page)
            print("Successfully logged in!")
            
            # Set date range to today before processing any students
            print("Navigating to Reports tab...")
            await navigate_tab(page, "reports-tab-link", "Reports")
            print("Attempting to set date range...")
            if not await set_date_range_to_today(page):
                print("Failed to set date range to today, exiting...")
                return
            print("Successfully set date range to today")
            
            # Process each student in the list
            for student in students:
                try:
                    await process_student_data(page, student)
                except Exception as e:
                    print(f"Error processing student {student}: {e}")
                    continue  # Continue with next student
            
            # Save all collected data to a single file
            data_collector.save_to_file()
            print("Done! Browser will close automatically.")
            
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    # Check if running in CI or if .env file exists
    is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
    
    if not is_ci and not os.path.exists('.env'):
        print("Please create a .env file with your credentials.")
        print("Use .env.example as a template.")
        exit(1)
    
    # Verify required environment variables are present
    required_vars = ['MEMBEAN_USERNAME', 'MEMBEAN_PASSWORD', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) and not config(var, default=None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        if is_ci:
            print("Please configure these as repository secrets in GitHub Actions.")
        else:
            print("Please add these to your .env file.")
        exit(1)
        
    asyncio.run(main()) 