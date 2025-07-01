import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime
import pandas as pd
from supabase import create_client
import re
from dateutil import parser as date_parser

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def load_target_students():
    """Load the list of target students from target_students.txt."""
    try:
        with open('target_students.txt', 'r') as f:
            # Read lines and filter out comments and empty lines
            students = [
                line.strip() 
                for line in f.readlines() 
                if line.strip() and not line.strip().startswith('#')
            ]
        if not students:
            logger.warning("No target students found in target_students.txt")
        else:
            logger.info(f"Loaded {len(students)} target students")
        return set(students)  # Using a set for faster lookups
    except FileNotFoundError:
        logger.error("target_students.txt not found. Please create it with the list of target students.")
        return set()

async def login_to_math_academy(page):
    """Login to Math Academy using credentials from .env file."""
    try:
        await page.goto('https://www.mathacademy.com/login')
        logger.info("Navigated to login page")

        # Fill in login credentials
        await page.fill('#usernameOrEmail', os.getenv('MATH_ACADEMY_USERNAME'))
        await page.fill('#password', os.getenv('MATH_ACADEMY_PASSWORD'))
        
        # Click login button
        await page.click('#loginButton')
        
        # Wait for navigation after login
        await page.wait_for_load_state('networkidle')
        
        # Check if login was successful
        if 'login' not in page.url:
            logger.info("Login successful")
            return True
        else:
            logger.error("Login failed - still on login page")
            return False
            
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return False

async def get_task_details(page, task_element):
    task_info = {
        'id': None,
        'type': None,
        'name': None,
        'completion_time': None,
        'points': {
            'earned': None,
            'possible': None,
            'raw_text': None
        },
        'progress': None,
        'initial_placement': None
    }
    
    try:
        # Get task ID and attributes
        task_id = await task_element.get_attribute('id')
        if task_id:
            task_info['id'] = task_id.replace('task-', '')
        
        # Get task type
        task_type_elem = await task_element.query_selector('td.taskTypeColumn')
        if task_type_elem:
            task_info['type'] = (await task_type_elem.text_content()).strip()
            
        # Get task name
        task_name_elem = await task_element.query_selector('div.taskName')
        if task_name_elem:
            task_info['name'] = (await task_name_elem.text_content()).strip()
            
        # Get completion time
        completion_time_elem = await task_element.query_selector('td.taskCompletedColumn')
        if completion_time_elem:
            task_info['completion_time'] = (await completion_time_elem.text_content()).strip()
            
        # Get points information
        points_elem = await task_element.query_selector('span.taskPoints')
        if points_elem:
            points_text = await points_elem.text_content()
            task_info['points']['raw_text'] = points_text.strip()
            
            # Parse points (format: "6/4 XP")
            try:
                earned = points_text.split('/')[0].strip()
                possible = points_text.split('/')[1].split('XP')[0].strip()
                task_info['points']['earned'] = int(earned)
                task_info['points']['possible'] = int(possible)
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse points from text: {points_text}")
                
        # Get progress and initial placement from attributes
        progress = await task_element.get_attribute('progress')
        if progress:
            task_info['progress'] = progress
            
        initial_placement = await task_element.get_attribute('initialplacement')
        if initial_placement:
            task_info['initial_placement'] = initial_placement
            
    except Exception as e:
        logger.error(f"Error extracting task details: {str(e)}")
        
    return task_info

