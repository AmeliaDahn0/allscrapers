import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime
from supabase_client import upsert_student_data

# Load environment variables
load_dotenv()

def run_scraper():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)  # Always use headless in CI
        page = browser.new_page()
        
        try:
            # Navigate to login page
            page.goto('https://alpharead.alpha.school/guide/students')
            
            # Wait for the page to load
            page.wait_for_load_state('networkidle')
            
            # Try clicking the button by class first
            try:
                page.wait_for_selector('button.bg-gradient-to-b.from-reading-primary.to-reading-secondary', state='visible', timeout=5000)
                page.click('button.bg-gradient-to-b.from-reading-primary.to-reading-secondary')
            except Exception:
                # Fallback: Try partial text match
                page.wait_for_selector('button:has-text("Sign in with")', state='visible', timeout=5000)
                page.click('button:has-text("Sign in with")')
            
            # Wait for Google login page to load
            page.wait_for_url("https://accounts.google.com/**", timeout=15000)
            
            # Wait for the email input field to be visible
            page.wait_for_selector('input#identifierId', state='visible', timeout=15000)
            # Fill in the email from the .env file
            page.fill('input#identifierId', os.getenv('ALPHAREAD_EMAIL'))
            # Click the Next button
            page.click('button:has-text("Next")')
            
            # Wait for the password input field to be visible
            page.wait_for_selector('input[type="password"]', state='visible', timeout=15000)
            # Fill in the password from the .env file
            page.fill('input[type="password"]', os.getenv('ALPHAREAD_PASSWORD'))
            # Click the Next button
            page.click('button:has-text("Next")')
            
            # Add a small delay to ensure everything is loaded
            time.sleep(3)

            # Click the 'Guide Dashboard' button
            page.click('text=Guide Dashboard')
            
            # Click the 'Student Management' card
            page.click('text=Student Management')
            
            # Prepare daily JSON file for student data
            today_str = datetime.now().strftime('%Y-%m-%d')
            data_filename = f'student_data_{today_str}.json'
            latest_filename = 'student_data_latest.json'
            # Load or initialize daily file
            if os.path.exists(data_filename):
                with open(data_filename, 'r') as f:
                    student_data = json.load(f)
            else:
                with open('student_data_template.json', 'r') as f:
                    student_data = json.load(f)
                with open(data_filename, 'w') as f:
                    json.dump(student_data, f, indent=2)
            # Always start with a fresh latest_data structure for the latest file
            latest_data = {'students': []}
            
            # Read student emails from file
            with open('student_emails.txt', 'r') as f:
                student_emails = [line.strip() for line in f if line.strip()]

            for email in student_emails:
                print(f"\n--- Searching for student: {email} ---")
                # Clear the search bar before each search
                print("Clearing search bar...")
                page.fill('input[placeholder="Search..."]', '')
                print(f"Filling search bar with: {email}")
                page.fill('input[placeholder="Search..."]', email)
                print("Waiting for table to update...")
                time.sleep(2)  # Give the table more time to update
                # Use a robust selector to find the row with the email
                row_selector = f'tr:has(td:has-text("{email}"))'
                print(f"Looking for row with selector: {row_selector}")
                try:
                    page.wait_for_selector(row_selector, timeout=5000)
                    row = page.query_selector(row_selector)
                    print(f"Row found for {email}: {row is not None}")
                    if row:
                        # Find the "Details" button within the row and click it
                        details_button = row.query_selector('a:has-text("Details")')
                        if details_button:
                            print(f"Clicking Details button for {email}")
                            details_button.click()
                            # Wait for the details page to load (adjust selector as needed)
                            try:
                                page.wait_for_selector('text=Course Enrollment', timeout=5000)
                            except Exception:
                                time.sleep(2)  # Fallback wait if selector is not robust
                            # --- Scrape the data ---
                            student_info = {}
                            # Email
                            email_elem = page.query_selector('p.text-muted-foreground')
                            student_info['email'] = email_elem.inner_text().strip() if email_elem else email
                            # Grade Level, Reading Level, Average Score, Sessions This Month
                            info_boxes = page.query_selector_all('div.grid.grid-cols-2.md\\:grid-cols-4 > div.text-center')
                            if info_boxes and len(info_boxes) >= 4:
                                student_info['grade_level'] = info_boxes[0].query_selector('div.text-2xl.font-bold').inner_text().strip() if info_boxes[0].query_selector('div.text-2xl.font-bold') else None
                                student_info['reading_level'] = info_boxes[1].query_selector('div.text-2xl.font-bold').inner_text().strip() if info_boxes[1].query_selector('div.text-2xl.font-bold') else None
                                student_info['average_score'] = info_boxes[2].query_selector('div.text-2xl.font-bold').inner_text().strip() if info_boxes[2].query_selector('div.text-2xl.font-bold') else None
                                student_info['sessions_this_month'] = info_boxes[3].query_selector('div.text-2xl.font-bold').inner_text().strip() if info_boxes[3].query_selector('div.text-2xl.font-bold') else None
                            # Total Sessions, Time Reading, Success Rate, Last Active, Avg. Session Time
                            stats_boxes = page.query_selector_all('div.mt-6.grid.grid-cols-2.sm\\:grid-cols-5 > div.flex')
                            if stats_boxes and len(stats_boxes) >= 5:
                                student_info['total_sessions'] = stats_boxes[0].query_selector('div.text-xl.font-bold').inner_text().strip() if stats_boxes[0].query_selector('div.text-xl.font-bold') else None
                                student_info['time_reading'] = stats_boxes[1].query_selector('div.text-xl.font-bold').inner_text().strip() if stats_boxes[1].query_selector('div.text-xl.font-bold') else None
                                student_info['success_rate'] = stats_boxes[2].query_selector('div.text-xl.font-bold').inner_text().strip() if stats_boxes[2].query_selector('div.text-xl.font-bold') else None
                                student_info['last_active'] = stats_boxes[3].query_selector('div.text-xl.font-bold').inner_text().strip() if stats_boxes[3].query_selector('div.text-xl.font-bold') else None
                                student_info['avg_session_time'] = stats_boxes[4].query_selector('div.text-xl.font-bold').inner_text().strip() if stats_boxes[4].query_selector('div.text-xl.font-bold') else None
                            # Current Course
                            current_course = page.query_selector('div.p-6.pt-0 span')
                            student_info['current_course'] = current_course.inner_text().strip() if current_course else None
                            # User PowerPath ID
                            powerpath_id = page.query_selector('div.text-right .font-mono')
                            student_info['user_powerpath_id'] = powerpath_id.inner_text().strip() if powerpath_id else None
                            print(student_info)
                            
                            # Save to JSON files
                            if 'students' not in student_data:
                                student_data['students'] = []
                            # Check if student already exists (by email)
                            existing = next((s for s in student_data['students'] if s.get('email') == student_info['email']), None)
                            if existing:
                                existing.update(student_info)
                            else:
                                student_data['students'].append(student_info)
                            # For latest_data, just append (no need to check for existing, since it's a fresh run)
                            latest_data['students'].append(student_info)
                            
                            # Save to Supabase
                            print(f"Saving {email} to Supabase...")
                            result = upsert_student_data(student_info)
                            if result:
                                print(f"Successfully saved {email} to Supabase")
                            else:
                                print(f"Failed to save {email} to Supabase")
                            
                            # --- End scrape ---
                            time.sleep(2)  # Pause to simulate human reading/scraping
                            page.go_back()  # Go back to the student list
                            page.wait_for_selector('input[placeholder="Search..."]', timeout=5000)
                        else:
                            print(f"Details button not found for {email}")
                            # Create basic student record
                            student_info = {
                                'email': email,
                                'grade_level': None,
                                'reading_level': None,
                                'average_score': '0%',
                                'sessions_this_month': '0',
                                'total_sessions': '0',
                                'time_reading': '0m',
                                'success_rate': '0%',
                                'last_active': datetime.now().strftime('%b %d'),
                                'avg_session_time': '0m',
                                'current_course': None,
                                'user_powerpath_id': None
                            }
                            # Save to JSON files
                            if 'students' not in student_data:
                                student_data['students'] = []
                            student_data['students'].append(student_info)
                            latest_data['students'].append(student_info)
                            
                            # Save to Supabase
                            print(f"Saving {email} to Supabase...")
                            result = upsert_student_data(student_info)
                            if result:
                                print(f"Successfully saved {email} to Supabase")
                            else:
                                print(f"Failed to save {email} to Supabase")
                    else:
                        print(f"No row found for {email}")
                        # Create basic student record
                        student_info = {
                            'email': email,
                            'grade_level': None,
                            'reading_level': None,
                            'average_score': '0%',
                            'sessions_this_month': '0',
                            'total_sessions': '0',
                            'time_reading': '0m',
                            'success_rate': '0%',
                            'last_active': datetime.now().strftime('%b %d'),
                            'avg_session_time': '0m',
                            'current_course': None,
                            'user_powerpath_id': None
                        }
                        # Save to JSON files
                        if 'students' not in student_data:
                            student_data['students'] = []
                        student_data['students'].append(student_info)
                        latest_data['students'].append(student_info)
                        
                        # Save to Supabase
                        print(f"Saving {email} to Supabase...")
                        result = upsert_student_data(student_info)
                        if result:
                            print(f"Successfully saved {email} to Supabase")
                        else:
                            print(f"Failed to save {email} to Supabase")
                except Exception as e:
                    print(f"Could not find row or details for {email}: {e}")
                    # Create basic student record
                    student_info = {
                        'email': email,
                        'grade_level': None,
                        'reading_level': None,
                        'average_score': '0%',
                        'sessions_this_month': '0',
                        'total_sessions': '0',
                        'time_reading': '0m',
                        'success_rate': '0%',
                        'last_active': datetime.now().strftime('%b %d'),
                        'avg_session_time': '0m',
                        'current_course': None,
                        'user_powerpath_id': None
                    }
                    # Save to JSON files
                    if 'students' not in student_data:
                        student_data['students'] = []
                    student_data['students'].append(student_info)
                    latest_data['students'].append(student_info)
                    
                    # Save to Supabase
                    print(f"Saving {email} to Supabase...")
                    result = upsert_student_data(student_info)
                    if result:
                        print(f"Successfully saved {email} to Supabase")
                    else:
                        print(f"Failed to save {email} to Supabase")
                # Pause before next search
                time.sleep(2)
            
            # Write both files
            with open(data_filename, 'w') as f:
                json.dump(student_data, f, indent=2)
            with open(latest_filename, 'w') as f:
                json.dump(latest_data, f, indent=2)
            
            print("\nScraping completed successfully!")
            
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_scraper() 