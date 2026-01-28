#!/usr/bin/env python3
"""
Browser-based paywall article scraper using Selenium.
Uses your logged-in Chrome browser to access paywall articles.
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime
from urllib.parse import urlparse

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    print("Warning: selenium not installed. Install with: pip install selenium")

from news_scraper import NewsScraper


class BrowserPaywallScraper:
    """Scrape paywall articles using logged-in Chrome browser."""
    
    def __init__(self, headless=False, use_profile=True):
        """Initialize the browser scraper."""
        if not HAS_SELENIUM:
            raise ImportError("selenium is required. Install with: pip install selenium")
        
        self.headless = headless
        self.use_profile = use_profile
        self.driver = None
        self.scraper = NewsScraper()
        
    def setup_driver(self):
        """Setup Chrome driver with user profile."""
        chrome_options = Options()
        
        # Use your existing Chrome profile (where you're logged in)
        # On macOS, Chrome profile is usually at:
        # ~/Library/Application Support/Google/Chrome/Default
        chrome_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        chrome_profile_path = os.path.join(chrome_data_dir, "Default")
        
        if self.use_profile and os.path.exists(chrome_data_dir):
            chrome_options.add_argument(f"--user-data-dir={chrome_data_dir}")
            chrome_options.add_argument("--profile-directory=Default")
            print(f"✓ Using Chrome profile: {chrome_profile_path}")
        else:
            if not self.use_profile:
                print("⚠️  Using temporary profile (not logged in)")
            else:
                print("⚠️  Chrome profile not found. Using temporary profile.")
                print("   You may need to login manually in the browser.")
        
        # Other options
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Try to use system Chrome
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✓ Chrome driver initialized")
                return
            except Exception as e:
                error_msg = str(e)
                if "session not created" in error_msg.lower() or "chrome instance exited" in error_msg.lower():
                    if attempt == 0 and self.use_profile:
                        print(f"⚠️  Failed to use Chrome profile (attempt {attempt + 1}/{max_retries})")
                        print("   Trying with temporary profile instead...")
                        # Retry without profile
                        chrome_options = Options()
                        if self.headless:
                            chrome_options.add_argument("--headless")
                        chrome_options.add_argument("--no-sandbox")
                        chrome_options.add_argument("--disable-dev-shm-usage")
                        self.use_profile = False
                        continue
                    else:
                        print(f"\n✗ Error initializing Chrome driver: {e}")
                        print("\nTroubleshooting:")
                        print("1. Make sure Chrome is completely closed:")
                        print("   killall 'Google Chrome'")
                        print("2. Or try running the script with Chrome already closed")
                        print("3. Make sure ChromeDriver matches your Chrome version")
                        raise
                else:
                    print(f"\n✗ Error: {e}")
                    raise
    
    def extract_article_content(self, url: str) -> dict:
        """Extract article content from URL using browser."""
        if not self.driver:
            self.setup_driver()
        
        print(f"\nAccessing: {url}")
        
        try:
            # Navigate to the article
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait a bit more for dynamic content
            import time
            time.sleep(3)
            
            # Try to find article content
            # Different sites use different selectors
            content_selectors = [
                "article",
                "main article",
                "[role='article']",
                ".article-body",
                ".article-content",
                ".story-body",
                ".post-content",
                "main",
            ]
            
            article_element = None
            for selector in content_selectors:
                try:
                    article_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if article_element:
                        print(f"  Found content using selector: {selector}")
                        break
                except NoSuchElementException:
                    continue
            
            if not article_element:
                # Fallback: get body content
                article_element = self.driver.find_element(By.TAG_NAME, "body")
                print("  Using body as fallback")
            
            # Extract text content
            content = article_element.text
            
            # Try to get title
            title = ""
            title_selectors = ["h1", ".article-title", "title", "[itemprop='headline']"]
            for selector in title_selectors:
                try:
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except:
                    continue
            
            if not title:
                title = self.driver.title
            
            # Try to get author
            author = ""
            author_selectors = [
                "[itemprop='author']",
                ".byline",
                ".author",
                "[rel='author']"
            ]
            for selector in author_selectors:
                try:
                    author_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip()
                    if author:
                        # Clean up author text
                        author = re.sub(r'^By\s+', '', author, flags=re.IGNORECASE)
                        author = author.split(',')[0].split('|')[0].strip()
                        break
                except:
                    continue
            
            # Get source from URL
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            source_names = {
                'wsj.com': 'The Wall Street Journal',
                'nytimes.com': 'The New York Times',
                'ft.com': 'Financial Times',
                'bloomberg.com': 'Bloomberg',
                'washingtonpost.com': 'The Washington Post',
                'economist.com': 'The Economist',
            }
            source = source_names.get(domain, domain)
            
            return {
                'content': content,
                'title': title,
                'author': author,
                'source': source,
                'url': url,
            }
            
        except Exception as e:
            print(f"  Error extracting content: {e}")
            return None
    
    def process_article(self, url: str) -> dict:
        """Process a paywall article URL."""
        # Extract content using browser
        article_data = self.extract_article_content(url)
        
        if not article_data or not article_data.get('content'):
            print("  Failed to extract content")
            return None
        
        print(f"  Extracted {len(article_data['content'])} characters")
        print(f"  Title: {article_data['title'][:60]}...")
        
        # Generate ID
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        date_str = datetime.now().strftime('%Y-%m-%d')
        article_id = f"news_{date_str}_{url_hash}"
        
        # Generate summary
        content = article_data['content']
        summary = self.scraper.generate_summary(content, article_data['title'])
        
        # Detect tags
        tags = self.scraper._detect_tags(article_data['title'], content)
        
        # Mark as paywall
        has_paywall = True
        
        # Build article record
        article = {
            'id': article_id,
            'date': date_str,
            'title': article_data['title'],
            'source': article_data['source'],
            'source_url': url,
            'author': article_data.get('author', ''),
            'summary': summary,
            'tags': tags,
            'has_paywall': has_paywall,
            'scraped_at': datetime.now().isoformat(),
        }
        
        # Save as HTML
        article['content'] = content
        html_path = self.scraper.save_as_html(article)
        article['html_path'] = html_path
        del article['content']
        
        return article
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            print("\n✓ Browser closed")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python browser_paywall_scraper.py <article_url>")
        print("\nExample:")
        print("  python browser_paywall_scraper.py https://www.wsj.com/articles/...")
        sys.exit(1)
    
    url = sys.argv[1]
    
    scraper = BrowserPaywallScraper(headless=False)  # Show browser so you can see it
    
    try:
        article = scraper.process_article(url)
        
        if article:
            # Update news.json
            news_json_path = 'data/news.json'
            news_list = []
            if os.path.exists(news_json_path):
                with open(news_json_path, 'r', encoding='utf-8') as f:
                    news_list = json.load(f)
            
            # Check if article already exists
            existing_idx = None
            for i, existing in enumerate(news_list):
                if existing.get('source_url') == url:
                    existing_idx = i
                    break
            
            if existing_idx is not None:
                # Update existing
                news_list[existing_idx].update(article)
                print(f"\n✓ Updated existing article in news.json")
            else:
                # Add new
                news_list.insert(0, article)
                print(f"\n✓ Added new article to news.json")
            
            # Save
            news_list.sort(key=lambda x: x.get('date', ''), reverse=True)
            with open(news_json_path, 'w', encoding='utf-8') as f:
                json.dump(news_list, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Article saved: {article['html_path']}")
        else:
            print("\n✗ Failed to process article")
            
    finally:
        scraper.close()


if __name__ == '__main__':
    main()