async def get_progress_details(page, student_id):
    """Get detailed progress information from a student's progress page."""
    try:
        # Navigate to student's progress page
        progress_url = f'https://www.mathacademy.com/students/{student_id}/progress'
        await page.goto(progress_url)
        
        # Wait for the page to be fully loaded
        await page.wait_for_load_state('networkidle')
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_load_state('load')
        
        # Add a small delay to ensure dynamic content is loaded
        await asyncio.sleep(2)
        
        logger.info(f"Navigated to progress page: {progress_url}")
        
        # Initialize data structure for progress
        progress_data = {
            'units': []
        }
        
        # Get all unit divs
        units = await page.query_selector_all('div.unit')
        
        for unit in units:
            try:
                # Get unit header info
                header = await unit.query_selector('div.unitHeader')
                unit_number = await header.query_selector('div.unitNumber')
                unit_name = await header.query_selector('span.unitName')
                unit_topics = await header.query_selector('div.unitNumTopics')
                
                # Get progress bar data
                progress_bar = await unit.query_selector('table.unitProgressBar tr')
                progress_cells = await progress_bar.query_selector_all('td')
                progress_segments = []
                
                for cell in progress_cells:
                    style = await cell.get_attribute('style')
                    width = None
                    color = None
                    
                    # Extract width and color from style
                    if style:
                        for attr in style.split(';'):
                            if 'width:' in attr:
                                width = attr.split('width:')[1].strip().replace('%', '')
                            elif 'background-color:' in attr:
                                color = attr.split('background-color:')[1].strip()
                    
                    progress_segments.append({
                        'width': float(width) if width else 0,
                        'color': color
                    })
                
                # Get modules data
                modules = await unit.query_selector_all('div.module')
                modules_data = []
                
                for module in modules:
                    module_name = await module.query_selector('div')
                    topics = await module.query_selector_all('tr')
                    topics_data = []
                    
                    for topic in topics:
                        topic_circle = await topic.query_selector('div.topicCircle')
                        topic_number = await topic.query_selector('td.topicNumber')
                        topic_name = await topic.query_selector('td.topicName a')
                        
                        circle_style = await topic_circle.get_attribute('style')
                        status_color = None
                        if circle_style:
                            for attr in circle_style.split(';'):
                                if 'background:' in attr:
                                    status_color = attr.split('background:')[1].strip()
                        
                        topics_data.append({
                            'number': await topic_number.text_content() if topic_number else None,
                            'name': await topic_name.text_content() if topic_name else None,
                            'status_color': status_color,
                            'url': await topic_name.get_attribute('href') if topic_name else None
                        })
                    
                    modules_data.append({
                        'name': await module_name.text_content() if module_name else None,
                        'topics': topics_data
                    })
                
                # Add unit data to progress_data
                progress_data['units'].append({
                    'number': await unit_number.text_content() if unit_number else None,
                    'name': await unit_name.text_content() if unit_name else None,
                    'total_topics': await unit_topics.text_content() if unit_topics else None,
                    'progress_segments': progress_segments,
                    'modules': modules_data
                })
                
            except Exception as e:
                logger.error(f"Error processing unit: {str(e)}")
                continue
        
        return progress_data
        
    except Exception as e:
        logger.error(f"Error getting progress details: {str(e)}")
        return None

