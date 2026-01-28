#!/usr/bin/env python3
"""
Browser-assisted article scraper.
Use this to manually fetch articles from paywalled sites that you're logged into.

Usage:
1. Open the article in Chrome
2. Run: python browser_scraper.py <article_url>
3. The script will fetch content from your browser and save it locally
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime
from urllib.parse import urlparse

# Import the main scraper for HTML generation
from news_scraper import NewsScraper


def clean_content(raw_text: str) -> str:
    """Clean the raw text extracted from browser."""
    # Remove common navigation/footer patterns
    lines = raw_text.split('\n')
    cleaned_lines = []

    skip_patterns = [
        'Sign up', 'Subscribe', 'Newsletter', 'Read Next',
        'Suggested Topics', 'Share', 'Facebook', 'Twitter', 'LinkedIn',
        'Purchase Licensing', 'Our Standards', 'Trust Principles',
        'Get a daily digest', 'Sign up here'
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that are just navigation/social
        if any(pattern in line for pattern in skip_patterns):
            continue
        # Skip very short lines that are likely buttons
        if len(line) < 20 and any(c in line for c in ['>', '<', '|']):
            continue
        cleaned_lines.append(line)

    return '\n\n'.join(cleaned_lines)


def extract_article_from_text(raw_text: str, url: str) -> dict:
    """Extract article metadata and content from raw text."""
    lines = raw_text.split('\n')

    # First line is usually the title
    title = lines[0] if lines else 'Untitled'

    # Try to find author and date
    author = ''
    date_str = datetime.now().strftime('%Y-%m-%d')

    for line in lines[:10]:
        if 'By ' in line:
            author_match = re.search(r'By\s+([^,\n]+)', line)
            if author_match:
                author = author_match.group(1).strip()

        # Look for date patterns
        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', line)
        if date_match:
            try:
                parsed = datetime.strptime(date_match.group(), '%B %d, %Y')
                date_str = parsed.strftime('%Y-%m-%d')
            except:
                try:
                    parsed = datetime.strptime(date_match.group(), '%B %d %Y')
                    date_str = parsed.strftime('%Y-%m-%d')
                except:
                    pass

    # Get domain as source
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[4:]

    source_names = {
        'reuters.com': 'Reuters',
        'bloomberg.com': 'Bloomberg',
        'wsj.com': 'The Wall Street Journal',
        'nytimes.com': 'The New York Times',
        'ft.com': 'Financial Times',
        'axios.com': 'Axios',
    }
    source = source_names.get(domain, domain)

    # Clean the content
    content = clean_content(raw_text)

    return {
        'title': title,
        'author': author,
        'date': date_str,
        'source': source,
        'content': content,
        'url': url,
    }


def update_news_json(article_data: dict, html_path: str):
    """Update news.json with the new article or update existing."""
    news_json_path = 'data/news.json'

    # Load existing news
    news_list = []
    if os.path.exists(news_json_path):
        with open(news_json_path, 'r', encoding='utf-8') as f:
            news_list = json.load(f)

    # Find if article already exists (by URL or similar title)
    url = article_data['url']
    existing_idx = None

    for i, article in enumerate(news_list):
        # Match by source_url containing similar path
        if article.get('source_url') and url in article.get('source_url', ''):
            existing_idx = i
            break
        # Or match by exact URL
        if article.get('source_url') == url:
            existing_idx = i
            break

    if existing_idx is not None:
        # Update existing article
        news_list[existing_idx]['html_path'] = html_path
        news_list[existing_idx]['summary'] = article_data['content'][:300] + '...'
        # Mark as paywall if from known paywall domains or sources
        paywall_domains = ['wsj.com', 'nytimes.com', 'ft.com', 'bloomberg.com', 'washingtonpost.com', 'economist.com']
        paywall_source_patterns = [
            'wall street journal', 'wsj', 'the wall street journal',
            'new york times', 'nytimes', 'ny times', 'the new york times',
            'financial times', 'ft.com', 'the financial times',
            'bloomberg', 'bloomberg news',
            'washington post', 'wapo', 'the washington post',
            'economist', 'the economist'
        ]
        
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        source_lower = article_data.get('source', '').lower()
        news_list[existing_idx]['has_paywall'] = (
            any(pd in domain for pd in paywall_domains) or
            any(pattern in source_lower for pattern in paywall_source_patterns)
        )
        print(f"Updated existing article at index {existing_idx}")
    else:
        # Add new article
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        article_id = f"news_{article_data['date']}_{url_hash}"

        # Mark as paywall if from known paywall domains or sources
        paywall_domains = ['wsj.com', 'nytimes.com', 'ft.com', 'bloomberg.com', 'washingtonpost.com', 'economist.com']
        paywall_source_patterns = [
            'wall street journal', 'wsj', 'the wall street journal',
            'new york times', 'nytimes', 'ny times', 'the new york times',
            'financial times', 'ft.com', 'the financial times',
            'bloomberg', 'bloomberg news',
            'washington post', 'wapo', 'the washington post',
            'economist', 'the economist'
        ]
        
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        source_lower = article_data.get('source', '').lower()
        has_paywall = (
            any(pd in domain for pd in paywall_domains) or
            any(pattern in source_lower for pattern in paywall_source_patterns)
        )

        new_entry = {
            'id': article_id,
            'date': article_data['date'],
            'title': article_data['title'],
            'source': article_data['source'],
            'source_url': url,
            'author': article_data['author'],
            'summary': article_data['content'][:300] + '...',
            'tags': [],
            'has_paywall': has_paywall,
            'scraped_at': datetime.now().isoformat(),
            'html_path': html_path,
        }
        news_list.insert(0, new_entry)
        print(f"Added new article: {article_id}")

    # Sort by date
    news_list.sort(key=lambda x: x.get('date', ''), reverse=True)

    # Save
    with open(news_json_path, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, indent=2, ensure_ascii=False)


def save_article_html(article_data: dict) -> str:
    """Save article as HTML file."""
    scraper = NewsScraper()

    # Generate ID
    url_hash = hashlib.md5(article_data['url'].encode()).hexdigest()[:8]
    article_id = f"news_{article_data['date']}_{url_hash}"

    article = {
        'id': article_id,
        'title': article_data['title'],
        'source': article_data['source'],
        'date': article_data['date'],
        'author': article_data['author'],
        'summary': article_data['content'][:300] + '...',
        'content': article_data['content'],
        'source_url': article_data['url'],
    }

    html_path = scraper.save_as_html(article)
    return html_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python browser_scraper.py <url> <raw_text_file>")
        print("")
        print("This script processes article content that you've extracted from your browser.")
        print("1. Copy the article text from your browser")
        print("2. Save it to a text file")
        print("3. Run this script with the URL and text file path")
        sys.exit(1)

    url = sys.argv[1]
    text_file = sys.argv[2]

    # Read the raw text
    with open(text_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    print(f"Processing article from: {url}")

    # Extract article data
    article_data = extract_article_from_text(raw_text, url)
    print(f"Title: {article_data['title']}")
    print(f"Author: {article_data['author']}")
    print(f"Date: {article_data['date']}")
    print(f"Source: {article_data['source']}")
    print(f"Content length: {len(article_data['content'])} chars")

    # Save as HTML
    html_path = save_article_html(article_data)
    print(f"Saved HTML to: {html_path}")

    # Update news.json
    update_news_json(article_data, html_path)
    print("Updated news.json")

    print("\nDone! Refresh the news page to see the updated article.")


if __name__ == '__main__':
    main()
