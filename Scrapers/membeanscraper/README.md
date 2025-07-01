# All Scrapers

A collection of web scrapers for various educational platforms and services.

## Scrapers Included

### 1. MemBean Scraper
- **Location**: `membeanscraper/`
- **Purpose**: Scrapes student data from MemBean educational platform
- **Features**: 
  - Historical data scraping
  - Weekly data collection
  - Supabase integration for data storage
  - Automated login and data extraction

### 2. Math Academy Scraper
- **Location**: `mathacademyscraper/`
- **Purpose**: Scrapes data from Math Academy platform
- **Features**: 
  - Student progress tracking
  - Automated data collection

### 3. AlphaRead Scraper
- **Location**: `alphareadscraper/`
- **Purpose**: Scrapes data from AlphaRead platform
- **Features**: 
  - API discovery and data extraction
  - Student data collection

### 4. AlphaLearn Scraper
- **Location**: `alphalearnscraper/`
- **Purpose**: Scrapes data from AlphaLearn platform
- **Features**: 
  - Learning progress tracking
  - Automated data collection

### 5. RocketMath Scraper
- **Location**: `rocketmathscraper/`
- **Purpose**: Scrapes data from RocketMath platform
- **Features**: 
  - Math progress tracking
  - Student performance data

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/AmeliaDahn0/allscrapers.git
   cd allscrapers
   ```

2. Set up virtual environment for each scraper:
   ```bash
   # For each scraper directory
   cd [scraper-name]
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env` in each scraper directory
   - Fill in the required credentials and API keys

## Usage

Each scraper can be run independently. Navigate to the specific scraper directory and follow the individual README instructions.

### Example:
```bash
cd membeanscraper
source venv/bin/activate
python membean_scraper.py
```

## Data Storage

Most scrapers are configured to store data in:
- JSON files locally
- Supabase database (where configured)
- CSV files for analysis

## Security Notes

- Never commit `.env` files containing sensitive credentials
- Keep API keys and passwords secure
- Use environment variables for sensitive configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and personal use only. Please respect the terms of service of the platforms being scraped.

## Disclaimer

These scrapers are designed for educational purposes and personal use. Users are responsible for complying with the terms of service of the platforms being accessed. 