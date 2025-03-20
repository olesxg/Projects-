# Prospekt Scraper

A Python-based scraper for collecting promotional leaflets from various stores. Built with performance and reliability in mind.

## Features

- Fast and efficient data collection using Playwright
- Robust error handling and automatic retries
- Smart date parsing with multiple format support
- Clean and maintainable codebase
- Comprehensive logging system
- Flexible output formats (JSON/JS)

## How It Works

1. **Initialization**
   - Loads configuration and sets up logging
   - Initializes Playwright browser instances
   - Prepares data storage structures

2. **Data Collection**
   - Visits store websites using Playwright
   - Extracts promotional information
   - Parses dates and validates data
   - Handles pagination and dynamic content

3. **Data Processing**
   - Normalizes dates to ISO format
   - Validates and cleans collected data
   - Removes duplicates
   - Structures data for export

4. **Export**
   - Saves data in JSON format
   - Generates JavaScript module if needed
   - Creates backup of results

## Setup

1. Install Python 3.11 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install
```

## Usage

### Basic Usage
Run the scraper with default settings:
```bash
python main.py
```

### Advanced Usage

1. **With Verbose Logging**
```bash
python main.py -v
```

2. **Custom Output Location**
```bash
python main.py -o ./data/leaflets.json
```

3. **Combined Options**
```bash
python main.py -v -o ./data/leaflets.json
```

### Expected Output
The script will:
1. Create output directory if it doesn't exist
2. Generate JSON file with collected data
3. Show progress in console
4. Log detailed information if verbose mode is enabled

## Output Format

### JSON
```json
{
    "store_name": "EDEKA",
    "title": "Wochenangebote",
    "start_date": "2025-03-16",
    "end_date": "2025-03-22",
    "parsed_time": "2024-03-17 15:30:00"
}
```

### JavaScript
```javascript
const leaflets = [
    {
        store_name: "EDEKA",
        title: "Wochenangebote",
        start_date: "2025-03-16",
        end_date: "2025-03-22",
        parsed_time: "2024-03-17 15:30:00"
    }
];
```

## Project Structure
- `main.py`: Entry point
- `scraper.py`: Core scraping logic
- `exporters.py`: Data export handlers
- `utils.py`: Helper functions
- `models.py`: Data structures
- `requirements.txt`: Dependencies

## Logging

The scraper provides detailed logging for monitoring and debugging:

- Start/end of scraping sessions
- Successful data collection
- Failed requests with retry attempts
- Date parsing results
- Export operations
- Performance metrics

Enable verbose logging with `-v` flag for maximum detail.

## Troubleshooting

### Common Issues

1. **Playwright Installation**
```bash
# If playwright install fails
pip install --upgrade pip
pip install playwright
playwright install
```

2. **Date Parsing Errors**
- Check if the date format matches the expected pattern
- Enable verbose logging to see raw date strings
- Dates should be in ISO format (YYYY-MM-DD)

3. **Connection Issues**
- Verify internet connection
- Check if target websites are accessible
- Consider using a VPN if blocked

4. **Memory Usage**
- For large datasets, use the `--output` flag to save to file
- Monitor system resources during long runs

## Performance Tips

- Use `--output` to save results to file for large datasets
- Enable verbose logging only when needed
- Consider running during off-peak hours
- Regular updates ensure optimal performance

## License
MIT
