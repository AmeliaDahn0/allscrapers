# AlphaRead Scraper

A web scraping system designed to extract student reading data from the AlphaRead platform (https://alpharead.alpha.school) and store it in both local JSON files and a Supabase database.

## Features

- **Automated Web Scraping**: Uses Playwright for browser automation
- **Google OAuth Login**: Automated authentication via Google
- **Student Data Extraction**: Collects comprehensive reading metrics
- **Dual Storage**: Saves data to both local JSON files and Supabase database
- **Daily Snapshots**: Maintains historical data with date-stamped files
- **Error Handling**: Robust error handling with default records for missing students
- **GitHub Actions**: Automated scheduling and execution via GitHub Actions

## Data Collected

For each student, the scraper extracts:
- Email address
- Grade level and reading level
- Average score and success rate
- Session statistics (total, this month, average time)
- Time spent reading
- Last active date
- Current course
- User PowerPath ID

## Setup

### Prerequisites

- Python 3.8+
- Git
- Supabase account (for database storage)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/AmeliaDahn0/alphareadscraper.git
cd alphareadscraper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Create a `.env` file with your credentials:
```env
ALPHAREAD_EMAIL=your_email@example.com
ALPHAREAD_PASSWORD=your_password
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Configuration

1. **AlphaRead Credentials**: Add your AlphaRead login credentials to the `.env` file
2. **Supabase Setup**: 
   - Create a Supabase project
   - Create a table named `alpharead_students` with the appropriate schema
   - Add your Supabase URL and key to the `.env` file
3. **Student Emails**: Update `student_emails.txt` with the email addresses of students to scrape

## GitHub Actions Setup

### Setting Up Repository Secrets

To use the automated GitHub Actions, you need to add the following secrets to your repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add each of the following:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ALPHAREAD_EMAIL` | Your AlphaRead login email | `your_email@example.com` |
| `ALPHAREAD_PASSWORD` | Your AlphaRead login password | `your_password` |
| `SUPABASE_URL` | Your Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_KEY` | Your Supabase service role key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |

### How to Find Your Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy the **Project URL** for `SUPABASE_URL`
4. Copy the **service_role** key for `SUPABASE_KEY` (not the anon key)

### Available Workflows

The repository includes three GitHub Actions workflows:

**`scraper.yml`**: Basic scraper workflow
- **Schedule**: Runs every day at 6:00 AM UTC
- **Manual Trigger**: Can be run manually via the Actions tab
- **Features**:
  - Installs Python dependencies and Playwright browsers
  - Creates `.env` file from GitHub secrets
  - Runs the scraper
  - Commits and pushes updated data files back to the repository

**`scraper-advanced.yml`**: Advanced scraper workflow
- **Schedule**: Runs every day at 6:00 AM UTC
- **Manual Trigger**: Can be run manually via the Actions tab
- **Features**:
  - 30-minute timeout protection
  - Better error handling and logging
  - Conditional commits (only when data changes)
  - Data artifacts uploaded for 30 days
  - Optional Slack notifications (requires `SLACK_WEBHOOK_URL` secret)
  - Detailed run summaries

**`test.yml`**: Test workflow
- **Triggers**: Runs on every push and pull request
- **Features**:
  - Validates Python imports
  - Checks file structure
  - Validates JSON files
  - Verifies email format in `student_emails.txt`
  - Ensures setup is correct before deployment

### Optional Slack Notifications

To receive Slack notifications about scraper runs:

1. Create a Slack app and get a webhook URL
2. Add `SLACK_WEBHOOK_URL` to your repository secrets
3. Use the `scraper-advanced.yml` workflow

The notifications will include:
- Success/failure status
- Link to the GitHub Actions run
- Whether data changes were detected
- Timestamp of completion

### Manual Execution

You can manually trigger the scraper:
1. Go to the **Actions** tab in your repository
2. Select **AlphaRead Scraper** workflow
3. Click **Run workflow**
4. Choose the branch to run on (usually `main`)
5. Click **Run workflow**

### Monitoring Runs

- View run history in the **Actions** tab
- Check logs for any errors or issues
- Monitor the **student_data_latest.json** file for updated data
- Review daily snapshot files for historical data

## Usage

### Run the Scraper Locally

```bash
python scraper.py
```

This will:
- Log into AlphaRead
- Navigate to the Student Management dashboard
- Search for each student in `student_emails.txt`
- Extract their reading data
- Save to daily JSON files and Supabase database

### API Discovery

To discover potential API endpoints:

```bash
python api_discovery.py
```

This will monitor network traffic during the login and navigation process to identify API calls.

## File Structure

```
alphareadscraper/
├── scraper.py              # Main scraping script
├── supabase_client.py      # Database operations
├── api_discovery.py        # API endpoint discovery
├── requirements.txt        # Python dependencies
├── student_emails.txt      # List of student emails
├── student_data_template.json  # Template for data structure
├── student_data_latest.json    # Most recent scraping results
├── student_data_YYYY-MM-DD.json # Daily snapshots
├── .github/workflows/      # GitHub Actions workflows
│   ├── scraper.yml         # Basic scraper workflow
│   ├── scraper-advanced.yml # Advanced scraper workflow
│   └── test.yml           # Test workflow
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Database Schema

The Supabase table `alpharead_students` should have the following columns:

- `student_id` (text): PowerPath ID or email
- `name` (text): Student name extracted from email
- `level` (text): Reading level
- `progress` (text): Average score
- `last_activity` (timestamp): Last active date
- `accuracy` (text): Success rate
- `reading_time` (integer): Total reading time in minutes
- `created_at` (timestamp): Record creation time
- `scrape_date` (date): Date of scraping

## Output Files

- **`student_data_latest.json`**: Contains the most recent scraping results
- **`student_data_YYYY-MM-DD.json`**: Daily snapshots for historical tracking
- **Supabase Database**: Cloud storage with transformed data
- **GitHub Artifacts**: Archived data files from each run

## Error Handling

The scraper includes robust error handling:
- Creates default records for students not found
- Handles network timeouts and connection issues
- Provides detailed logging for debugging
- Continues processing even if individual students fail
- GitHub Actions include timeout protection and failure notifications

## Monitoring

- **GitHub Actions**: Monitor runs in the Actions tab
- **Artifacts**: Download data files from successful runs
- **Notifications**: Optional Slack notifications for failures
- **Run Summaries**: Detailed summaries for each execution

## Security Notes

- Never commit the `.env` file to version control
- Keep your AlphaRead credentials secure
- Use environment variables for all sensitive data
- The `.gitignore` file is configured to exclude sensitive files
- GitHub secrets are encrypted and secure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and research purposes. Please ensure compliance with AlphaRead's terms of service and data privacy regulations.

## Support

For issues or questions, please open an issue on GitHub. 