async def get_activity_details(page, student_id):
    """Get detailed activity information from a student's activity page."""
    try:
        # Navigate to student's activity page
        student_url = f'https://www.mathacademy.com/students/{student_id}/activity'
        await page.goto(student_url)
        
        # Wait for the page to be fully loaded
        await page.wait_for_load_state('networkidle')
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_load_state('load')
        
        # Add a small delay to ensure dynamic content is loaded
        await asyncio.sleep(2)
        
        logger.info(f"Navigated to student page: {student_url}")
        
        # Get estimated completion date
        estimated_completion = None
        try:
            # Try multiple approaches to find the completion date
            # First try: Look for the specific text in any element
            completion_elem = await page.query_selector('div >> text="Estimated completion is"')
            if not completion_elem:
                # Second try: Look for any element containing the text
                completion_elem = await page.query_selector('div:has-text("Estimated completion")')
            if not completion_elem:
                # Third try: Look for text nodes containing the phrase
                completion_elem = await page.evaluate('''() => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.textContent.includes("Estimated completion is")) {
                            return node.textContent;
                        }
                    }
                    return null;
                }''')
            
            if completion_elem:
                if isinstance(completion_elem, str):
                    completion_text = completion_elem
                else:
                    completion_text = await completion_elem.text_content()
                
                if "Estimated completion is" in completion_text:
                    estimated_completion = completion_text.split("Estimated completion is")[1].strip()
                    logger.info(f"Found estimated completion date: {estimated_completion}")
                
        except Exception as e:
            logger.warning(f"Could not get estimated completion date: {str(e)}")
        
        # Initialize data structures
        daily_tasks = {}
        current_date = None
        
        # Get all task rows including date headers
        rows = await page.query_selector_all('tr')
        
        for row in rows:
            try:
                # Check if this is a date header
                date_header = await row.query_selector('td.dateHeader')
                if date_header:
                    # Extract date and XP
                    header_text = await date_header.text_content()
                    date_parts = header_text.split('XP')[0].strip()
                    xp_text = await date_header.query_selector('span.dateTotalXP')
                    daily_xp = await xp_text.text_content() if xp_text else "0 XP"
                    
                    current_date = {
                        'date': date_parts,
                        'daily_xp': daily_xp.strip(),
                        'tasks': []
                    }
                    daily_tasks[date_parts] = current_date
                    continue
                
                # Check if this is a task row
                task_id = await row.get_attribute('id')
                if task_id and task_id.startswith('task-'):
                    if current_date:
                        task_info = await get_task_details(page, row)
                        # Only include if the task is completed (has a completion time and earned XP)
                        if task_info.get('completion_time') and task_info['points'].get('earned') is not None:
                            current_date['tasks'].append(task_info)
                
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                continue
        
        # Ensure today is present in daily_tasks, even if empty
        today_str = datetime.now().strftime('%a, %b %d')
        if today_str not in daily_tasks:
            daily_tasks[today_str] = {
                'date': today_str,
                'daily_xp': '0 XP',
                'tasks': []
            }
        
        return {
            'daily_activity': daily_tasks,
            'estimated_completion': estimated_completion
        }
        
    except Exception as e:
        logger.error(f"Error getting activity details: {str(e)}")
        return None

async def get_student_details(page, student_id):
    """Get detailed information from a student's individual page."""
    try:
        # Get activity data
        activity_data = await get_activity_details(page, student_id)
        
        # Get progress data
        progress_data = await get_progress_details(page, student_id)
        
        # Combine the data
        return {
            'student_url': f'https://www.mathacademy.com/students/{student_id}',
            'daily_activity': activity_data['daily_activity'] if activity_data else {},
            'progress': progress_data if progress_data else {},
            'estimated_completion': activity_data['estimated_completion'] if activity_data else None
        }
        
    except Exception as e:
        logger.error(f"Error getting student details: {str(e)}")
        return None

def parse_last_activity(text):
    """Parse 'Last activity on Mon, Feb 24th', 'Last activity on Today', or 'Last activity on Yesterday' to ISO timestamp or None."""
    if not text or not text.strip():
        return None
    # Handle 'today'
    if 'today' in text.lower():
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    # Handle 'yesterday'
    if 'yesterday' in text.lower():
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    match = re.search(r"Last activity on (\w+), (\w+) (\d+)(?:st|nd|rd|th)?", text)
    if match:
        try:
            month = match.group(2)
            day = match.group(3)
            year = datetime.now().year
            date_str = f"{month} {day} {year}"
            dt = date_parser.parse(date_str)
            return dt.isoformat()
        except Exception:
            return None
    return None

