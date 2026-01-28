# Browser Paywall Scraper

## Overview

This script uses Selenium to access paywall articles through your logged-in Chrome browser and save them as HTML files.

## Setup

1. **Install Selenium**:
   ```bash
   pip install selenium
   ```

2. **Install ChromeDriver**:
   ```bash
   # Using Homebrew (macOS)
   brew install chromedriver
   
   # Or download from: https://chromedriver.chromium.org/
   ```

## Usage

```bash
python browser_paywall_scraper.py <article_url>
```

### Example

```bash
python browser_paywall_scraper.py https://www.wsj.com/articles/fed-rate-decision-2025
```

## How It Works

1. **Opens Chrome** with your existing profile (where you're logged into paywall sites)
2. **Navigates** to the article URL
3. **Extracts** article content, title, and author
4. **Saves** as HTML file with proper paragraph formatting
5. **Updates** `news.json` with the new article

## Features

- Uses your logged-in Chrome session (no need to login again)
- Automatically detects article content from various sites
- Properly formats paragraphs
- Marks articles as paywall automatically
- Generates summaries and tags

## Notes

- The browser window will open (not headless) so you can see what's happening
- Make sure Chrome is not already running when you start the script
- The script will automatically close the browser when done

## Troubleshooting

If you get "ChromeDriver not found":
- Install ChromeDriver: `brew install chromedriver`
- Or download from: https://chromedriver.chromium.org/

If content extraction fails:
- The script tries multiple selectors to find article content
- Some sites may need custom selectors (can be added to the script)
