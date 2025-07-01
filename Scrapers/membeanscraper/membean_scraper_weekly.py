import asyncio
from playwright.async_api import async_playwright
from decouple import config
import os
import csv
from typing import List, Dict
import json
from datetime import datetime, timedelta

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

def get_week_dates():
    """Get the Sunday and Saturday dates for the current week"""
    today = datetime.now()
    sunday = today - timedelta(days=today.weekday() + 1)  # Go back to previous Sunday
    saturday = sunday + timedelta(days=6)  # Get the following Saturday
    return sunday.strftime("%b %d, %Y"), saturday.strftime("%b %d, %Y")

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

async def set_date_range_to_week(page):
    """Set the date range to current week (Sunday to Saturday) in the reports view"""
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
        
        print("Looking for Custom button...")
        custom_btn = await page.wait_for_selector('a.mrl[data-period-key="custom"]')
        if not custom_btn:
            print("Could not find Custom button")
            return False
            
        print("Clicking Custom button...")
        await custom_btn.click()
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(2000)  # Give UI time to settle
        
        # Get current week's Sunday and Saturday dates
        start_date, end_date = get_week_dates()
        
        print(f"Setting date range to: {start_date} - {end_date}")
        
        # Fill in start date
        start_date_input = await page.wait_for_selector('#custom_start_date')
        if not start_date_input:
            print("Could not find start date input")
            return False
        await start_date_input.fill(start_date)
        
        # Fill in end date
        end_date_input = await page.wait_for_selector('#custom_end_date')
        if not end_date_input:
            print("Could not find end date input")
            return False
        await end_date_input.fill(end_date)
        
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
        print("Set date range to current week")
        return True
    except Exception as e:
        print(f"Error setting date range: {e}")
        return False

async def extract_report_data(page) -> Dict:
    """Extract data from the reports table"""
    reports_data = {}
    
    # Wait for the table to be visible
    table = await page.wait_for_selector('table#report-table')
    if not table:
        print("Could not find reports table")
        return reports_data
    
    # Get all student rows
    rows = await page.query_selector_all('table#report-table tbody tr')
    
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
        new_words_cell = await row.query_selector('td[data-mode="new_words"]')
        if new_words_cell:
            new_words_text = await new_words_cell.text_content()
            student_data['new_words'] = int(new_words_text) if new_words_text.strip() else 0
        
        # Assessment score
        assessment_cell = await row.query_selector('td[data-mode="assessment_score"]')
        if assessment_cell:
            student_data['assessment_score'] = await assessment_cell.text_content()
        
        reports_data[student_id] = student_data
    
    return reports_data

async def process_tab_data(page, tab_name: str):
    """Process data from a specific tab"""
    print(f"\nProcessing {tab_name} tab...")
    
    if tab_name == "Reports":
        # Extract report data
        return await extract_report_data(page)
    
    # For other tabs, return empty data for now
    return {}

async def navigate_tab(page, tab_id: str, tab_name: str) -> bool:
    """Navigate to a specific tab"""
    try:
        print(f"Navigating to {tab_name} tab...")
        
        # Try different selectors for the tab
        tab_selectors = [
            f'a[href="#{tab_id}"]',
            f'a#{tab_id}',
            f'a[data-tab="{tab_id}"]',
            f'a:has-text("{tab_name}")',
            f'a.nav-link:has-text("{tab_name}")',
            f'a.tab-link:has-text("{tab_name}")',
            f'a[role="tab"]:has-text("{tab_name}")'
        ]
        
        tab = None
        for selector in tab_selectors:
            try:
                tab = await page.wait_for_selector(selector, timeout=5000)
                if tab:
                    print(f"Found tab with selector: {selector}")
                    break
            except:
                continue
        
        if not tab:
            print(f"Could not find {tab_name} tab")
            return False
        
        await tab.click()
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)  # Give UI time to settle
        return True
    except Exception as e:
        print(f"Error navigating to {tab_name} tab: {e}")
        return False

