#!/bin/bash
# Quick test script

echo "Browser Paywall Scraper Test"
echo "=============================="
echo ""
echo "Please provide a paywall article URL to test."
echo "For example:"
echo "  - WSJ article: https://www.wsj.com/articles/..."
echo "  - NYTimes article: https://www.nytimes.com/..."
echo "  - Bloomberg article: https://www.bloomberg.com/..."
echo ""
read -p "Enter article URL (or press Enter to skip): " url

if [ -z "$url" ]; then
    echo "No URL provided. Exiting."
    exit 0
fi

echo ""
echo "Running scraper..."
python3 browser_paywall_scraper.py "$url"
