#!/usr/bin/env python3
"""
Reformat existing article HTML files to fix paragraph structure.
"""

import os
import re
import json
from news_scraper import NewsScraper

def reformat_article_html(html_path):
    """Reformat a single article HTML file to fix paragraphs."""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extract content from the HTML
        content_match = re.search(r'<div class="article-content">(.*?)</div>', html_content, re.DOTALL)
        if not content_match:
            print(f"  Could not find content in {html_path}")
            return False
        
        old_content_html = content_match.group(1)
        
        # Extract text from existing paragraphs
        old_paragraphs = re.findall(r'<p>(.*?)</p>', old_content_html, re.DOTALL)
        
        if not old_paragraphs:
            print(f"  No paragraphs found in {html_path}")
            return False
        
        # Get the raw text (all paragraphs combined)
        raw_text = ' '.join(p.strip() for p in old_paragraphs)
        
        # Reformat using the same logic as save_as_html
        paragraphs = raw_text.split('\n\n')
        
        # If content doesn't have proper paragraph breaks, split intelligently
        if len(paragraphs) == 1 and len(raw_text) > 500:
            # Split on sentence endings followed by capital letters
            sentence_endings = re.finditer(r'([.!?]+)\s+([A-Z][a-z])', raw_text)
            
            split_points = [0]
            for match in sentence_endings:
                pos = match.start()
                before = raw_text[max(0, pos-100):pos]
                if len(before.strip()) > 80:
                    split_points.append(match.end() - len(match.group(2)))
            
            split_points.append(len(raw_text))
            
            # Create paragraphs from split points
            formatted_paragraphs = []
            for i in range(len(split_points) - 1):
                para = raw_text[split_points[i]:split_points[i+1]].strip()
                para = re.sub(r'^[.!?\s]+', '', para)
                if para and len(para) > 50:
                    para = ' '.join(para.split())
                    formatted_paragraphs.append(para)
            
            paragraphs = formatted_paragraphs if formatted_paragraphs else paragraphs
        
        # Format as HTML paragraphs
        formatted_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:
                para = ' '.join(para.split())
                formatted_paragraphs.append(f'<p>{para}</p>')
        
        new_content_html = '\n        '.join(formatted_paragraphs)
        
        # Replace the content in the HTML
        new_html = html_content.replace(old_content_html, '\n        ' + new_content_html + '\n    ')
        
        # Write back
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        
        print(f"  ✓ Reformatted {html_path} ({len(formatted_paragraphs)} paragraphs)")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing {html_path}: {e}")
        return False

def main():
    """Reformat all article HTML files."""
    scraper = NewsScraper()
    
    # Load news.json to get all articles
    news_json_path = 'data/news.json'
    if not os.path.exists(news_json_path):
        print("news.json not found")
        return
    
    with open(news_json_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Found {len(articles)} articles")
    print("Reformatting HTML files...\n")
    
    reformatted = 0
    for article in articles:
        html_path = article.get('html_path')
        if html_path and os.path.exists(html_path):
            if reformat_article_html(html_path):
                reformatted += 1
    
    print(f"\n✓ Reformatted {reformatted} articles")

if __name__ == '__main__':
    main()