async def scrape_teacher_dashboard(browser):
    """Scrape information from the teacher dashboard."""
    try:
        # Load target students
        target_students = load_target_students()
        if not target_students:
            logger.error("No target students found. Please add students to target_students.txt")
            return
            
        # Create initial context and page
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login first
        login_successful = await login_to_math_academy(page)
        if not login_successful:
            logger.error("Failed to login")
            await context.close()
            return
            
        # Navigate to students page
        await page.goto('https://www.mathacademy.com/students')
        await page.wait_for_load_state('networkidle')
        
        logger.info("Starting to scrape teacher dashboard")
        
        # Initialize student data list
        student_data = []
        
        # Wait for student elements to be visible and get all students
        await page.wait_for_selector('div.student', timeout=10000)
        student_elements = await page.query_selector_all('div.student')
        logger.info(f"Found {len(student_elements)} student elements")
        
        # Get list of all students for logging
        all_names = []
        target_student_elements = []
        for student_elem in student_elements:
            try:
                name_elem = await student_elem.query_selector('div.studentName')
                if name_elem:
                    name = await name_elem.text_content()
                    name = name.strip()
                    all_names.append(name)
                    if name in target_students:
                        target_student_elements.append((name, student_elem))
            except Exception as e:
                logger.error(f"Error getting student name: {str(e)}")
                continue
                
        logger.info(f"Found {len(all_names)} total students")
        logger.info(f"Found {len(target_student_elements)} target students")
        
        # Close initial page and context
        await page.close()
        await context.close()
        
        # Process each target student with a fresh context
        for student_name, student_elem in target_student_elements:
            try:
                logger.info(f"Processing student: {student_name}")
                
                # Create new context and page for this student
                student_context = await browser.new_context()
                student_page = await student_context.new_page()
                
                # Login again for this student's session
                login_successful = await login_to_math_academy(student_page)
                if not login_successful:
                    logger.error(f"Failed to login for student: {student_name}")
                    await student_context.close()
                    continue
                
                # Navigate to students page
                await student_page.goto('https://www.mathacademy.com/students')
                await student_page.wait_for_load_state('networkidle')
                
                # Get student ID and basic info
                student_elements = await student_page.query_selector_all('div.student')
                student_info = None
                
                for elem in student_elements:
                    name_elem = await elem.query_selector('div.studentName')
                    if name_elem:
                        name = await name_elem.text_content()
                        name = name.strip()
                        if name == student_name:
                            # Get student ID from the div id attribute
                            student_id_raw = await elem.get_attribute('id')
                            student_id = student_id_raw.split('-')[1] if student_id_raw else None
                            
                            if student_id:
                                # Get dashboard information
                                course_name_elem = await elem.query_selector('span.courseName')
                                course_progress_elem = await elem.query_selector('div.courseProgress')
                                last_activity_elem = await elem.query_selector('div.lastActivity')
                                todays_xp_elem = await elem.query_selector('td.todaysXP')
                                this_weeks_xp_elem = await elem.query_selector('span.thisWeeksXPValue')
                                
                                # Extract text content and attributes
                                course_name = await course_name_elem.text_content() if course_name_elem else ''
                                course_progress = await course_progress_elem.text_content() if course_progress_elem else ''
                                last_activity = await last_activity_elem.text_content() if last_activity_elem else ''
                                todays_xp = await todays_xp_elem.text_content() if todays_xp_elem else ''
                                this_weeks_xp = await this_weeks_xp_elem.text_content() if this_weeks_xp_elem else ''
                                
                                # Get detailed information from student's page
                                logger.info(f"Getting detailed information for student: {name}")
                                detailed_info = await get_student_details(student_page, student_id)
                                
                                # Prepare data for Supabase
                                parsed_last_activity = parse_last_activity(last_activity.strip())

                                # Fallback: if parsed_last_activity is None, use the most recent date from daily_activity
                                if not parsed_last_activity and detailed_info and detailed_info.get('daily_activity'):
                                    daily_activity = detailed_info['daily_activity']
                                    if daily_activity:
                                        # Try to get the most recent date key
                                        try:
                                            # Remove extra whitespace and sort by parsed date
                                            def parse_key_to_date(key):
                                                # Remove newlines and extra spaces
                                                date_str = key.split('\n')[0].strip()
                                                # Add current year for parsing
                                                return date_parser.parse(date_str + ' ' + str(datetime.now().year))
                                            most_recent = max(daily_activity.keys(), key=parse_key_to_date)
                                            dt = parse_key_to_date(most_recent)
                                            parsed_last_activity = dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                                        except Exception:
                                            parsed_last_activity = None

                                supabase_data = {
                                    'student_id': student_id,
                                    'name': name,
                                    'course_name': course_name.strip(),
                                    'percent_complete': course_progress.strip(),
                                    'last_activity': parsed_last_activity,
                                    'daily_xp': todays_xp.strip(),
                                    'weekly_xp': this_weeks_xp.strip(),
                                    'expected_weekly_xp': detailed_info.get('expected_weekly_xp') if detailed_info else None,
                                    'estimated_completion': detailed_info.get('estimated_completion') if detailed_info else None,
                                    'student_url': f'https://www.mathacademy.com/students/{student_id}/activity',
                                    'daily_activity': detailed_info.get('daily_activity', {}) if detailed_info else {},
                                    'tasks': detailed_info.get('tasks', []) if detailed_info else []
                                }

                                # Only save if student_id and name are present, and student_id is numeric
                                if supabase_data['student_id'] and supabase_data['name'] and supabase_data['student_id'].isdigit():
                                    success = await save_to_supabase(supabase_data)
                                    if success:
                                        logger.info(f"Successfully saved data for student {name} to Supabase")
                                    else:
                                        logger.error(f"Failed to save data for student {name} to Supabase")
                                    student_data.append(supabase_data)
                                else:
                                    logger.warning(f"Skipping student with missing or non-numeric student_id or name: {supabase_data}")
                                break
                
                # Close this student's context
                await student_page.close()
                await student_context.close()
                
                # Add a delay between students
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error processing student {student_name}: {str(e)}")
                continue
        
        if not student_data:
            logger.warning("No data collected. Check if the student names in target_students.txt match exactly with Math Academy.")
            return
            
        # Also save data to JSON file as backup
        json_filename = 'student_data.json'
        with open(json_filename, 'w') as f:
            json.dump(student_data, f, indent=2)
            
        logger.info(f"Data saved to {json_filename}")
        
    except Exception as e:
        logger.error(f"Error while scraping dashboard: {str(e)}")

