# All Scrapers

A comprehensive collection of web scrapers for educational platforms, designed to collect and track student performance data across multiple learning tools.

## Overview

This repository contains automated scrapers for three major educational platforms:
- **AlphaRead** - Reading comprehension and literacy tracking
- **MemBean** - Vocabulary learning and word mastery
- **Math Academy** - Mathematics progress and skill development

## Scrapers Included

### 1. AlphaRead Scraper (`Scrapers/alphareadscraper/`)
- **Platform**: https://alpharead.alpha.school
- **Purpose**: Tracks reading levels, comprehension scores, and reading time
- **Features**: 
  - Google OAuth authentication
  - Daily automated scraping via GitHub Actions
  - Comprehensive student metrics collection
  - Supabase database integration
- **Data Collected**: Grade level, reading level, average scores, session statistics, time spent reading, success rates

### 2. MemBean Scraper (`Scrapers/membeanscraper/`)
- **Platform**: MemBean vocabulary learning platform
- **Purpose**: Monitors vocabulary progress and word mastery
- **Features**:
  - Historical data collection
  - Weekly progress reports
  - Student level tracking
  - Automated data processing
- **Data Collected**: Word levels, training sessions, progress metrics, last activity dates

### 3. Math Academy Scraper (`Scrapers/mathacademyscraper/`)
- **Platform**: https://www.mathacademy.com
- **Purpose**: Tracks mathematics learning progress and skill development
- **Features**:
  - Detailed progress tracking
  - Task completion monitoring
  - Points and achievement tracking
  - Unit-based progress analysis
- **Data Collected**: Task completion, points earned, unit progress, skill mastery

## Student Population

All scrapers track the same cohort of 14 students:
- Keyen Gupta, Olivia Attia, Layla Ford, Geetesh Parelly
- Hasini Chandrakumar, Lawson Fass, Sloka Vudumu, Ridhima Chelani
- Layla Kelch, Shrika Vudumu, Dilan Koya, Jaiden Koya
- Jashwanth Jagadeesan, Ananya Peesu

## Setup Instructions

### Prerequisites
- Python 3.8+
- Git
- Supabase account (for database storage)
- Access to educational platforms

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AmeliaDahn0/allscrapers.git
   cd allscrapers
   ```

2. **Set up individual scrapers**:
   ```bash
   # For each scraper directory
   cd Scrapers/[scraper-name]
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   - Copy `.env.example` to `.env` in each scraper directory
   - Add your platform credentials and Supabase keys

4. **Install Playwright browsers** (for scrapers using Playwright):
   ```bash
   playwright install
   ```

## Usage

### Running Individual Scrapers

Each scraper can be run independently:

```bash
# AlphaRead Scraper
cd Scrapers/alphareadscraper
python scraper.py

# MemBean Scraper
cd Scrapers/membeanscraper
python membean_scraper.py

# Math Academy Scraper
cd Scrapers/mathacademyscraper
python scraper.py
```

### Automated Execution

The AlphaRead scraper includes GitHub Actions for automated daily execution:
- Runs every hour via GitHub Actions
- Automatically commits updated data files
- Handles authentication and error recovery

## Data Storage

### Local Storage
- **JSON Files**: Daily snapshots with date-stamped filenames
- **Latest Data**: Most recent scraping results
- **Historical Data**: Complete history of student progress

### Database Storage
- **Supabase**: Centralized database for all scrapers
- **Structured Schemas**: Organized data tables for each platform
- **Real-time Updates**: Immediate data availability

## Data Structure

Each scraper collects platform-specific metrics:

### AlphaRead Data
```json
{
  "email": "student@example.com",
  "grade_level": "10",
  "reading_level": "8",
  "average_score": "65.23%",
  "sessions_this_month": "5",
  "total_sessions": "36",
  "time_reading": "8h 38m",
  "success_rate": "65.23%",
  "last_active": "May 10",
  "avg_session_time": "14m"
}
```

### MemBean Data
```json
{
  "id": "student_id",
  "name": "Student Name",
  "level": "Level 5",
  "words_seen": 150,
  "last_trained": "2025-06-25"
}
```

### Math Academy Data
```json
{
  "student_id": "12345",
  "name": "Student Name",
  "units_completed": 3,
  "total_points": 450,
  "current_unit": "Unit 4"
}
```

## Security & Configuration

### Environment Variables
Each scraper requires specific environment variables:
- Platform login credentials
- Supabase database credentials
- API keys and tokens

### GitHub Secrets (for automated execution)
- `ALPHAREAD_EMAIL`
- `ALPHAREAD_PASSWORD`
- `SUPABASE_URL`
- `SUPABASE_KEY`

## Monitoring & Maintenance

### Data Quality
- Automated error handling and recovery
- Data validation and cleaning
- Fallback mechanisms for missing data

### Performance
- Efficient scraping with minimal platform impact
- Rate limiting and respectful crawling
- Optimized data processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and personal use only. Please respect the terms of service of the platforms being scraped.

## Disclaimer

These scrapers are designed for educational purposes and personal use. Users are responsible for complying with the terms of service of the platforms being accessed. Ensure you have proper authorization before scraping any educational platform.

## Support

For issues or questions:
1. Check the individual scraper README files
2. Review the GitHub Actions logs for automated runs
3. Ensure all environment variables are properly configured 