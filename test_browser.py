#!/usr/bin/env python3
"""Quick test to verify browser setup works."""

import sys
from browser_paywall_scraper import BrowserPaywallScraper

def test_browser_setup():
    """Test if browser can be initialized."""
    print("Testing browser setup...")
    
    try:
        scraper = BrowserPaywallScraper(headless=False)
        scraper.setup_driver()
        print("✓ Browser initialized successfully!")
        print("\nBrowser will open in 3 seconds to verify it works...")
        import time
        time.sleep(3)
        scraper.close()
        print("✓ Test completed successfully!")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Chrome is installed")
        print("2. Make sure ChromeDriver is installed: brew install chromedriver")
        print("3. Close all Chrome windows before running")
        return False

if __name__ == '__main__':
    success = test_browser_setup()
    sys.exit(0 if success else 1)
