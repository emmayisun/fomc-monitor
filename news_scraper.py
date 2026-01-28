#!/usr/bin/env python3
"""
Fed News Scraper - Automatically fetches Fed-related news from Google News,
filters by whitelist domains, extracts content, and generates AI summaries.
"""

import os
import re
import json
import hashlib
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

# Optional imports with fallbacks
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("Warning: feedparser not installed.")

try:
    from GoogleNews import GoogleNews
    HAS_GOOGLENEWS = True
except ImportError:
    HAS_GOOGLENEWS = False
    print("Warning: GoogleNews not installed. Using RSS fallback.")

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    print("Warning: trafilatura not installed. Using basic extraction.")

try:
    from googlenewsdecoder import new_decoderv1
    HAS_GNEWS_DECODER = True
except ImportError:
    HAS_GNEWS_DECODER = False
    print("Warning: googlenewsdecoder not installed. URL resolution may fail.")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: openai not installed. Summaries will be disabled.")


class NewsScraper:
    """Scrapes Fed-related news from various sources."""

    # Whitelist of allowed domains
    ALLOWED_DOMAINS = [
        'bloomberg.com',
        'reuters.com',
        'cnbc.com',
        'wsj.com',
        'ft.com',
        'politico.com',
        'marketwatch.com',
        'federalreserve.gov',
        'nytimes.com',
        'washingtonpost.com',
        'yahoo.com',
        'barrons.com',
        'economist.com',
        'businessinsider.com',
        'fortune.com',
        'axios.com',
    ]

    # Search queries for Fed news
    SEARCH_QUERIES = [
        'Federal Reserve',
        'Fed Powell',
        'FOMC meeting',
        'Fed interest rate decision',
        'Federal Reserve monetary policy',
    ]

    # Data directories
    DATA_DIR = 'data'
    NEWS_DIR = 'data/news'
    NEWS_JSON = 'data/news.json'

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the scraper."""
        self.openai_api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        self.openai_client = None

        if HAS_OPENAI and self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)

        # Ensure directories exist
        os.makedirs(self.NEWS_DIR, exist_ok=True)

        # Load existing news
        self.existing_news = self._load_existing_news()

    def _load_existing_news(self) -> List[Dict]:
        """Load existing news from JSON file."""
        if os.path.exists(self.NEWS_JSON):
            try:
                with open(self.NEWS_JSON, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_news(self, news_list: List[Dict]):
        """Save news list to JSON file."""
        # Sort by date descending
        news_list.sort(key=lambda x: x.get('date', ''), reverse=True)

        with open(self.NEWS_JSON, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, indent=2, ensure_ascii=False)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def _is_whitelisted(self, url: str, source_domain: str = '') -> bool:
        """Check if URL is from a whitelisted domain."""
        # First check source_domain if provided (from RSS feed)
        if source_domain:
            if any(allowed in source_domain for allowed in self.ALLOWED_DOMAINS):
                return True

        # Then check URL domain
        domain = self._get_domain(url)
        return any(allowed in domain for allowed in self.ALLOWED_DOMAINS)

    def _generate_id(self, url: str) -> str:
        """Generate unique ID for an article based on URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f"news_{date_str}_{url_hash}"

    def _url_exists(self, url: str) -> bool:
        """Check if URL already exists in our database."""
        for news in self.existing_news:
            if news.get('source_url') == url:
                return True
        return False

    def search_google_news(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search Google News for articles matching query."""
        articles = []

        if HAS_GOOGLENEWS:
            try:
                googlenews = GoogleNews(lang='en', period='7d')
                googlenews.search(query)
                results = googlenews.results()

                for result in results[:num_results]:
                    article = {
                        'title': result.get('title', ''),
                        'url': result.get('link', ''),
                        'source': result.get('media', ''),
                        'date': result.get('date', ''),
                        'description': result.get('desc', ''),
                    }
                    if article['url'] and article['title']:
                        articles.append(article)

                googlenews.clear()
            except Exception as e:
                print(f"Error searching Google News: {e}")
        else:
            # Fallback to Google News RSS
            articles = self._search_google_news_rss(query, num_results)

        return articles

    def _resolve_google_news_url(self, google_url: str) -> str:
        """Resolve Google News redirect URL to actual article URL."""
        # Try googlenewsdecoder first (most reliable)
        if HAS_GNEWS_DECODER:
            try:
                result = new_decoderv1(google_url)
                if result and result.get('status') and result.get('decoded_url'):
                    return result['decoded_url']
            except Exception as e:
                print(f"    googlenewsdecoder failed: {e}")

        # Fallback to HTTP redirect following
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            response = requests.get(google_url, headers=headers, timeout=15, allow_redirects=True)
            final_url = response.url

            if 'news.google.com' not in final_url:
                return final_url

        except Exception as e:
            pass

        return google_url

    def _search_google_news_rss(self, query: str, num_results: int = 10) -> List[Dict]:
        """Fallback: Search Google News via RSS feed using feedparser."""
        articles = []

        if not HAS_FEEDPARSER:
            print("feedparser not available, using basic RSS parsing")
            return self._search_google_news_rss_basic(query, num_results)

        try:
            # Google News RSS URL
            encoded_query = requests.utils.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:num_results]:
                # Get source domain from entry.source.href
                source_domain = ''
                if hasattr(entry, 'source') and hasattr(entry.source, 'href'):
                    source_domain = self._get_domain(entry.source.href)

                # Get source name
                source_name = ''
                if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                    source_name = entry.source.title

                # Clean description of any HTML
                description = entry.summary if hasattr(entry, 'summary') else ''
                if description:
                    description = re.sub(r'<[^>]+>', '', description)
                    # Replace HTML entities
                    description = description.replace('&nbsp;', ' ')
                    description = description.replace('&amp;', '&')
                    description = description.replace('&lt;', '<')
                    description = description.replace('&gt;', '>')
                    description = ' '.join(description.split())

                article = {
                    'title': entry.title if hasattr(entry, 'title') else '',
                    'url': entry.link if hasattr(entry, 'link') else '',
                    'source': source_name,
                    'source_domain': source_domain,
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'description': description,
                }
                articles.append(article)

        except Exception as e:
            print(f"Error fetching RSS: {e}")

        return articles

    def _search_google_news_rss_basic(self, query: str, num_results: int = 10) -> List[Dict]:
        """Basic RSS parsing fallback."""
        articles = []

        try:
            encoded_query = requests.utils.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(rss_url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')

            for item in items[:num_results]:
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                source = item.find('source')

                source_url = source.get('url', '') if source else ''

                if title and link:
                    article = {
                        'title': title.text.strip() if title else '',
                        'url': link.text.strip() if link else '',
                        'source': source.text.strip() if source else '',
                        'source_domain': self._get_domain(source_url) if source_url else '',
                        'date': pub_date.text.strip() if pub_date else '',
                        'description': '',
                    }
                    articles.append(article)

        except Exception as e:
            print(f"Error fetching RSS: {e}")

        return articles

    def fetch_article_content(self, url: str) -> Optional[Dict]:
        """Fetch and extract article content from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            content = None
            title = None
            author = None

            if HAS_TRAFILATURA:
                # Use trafilatura for better extraction
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    content = trafilatura.extract(downloaded, include_comments=False)

                    # Also get metadata
                    metadata = trafilatura.extract_metadata(downloaded)
                    if metadata:
                        title = metadata.title
                        author = metadata.author

            if not content:
                # Fallback to basic extraction
                soup = BeautifulSoup(response.text, 'html.parser')

                # Try to find article content
                article = soup.find('article') or soup.find('main') or soup.find('body')

                if article:
                    # Remove scripts, styles, nav, footer
                    for tag in article.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                        tag.decompose()

                    # Get text content - preserve paragraph structure
                    paragraphs = article.find_all('p')
                    # Filter out very short paragraphs (likely navigation/footer)
                    content_paragraphs = []
                    for p in paragraphs:
                        text = p.get_text().strip()
                        # Skip very short paragraphs (likely navigation/buttons)
                        if len(text) > 20:
                            content_paragraphs.append(text)
                    content = '\n\n'.join(content_paragraphs)

                # Get title
                title_tag = soup.find('title') or soup.find('h1')
                if title_tag:
                    title = title_tag.get_text().strip()

                # Try to find author
                author_meta = soup.find('meta', {'name': 'author'})
                if author_meta:
                    author = author_meta.get('content')

            if content:
                return {
                    'content': content,
                    'title': title,
                    'author': author,
                }

        except Exception as e:
            print(f"Error fetching article {url}: {e}")

        return None

    def generate_summary(self, content: str, title: str = '') -> str:
        """Generate AI summary of article content."""
        if not self.openai_client:
            # Fallback: Generate a simple summary from first few sentences
            # Try to find the first 2-3 complete sentences
            sentences = re.split(r'[.!?]+\s+', content)
            # Filter out very short sentences (likely fragments)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            
            if len(sentences) >= 2:
                # Take first 2-3 sentences, up to 300 chars
                summary_parts = []
                total_length = 0
                for sentence in sentences[:3]:
                    if total_length + len(sentence) < 300:
                        summary_parts.append(sentence)
                        total_length += len(sentence) + 1
                    else:
                        break
                summary = '. '.join(summary_parts)
                if summary and not summary.endswith('.'):
                    summary += '.'
                return summary if summary else content[:300] + '...'
            else:
                # Fallback to first 300 chars
                return content[:300] + '...' if len(content) > 300 else content

        try:
            # Truncate content if too long
            max_content_length = 8000
            if len(content) > max_content_length:
                content = content[:max_content_length] + '...'

            prompt = f"""Summarize this Federal Reserve/monetary policy news article in 2-3 sentences.
Focus on the key policy implications and market impact.

Title: {title}

Article:
{content}

Summary:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial news summarizer. Provide concise, factual summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error generating summary: {e}")
            return content[:300] + '...' if len(content) > 300 else content

    def save_as_html(self, article: Dict) -> str:
        """Save article as HTML file with consistent styling."""
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #ffffff;
    color: #1a1a1a;
    line-height: 1.7;
    max-width: 700px;
    margin: 0 auto;
    padding: 40px 24px;
    -webkit-font-smoothing: antialiased;
}}
.back-link {{
    display: inline-block;
    margin-bottom: 32px;
    color: #666;
    text-decoration: none;
    font-size: 14px;
    transition: color 0.2s;
}}
.back-link:hover {{
    color: #1a1a1a;
}}
.article-header {{
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid #e5e7eb;
}}
.article-title {{
    font-size: 28px;
    font-weight: 600;
    line-height: 1.3;
    margin-bottom: 16px;
    color: #1a1a1a;
}}
.article-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 14px;
    color: #666;
}}
.article-meta a {{
    color: #666;
    text-decoration: none;
}}
.article-meta a:hover {{
    color: #1a1a1a;
}}
.article-source {{
    font-weight: 500;
}}
.article-summary {{
    background: #f9fafb;
    border-left: 3px solid #1a1a1a;
    padding: 16px 20px;
    margin-bottom: 32px;
    font-size: 15px;
    color: #374151;
}}
.article-summary-label {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6b7280;
    margin-bottom: 8px;
}}
.article-content {{
    font-size: 16px;
    line-height: 1.8;
}}
.article-content p {{
    margin-bottom: 20px;
}}
.original-link {{
    display: inline-block;
    margin-top: 32px;
    padding: 12px 24px;
    background: #1a1a1a;
    color: #fff;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: background 0.2s;
}}
.original-link:hover {{
    background: #333;
}}
</style>
</head>
<body>
<a href="/news.html" class="back-link">← Back to News</a>

<article>
    <header class="article-header">
        <h1 class="article-title">{title}</h1>
        <div class="article-meta">
            <span class="article-source">{source}</span>
            <span class="article-date">{date}</span>
            {author_html}
        </div>
    </header>

    <div class="article-summary">
        <div class="article-summary-label">Summary</div>
        {summary}
    </div>

    <div id="paywall-notice" style="display: none; background: #fff3cd; border: 1px solid #ffc107; padding: 20px; margin-bottom: 32px; border-radius: 0;">
        <h3 style="font-size: 18px; margin-bottom: 12px; color: #856404;">🔒 Member-Only Content</h3>
        <p style="color: #856404; margin-bottom: 16px;">This article is behind a paywall. Full content is available to members only.</p>
        <a href="/login.html" style="display: inline-block; padding: 10px 20px; background: #1a1a1a; color: #fff; text-decoration: none; font-size: 14px; font-weight: 500;">Login or Register to View</a>
    </div>

    <div id="article-content" class="article-content">
        {content}
    </div>

    <a href="{source_url}" target="_blank" rel="noopener noreferrer" class="original-link">
        Read Original Article →
    </a>
    
    <script src="/auth.js"></script>
    <script>
        (function() {{
            // Temporarily disable auth - all content visible
            const hasPaywall = {has_paywall};
            const isMember = true; // authManager && authManager.isMember();
            
            if (hasPaywall && !isMember) {{
                // Hide content, show paywall notice
                document.getElementById('article-content').style.display = 'none';
                document.getElementById('paywall-notice').style.display = 'block';
            }}
        }})();
    </script>
</article>
</body>
</html>'''

        # Format content as paragraphs
        content_text = article.get('content', '')
        
        # Split by double newlines first (paragraph breaks)
        paragraphs = content_text.split('\n\n')
        
        # If content doesn't have proper paragraph breaks, try to split intelligently
        # This handles cases where trafilatura or extraction merged everything
        if len(paragraphs) == 1 and len(content_text) > 500:
            import re
            # Split on sentence endings (period, exclamation, question mark)
            # followed by space and capital letter (likely new paragraph)
            # Pattern: sentence ending + space + capital letter (but not after abbreviations)
            sentence_endings = re.finditer(r'([.!?]+)\s+([A-Z][a-z])', content_text)
            
            split_points = [0]
            for match in sentence_endings:
                # Check if this looks like a paragraph break (not just a sentence)
                # Look for patterns that suggest new paragraph:
                # - Long sentence before (> 100 chars)
                # - Capital word after that's not an abbreviation
                pos = match.start()
                before = content_text[max(0, pos-100):pos]
                after_word = match.group(2)
                
                # If the sentence before is substantial, this might be a paragraph break
                if len(before.strip()) > 80:
                    split_points.append(match.end() - len(after_word))
            
            split_points.append(len(content_text))
            
            # Create paragraphs from split points
            formatted_paragraphs = []
            for i in range(len(split_points) - 1):
                para = content_text[split_points[i]:split_points[i+1]].strip()
                # Clean up: remove leading punctuation fragments
                para = re.sub(r'^[.!?\s]+', '', para)
                if para and len(para) > 50:  # Only keep substantial paragraphs
                    # Remove extra whitespace
                    para = ' '.join(para.split())
                    formatted_paragraphs.append(para)
            
            paragraphs = formatted_paragraphs if formatted_paragraphs else paragraphs
        
        # Clean and format each paragraph
        formatted_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:  # Skip very short fragments
                # Remove extra whitespace within paragraph
                para = ' '.join(para.split())
                formatted_paragraphs.append(f'<p>{para}</p>')
        
        formatted_content = '\n        '.join(formatted_paragraphs)

        # Format author
        author = article.get('author', '')
        author_html = f'<span class="article-author">By {author}</span>' if author else ''

        has_paywall = article.get('has_paywall', False)
        
        html = html_template.format(
            title=article.get('title', 'Untitled'),
            source=article.get('source', 'Unknown'),
            date=article.get('date', ''),
            author_html=author_html,
            summary=article.get('summary', ''),
            content=formatted_content,
            source_url=article.get('source_url', '#'),
            has_paywall='true' if has_paywall else 'false',
        )

        # Save file
        article_id = article.get('id', self._generate_id(article.get('source_url', '')))
        filename = f"{article_id}.html"
        filepath = os.path.join(self.NEWS_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return f"data/news/{filename}"

    def _detect_tags(self, title: str, content: str) -> List[str]:
        """Detect relevant tags based on content."""
        text = (title + ' ' + content).lower()
        tags = []

        tag_keywords = {
            'Interest Rates': ['interest rate', 'rate cut', 'rate hike', 'fed funds', 'basis point'],
            'Inflation': ['inflation', 'cpi', 'pce', 'price stability', 'disinflation'],
            'Employment': ['employment', 'jobs', 'unemployment', 'labor market', 'payroll'],
            'Powell': ['powell', 'chair powell', 'fed chair'],
            'FOMC': ['fomc', 'federal open market'],
            'QT': ['quantitative tightening', 'balance sheet', 'qt'],
            'Banking': ['bank', 'banking', 'svb', 'regional bank'],
            'Markets': ['stock', 'bond', 'treasury', 'yield', 'market'],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        return tags[:5]  # Limit to 5 tags

    def process_article(self, article_info: Dict) -> Optional[Dict]:
        """Process a single article: fetch content, generate summary, save HTML."""
        url = article_info.get('url', '')
        source_domain = article_info.get('source_domain', '')
        google_news_url = url  # Keep original for link

        if not url:
            return None

        # Check whitelist using source_domain from RSS
        if not self._is_whitelisted(url, source_domain):
            print(f"  Skipping (not whitelisted): {source_domain or self._get_domain(url)}")
            return None

        # Use Google News URL as unique identifier for dedup
        if self._url_exists(url):
            print(f"  Skipping (already exists)")
            return None

        print(f"  Processing: {article_info.get('title', '')[:50]}...")

        # Try to resolve and fetch content
        actual_url = url
        if 'news.google.com' in url:
            print(f"    Resolving Google News URL...")
            actual_url = self._resolve_google_news_url(url)

        # Fetch full content
        article_data = self.fetch_article_content(actual_url)

        # If content extraction failed, create article with just metadata
        if not article_data or not article_data.get('content'):
            print(f"    Using description as summary (content extraction failed)")
            article_data = {
                'content': article_info.get('description', ''),
                'title': article_info.get('title', ''),
                'author': '',
            }

        # Use fetched title if original is missing
        title = article_info.get('title') or article_data.get('title') or 'Untitled'
        # Clean up title (remove " - Source" suffix from Google News)
        if ' - ' in title:
            title = title.rsplit(' - ', 1)[0]

        # Generate summary
        content = article_data.get('content', '')
        if content and len(content) > 50:
            summary = self.generate_summary(content, title)
        else:
            # Clean description of any HTML
            description = article_info.get('description', '')
            if description:
                # Remove HTML tags
                description = re.sub(r'<[^>]+>', '', description)
                # Clean up whitespace
                description = ' '.join(description.split())
                # Try to extract first 2-3 sentences for better summary
                sentences = re.split(r'[.!?]+\s+', description)
                sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
                if len(sentences) >= 2:
                    summary = '. '.join(sentences[:2])
                    if summary and not summary.endswith('.'):
                        summary += '.'
                else:
                    summary = description[:300] + '...' if len(description) > 300 else description
            else:
                summary = 'No summary available.'

        # Parse date
        date_str = article_info.get('date', '')
        try:
            # Try to parse various date formats
            if date_str:
                # Handle relative dates like "1 hour ago"
                if 'ago' in date_str.lower():
                    date_str = datetime.now().strftime('%Y-%m-%d')
                else:
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%b %d, %Y', '%B %d, %Y', '%d %b %Y']:
                        try:
                            parsed = datetime.strptime(date_str, fmt)
                            date_str = parsed.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
        except Exception:
            date_str = datetime.now().strftime('%Y-%m-%d')

        if not date_str or len(date_str) != 10:
            date_str = datetime.now().strftime('%Y-%m-%d')

        # Detect tags
        tags = self._detect_tags(title, article_data['content'])

        # Detect paywall - check if content is very short (likely paywalled)
        # or if source is known paywall site
        paywall_domains = ['wsj.com', 'nytimes.com', 'ft.com', 'bloomberg.com', 'washingtonpost.com', 'economist.com']
        paywall_source_patterns = [
            'wall street journal', 'wsj', 'the wall street journal',
            'new york times', 'nytimes', 'ny times', 'the new york times',
            'financial times', 'ft.com', 'the financial times',
            'bloomberg', 'bloomberg news',
            'washington post', 'wapo', 'the washington post',
            'economist', 'the economist'
        ]
        
        source_name = article_info.get('source', '').lower()
        domain = self._get_domain(url)
        
        # Check content length - if very short, likely paywalled
        # Also check for common paywall indicators in content
        content_length = len(content) if content else 0
        has_short_content = content_length < 500  # Increased threshold for better detection
        
        # Check for paywall indicators in content (common paywall messages)
        paywall_indicators = [
            'subscribe to read', 'sign up to continue', 'create a free account',
            'you have reached your', 'free articles remaining', 'register to read',
            'this article is for subscribers', 'unlock this article'
        ]
        has_paywall_message = False
        if content:
            content_lower = content.lower()
            has_paywall_message = any(indicator in content_lower for indicator in paywall_indicators)
        
        has_paywall = (
            domain in paywall_domains or
            any(pattern in source_name for pattern in paywall_source_patterns) or
            (has_short_content and content_length > 0) or  # Very short content likely paywalled
            has_paywall_message  # Contains paywall messages
        )

        # Build article record
        article = {
            'id': self._generate_id(url),
            'date': date_str,
            'title': title,
            'source': article_info.get('source', self._get_domain(url)),
            'source_url': google_news_url,  # Use Google News URL for linking
            'author': article_data.get('author', ''),
            'summary': summary,
            'tags': tags,
            'has_paywall': has_paywall,
            'scraped_at': datetime.now().isoformat(),
        }

        # Only save as HTML if we have actual content
        if content and len(content) > 100:
            article['content'] = content
            html_path = self.save_as_html(article)
            article['html_path'] = html_path
            del article['content']

        return article

    def run(self, max_articles: int = 20):
        """Run the full scraping pipeline."""
        print("=" * 60)
        print("Fed News Scraper")
        print("=" * 60)
        if not self.openai_client:
            print("⚠️  OpenAI API key not set. Using fallback summary generation.")
            print("   Set OPENAI_API_KEY environment variable for AI-powered summaries.\n")

        all_articles = []

        # Search for each query
        for query in self.SEARCH_QUERIES:
            print(f"\nSearching: {query}")
            results = self.search_google_news(query, num_results=10)
            print(f"  Found {len(results)} results")

            # Filter by whitelist - use source_domain from RSS feed
            whitelisted = [r for r in results if self._is_whitelisted(
                r.get('url', ''),
                r.get('source_domain', '')
            )]
            print(f"  {len(whitelisted)} from whitelisted sources")

            all_articles.extend(whitelisted)

            # Rate limiting
            time.sleep(2)

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        print(f"\n{len(unique_articles)} unique articles after deduplication")

        # Process articles
        new_articles = []
        for i, article_info in enumerate(unique_articles[:max_articles]):
            print(f"\n[{i+1}/{min(len(unique_articles), max_articles)}]")

            processed = self.process_article(article_info)
            if processed:
                new_articles.append(processed)

            # Rate limiting
            time.sleep(1)

        # Update news.json
        if new_articles:
            print(f"\n\nAdding {len(new_articles)} new articles to database")
            self.existing_news.extend(new_articles)
            self._save_news(self.existing_news)
        else:
            print("\n\nNo new articles to add")

        print(f"\nTotal articles in database: {len(self.existing_news)}")
        print("=" * 60)

        return new_articles


def main():
    """Main entry point."""
    scraper = NewsScraper()
    scraper.run(max_articles=15)


if __name__ == '__main__':
    main()
