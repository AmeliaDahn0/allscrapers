# Math Academy Teacher Dashboard Scraper

This script uses Playwright to log into Math Academy and extract information from the teacher dashboard.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install
```

3. Configure your credentials:
   - Copy the contents of `.env.example` to a new file named `.env`
   - Update the `.env` file with your Math Academy credentials:
     ```
     MATH_ACADEMY_USERNAME=your_username
     MATH_ACADEMY_PASSWORD=your_password
     ```

## Usage

Run the scraper:
```bash
python scraper.py
```

The script will:
1. Launch a browser window (visible for testing)
2. Log into Math Academy using your credentials
3. Navigate to the teacher dashboard
4. Extract student information (to be implemented based on dashboard structure)

## Notes

- The script currently runs in headed mode (visible browser) for testing purposes
- Modify the `scrape_teacher_dashboard()` function to extract specific information you need
- The browser will stay open for 10 seconds after completion for debugging purposes 