async def login_to_membean(page):
    """Log in to Membean"""
    try:
        print("Loading login page...")
        await page.goto('https://membean.com/login', wait_until='networkidle')
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_timeout(5000)  # Wait for 5 seconds
        
        print("Entering credentials...")
        # Get credentials from environment variables
        username = config('MEMBEAN_USERNAME')
        password = config('MEMBEAN_PASSWORD')
        
        # Wait for and fill in login form with human-like delays
        username_input = await page.wait_for_selector('#username', timeout=120000)
        await page.wait_for_timeout(1000)  # Wait 1 second
        await username_input.type(username, delay=100)  # Type slowly
        
        password_input = await page.wait_for_selector('#password', timeout=120000)
        await page.wait_for_timeout(1000)  # Wait 1 second
        await password_input.type(password, delay=100)  # Type slowly
        
        await page.wait_for_timeout(2000)  # Wait 2 seconds before clicking
        
        # Wait for and click login button
        submit_button = await page.wait_for_selector('button.btn-call-to-action[type="submit"]', timeout=120000)
        await submit_button.click()
        
        # Wait for navigation and check success
        try:
            await page.wait_for_url('**/dashboard**', timeout=120000)
            print("Login successful")
            
            # Wait for the SAT Blitz class link and click it
            print("Looking for SAT Blitz class link...")
            sat_blitz_link = await page.wait_for_selector('a:text("SAT Blitz - 2 Hour Learning")', timeout=120000)
            if not sat_blitz_link:
                print("Could not find SAT Blitz class link")
                return False
                
            print("Clicking SAT Blitz class link...")
            await sat_blitz_link.click()
            await page.wait_for_load_state('networkidle')
            print("Successfully navigated to SAT Blitz class")
            return True
            
        except Exception as e:
            print(f"Error after login: {e}")
            current_url = page.url
            print(f"Current URL: {current_url}")
            await page.screenshot(path='login_error.png')
            return False
                
    except Exception as e:
        print(f"Error during login: {e}")
        await page.screenshot(path='login_error.png')
        return False

async def process_student_data(page, student_name: str):
    """Process data for a specific student"""
    try:
        print(f"\nProcessing student: {student_name}")
        
        # Navigate to Students tab
        print("Navigating to Students tab...")
        await navigate_tab(page, "students-tab-link", "Students")
        await page.wait_for_load_state('networkidle')
        
        # Split the name into parts for flexible searching
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
                return None
        else:
            print(f"Warning: Invalid student name format: {student_name}")
            return None
        
        # Extract initial student data
        student_data = await extract_student_data(page)
        if not student_data:
            print("Failed to extract student data")
            return None
        
        # Process each tab
        tabs_to_process = [
            ('reports', 'Reports'),
            ('assessments', 'Assessments'),
            ('writing', 'Writing'),
            ('overview', 'Overview')
        ]
        
        tab_data = {}
        for tab_id, tab_name in tabs_to_process:
            if await navigate_tab(page, tab_id, tab_name):
                tab_result = await process_tab_data(page, tab_name)
                tab_data[tab_name] = tab_result
                await page.wait_for_timeout(2000)  # Add delay between tab switches
            await asyncio.sleep(1)  # Small delay between tab switches
        
        return student_data, tab_data
    except Exception as e:
        print(f"Error processing student {student_name}: {e}")
        return None

class DataCollector:
    def __init__(self):
        self.data = {
            'timestamp': datetime.now().isoformat(),
            'students': {}
        }
    
    def add_student_data(self, students_data: List[Dict]):
        """Add student data to the collector"""
        for student in students_data:
            student_id = student.pop('id')
            if student_id not in self.data['students']:
                self.data['students'][student_id] = {
                    'name': student.pop('name'),
                    'current_data': student,
                    'tabs_data': {}
                }
    
    def add_tab_data(self, tab_name: str, tab_data: Dict):
        """Add tab data to the collector"""
        for student_id, data in tab_data.items():
            if student_id in self.data['students']:
                self.data['students'][student_id]['tabs_data'][tab_name] = data
    
    def save_to_file(self):
        """Save collected data to a JSON file"""
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Get the date range for the filename
        start_date, end_date = get_week_dates()
        start_date_str = start_date.replace(" ", "_")
        end_date_str = end_date.replace(" ", "_")
        
        # Generate filename with date range
        filename = f"data/membean_weekly_{start_date_str}_to_{end_date_str}.json"
        
        # Save data to file
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Data saved to {filename}")

async def main():
    """Main function to run the scraper"""
    # Load student list
    students = load_student_list()
    print(f"Loaded {len(students)} students to process")
    
    # Initialize data collector
    collector = DataCollector()
    
    async with async_playwright() as p:
        # Launch browser with custom settings
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # Add page error handling
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Page error: {err}"))
        
        # Set default navigation timeout
        page.set_default_navigation_timeout(120000)  # 2 minutes
        page.set_default_timeout(120000)  # 2 minutes
        
        # Login
        if not await login_to_membean(page):
            print("Failed to log in")
            await browser.close()
            return
            
        # Navigate to Reports tab and set date range to current week once
        print("\nNavigating to Reports tab...")
        if not await navigate_tab(page, "reports", "Reports"):
            print("Failed to navigate to Reports tab")
            await browser.close()
            return
            
        print("Setting date range to current week...")
        if not await set_date_range_to_week(page):
            print("Failed to set date range to current week")
            await browser.close()
            return
        
        # Process each student
        for student in students:
            result = await process_student_data(page, student)
            if result:
                student_data, tab_data = result
                collector.add_student_data(student_data)
                for tab_name, data in tab_data.items():
                    collector.add_tab_data(tab_name, data)
        
        await browser.close()
    
    # Save collected data
    collector.save_to_file()
    print("Done!")

if __name__ == "__main__":
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Please create a .env file with your credentials.")
        print("Use .env.example as a template.")
        exit(1)
        
    asyncio.run(main()) 