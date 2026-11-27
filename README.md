# Lindholmen Lunch

**Lindholmen Lunch** – Your daily lunch overview for Gothenburg's Lindholmen district.

**Lindholmen Lunch** is a Python project that fetches, parses, and summarizes lunch menus from various restaurants in Lindholmen, Gothenburg. It scrapes menus from multiple restaurant websites, organizes the data by weekday, and generates user-friendly HTML summaries for easy viewing.

## Features

- Scrapes lunch menus from several Lindholmen restaurants using dedicated scrapers.
- Scrapes up to five restaurants concurrently, with sequential retries per restaurant and shared weekly caching.
- Stores daily menu data in JSON files under the `data/` directory.
- Opens today's menu automatically (Stockholm time; Monday on weekends), with links between all weekday menus.
- Modular scraper architecture for easy extension to new restaurants.
- Includes sample HTML files and test data for development and testing.

## Project Structure

```
.
├── main.py                  # Main entry point for scraping and HTML generation
├── generate_html.py         # Functions to generate HTML summaries from JSON data
├── utils.py                 # Utility functions (e.g., date helpers)
├── scrapers/                # Individual restaurant scrapers (one per restaurant)
├── data/                    # Cached JSON data and generated HTML summaries
├── docs/                  # Generated HTML files for each weekday and index
├── templates/               # Jinja2 HTML templates for rendering summaries
├── tests/                   # Test scripts and sample HTML files for development
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
└── .gitignore
```

## Requirements

- Python 3.10+
- Google Chrome (for Selenium-based scrapers)
- ChromeDriver installed and in your PATH

## Usage

1. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```
2. **Scrape menus and generate HTML:**

    Scraped data is cached in data/lunch_data_<day>.json and reused unless --refresh is passed.

   - To scrape and generate the summary for today:
     ```sh
     python main.py
     ```
   - To scrape for a specific day (e.g., "monday"):
     ```sh
     python main.py --day monday
     ```
   - Force refresh for a specific day (e.g., "monday"):
     ```sh
     python main.py --day monday --refresh
     ```
   - Force refresh for all days:
     ```sh
     python main.py --all --refresh
     ```
3. **View results:**

   - Open the generated HTML files in your browser (e.g., `docs/index.html`, `docs/lunch_monday.html`).

## Adding a New Restaurant

1. Create a new scraper in the `scrapers/` directory by subclassing `LunchScraper`.
2. Implement the scraping logic for the restaurant's website.
3. Add the new scraper to the `SCRAPERS` list in [`main.py`](main.py).

## Development & Testing

- Run or adapt tests as needed to verify scraper correctness.

## License

This project is for educational and personal use. Please respect the terms of use of the restaurant websites being scraped.

---