async def save_to_supabase(student_data):
    """Save student data to Supabase as a new row every time."""
    try:
        # Prepare the data according to the schema
        supabase_data = {
            'student_id': str(student_data.get('student_id')),
            'name': str(student_data.get('name')),
            'course_name': str(student_data.get('course_name')) if student_data.get('course_name') else None,
            'percent_complete': str(student_data.get('percent_complete')) if student_data.get('percent_complete') else None,
            'last_activity': str(student_data.get('last_activity')) if student_data.get('last_activity') else None,
            'daily_xp': str(student_data.get('daily_xp')) if student_data.get('daily_xp') else None,
            'weekly_xp': str(student_data.get('weekly_xp')) if student_data.get('weekly_xp') else None,
            'expected_weekly_xp': str(student_data.get('expected_weekly_xp')) if student_data.get('expected_weekly_xp') else None,
            'estimated_completion': str(student_data.get('estimated_completion')) if student_data.get('estimated_completion') else None,
            'student_url': str(student_data.get('student_url')) if student_data.get('student_url') else None,
            'daily_activity': student_data.get('daily_activity', {}),
            'tasks': student_data.get('tasks', []),
            'created_at': datetime.now().isoformat()
        }

        # Remove None values to avoid null constraints
        supabase_data = {k: v for k, v in supabase_data.items() if v is not None}

        # Only insert if student_id and name are present
        if supabase_data.get('student_id') and supabase_data.get('name'):
            result = supabase.table('math_academy_students').insert(supabase_data).execute()
            if hasattr(result, 'data'):
                logger.info(f"Successfully inserted data for student {supabase_data.get('student_id')} to Supabase")
                return True
            else:
                logger.error(f"Failed to insert data for student {supabase_data.get('student_id')} to Supabase. Response: {result}")
                return False
        else:
            logger.warning(f"Skipping student with missing student_id or name: {supabase_data}")
            return False

    except Exception as e:
        logger.error(f"Error inserting to Supabase: {str(e)}")
        return False

async def main():
    """Main function to run the scraper."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            await scrape_teacher_dashboard(browser)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 