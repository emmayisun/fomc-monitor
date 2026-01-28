#!/usr/bin/env python3
"""
FOMC Press Conference Transcript Scraper
Downloads PDF files and converts them to HTML
"""

import requests
import os
import json
from datetime import datetime
from pathlib import Path
import pdfplumber
import re

class FOMCScraper:
    def __init__(self):
        self.base_url = "https://www.federalreserve.gov"
        self.data_dir = Path("data")
        self.pdfs_dir = self.data_dir / "pdfs"
        self.htmls_dir = self.data_dir / "htmls"
        self.data_file = self.data_dir / "transcripts.json"
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.pdfs_dir.mkdir(exist_ok=True)
        self.htmls_dir.mkdir(exist_ok=True)
        
        # Load existing data
        self.transcripts = self.load_data()
    
    def load_data(self):
        """Load existing transcripts data"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_data(self):
        """Save transcripts data to JSON"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.transcripts, f, indent=2, ensure_ascii=False)
    
    def find_pdf_url(self, date_str, title):
        """
        Find PDF URL for a given FOMC meeting date
        URL format: https://www.federalreserve.gov/mediacenter/files/FOMCpresconfYYYYMMDD.pdf
        """
        # Convert date from YYYY-MM-DD to YYYYMMDD
        year = date_str[:4]
        month = date_str[5:7]
        day = date_str[8:10]
        date_compact = f"{year}{month}{day}"
        
        # Primary URL pattern (most common format)
        primary_url = f"{self.base_url}/mediacenter/files/FOMCpresconf{date_compact}.pdf"
        
        # Try primary URL first
        try:
            response = requests.head(primary_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return primary_url
        except Exception as e:
            print(f"Error checking primary URL: {e}")
        
        # Try alternative patterns if primary fails
        patterns = [
            f"{self.base_url}/mediacenter/files/fomcpresconf{date_compact}.pdf",
            f"{self.base_url}/newsevents/pressreleases/monetary{date_compact}a1.pdf",
        ]
        
        for pattern in patterns:
            try:
                response = requests.head(pattern, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    return pattern
            except:
                continue
        
        return None
    
    def download_pdf(self, url, filename):
        """Download PDF file"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            filepath = self.pdfs_dir / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filepath
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return None
    
    def pdf_to_html(self, pdf_path, html_filename):
        """Convert PDF to HTML"""
        try:
            html_content = []
            html_content.append('<!DOCTYPE html>')
            html_content.append('<html lang="en">')
            html_content.append('<head>')
            html_content.append('<meta charset="UTF-8">')
            html_content.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
            html_content.append('<title>FOMC Press Conference Transcript</title>')
            html_content.append('<style>')
            html_content.append('''
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    background: #ffffff;
                    color: #1a1a1a;
                    line-height: 1.6;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 40px 48px;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }
                .back-link { 
                    display: inline-block; 
                    margin-bottom: 40px; 
                    color: #666; 
                    text-decoration: none;
                    font-size: 15px;
                    font-weight: 400;
                    transition: color 0.2s;
                }
                .back-link:hover { 
                    color: #1a1a1a; 
                }
                .speaker { 
                    font-weight: 600; 
                    color: #1a1a1a; 
                    margin-top: 32px; 
                    margin-bottom: 8px;
                    font-size: 15px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .question { 
                    color: #666; 
                    margin-left: 0;
                    border-left: 2px solid #1a1a1a;
                    padding-left: 16px;
                    margin-top: 8px;
                    margin-bottom: 16px;
                    font-size: 15px;
                    line-height: 1.7;
                }
                .answer {
                    margin-left: 0;
                    color: #1a1a1a;
                    margin-top: 8px;
                    margin-bottom: 16px;
                    font-size: 15px;
                    line-height: 1.7;
                }
                p {
                    margin: 0;
                }
            ''')
            html_content.append('</style>')
            html_content.append('</head>')
            html_content.append('<body>')
            html_content.append('<a href="/index.html" class="back-link">← Back to List</a>')
            
            # Extract all text from PDF
            full_text = []
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
            
            # Combine all pages and process
            combined_text = '\n'.join(full_text)
            # Clean and format text
            cleaned_text = self.clean_text(combined_text)
            # Convert to HTML paragraphs
            paragraphs = self.text_to_html_paragraphs(cleaned_text)
            html_content.extend(paragraphs)
            
            html_content.append('</body>')
            html_content.append('</html>')
            
            html_path = self.htmls_dir / html_filename
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(html_content))
            
            return html_path
        except Exception as e:
            print(f"Error converting PDF to HTML: {e}")
            return None
    
    def clean_text(self, text):
        """Clean extracted text and remove headers/footers"""
        if not text:
            return ""
        
        # IMPORTANT: Only remove headers that appear at the start or as page headers
        # Do NOT remove content that appears before the first speaker
        months = r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        
        # Find the first speaker (usually CHAIR POWELL or similar)
        first_speaker_match = re.search(r'([A-Z][A-Z\s]{2,}\.)\s+', text)
        if first_speaker_match:
            # Only clean text before the first speaker (header area)
            header_text = text[:first_speaker_match.start()]
            content_text = text[first_speaker_match.start():]
            
            # Clean header area only
            # Pattern 1: Full header with FINAL
            header_pattern1 = re.compile(
                rf'{months}\s+\d{{1,2}},\s+\d{{4}}\s+Chair\s+Powell\'?s?\s+Press\s+Conference\s+FINAL',
                re.IGNORECASE
            )
            header_text = header_pattern1.sub(' ', header_text)
            
            # Pattern 2: Full header without FINAL
            header_pattern2 = re.compile(
                rf'{months}\s+\d{{1,2}},\s+\d{{4}}\s+Chair\s+Powell\'?s?\s+Press\s+Conference',
                re.IGNORECASE
            )
            header_text = header_pattern2.sub(' ', header_text)
            
            # Pattern 3: "Transcript of Chair Powell's Press Conference"
            header_pattern3 = re.compile(
                r'Transcript\s+of\s+Chair\s+Powell\'?s?\s+Press\s+Conference',
                re.IGNORECASE
            )
            header_text = header_pattern3.sub(' ', header_text)
            
            # Pattern 4: Standalone date line (e.g., "January 29, 2025")
            header_pattern4 = re.compile(
                rf'^{months}\s+\d{{1,2}},\s+\d{{4}}$',
                re.IGNORECASE | re.MULTILINE
            )
            header_text = header_pattern4.sub(' ', header_text)
            
            # Combine cleaned header with content
            text = header_text + content_text
        
        # Remove "FINAL" that appears before speaker names (e.g., "FINAL HOWARD SCHNEIDER.")
        text = re.sub(r'\bFINAL\s+([A-Z][A-Z\s]{2,}\.)', r'\1', text)
        
        # Remove standalone "FINAL" words
        text = re.sub(r'\bFINAL\b', '', text)
        
        # Remove remaining fragments like "'s Press Conference" or "Press Conference" (but only if not part of actual content)
        text = re.sub(r'\'?s?\s+Press\s+Conference\b', '', text, flags=re.IGNORECASE)
        
        # Remove "Page X of Y" footers
        text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
        
        # Remove date fragments that appear in the middle of text (likely from page headers)
        # Pattern: "January 29, 2025 Chair Powell'" (date + "Chair Powell" + apostrophe)
        # But only if it's clearly a page header fragment, not part of actual speech
        # Look for patterns where date appears followed by "Chair Powell" but not as part of a sentence
        date_fragment_pattern = re.compile(
            rf'\s+{months}\s+\d{{1,2}},\s+\d{{4}}\s+Chair\s+Powell\'?\s+',
            re.IGNORECASE
        )
        text = date_fragment_pattern.sub(' ', text)
        
        # Also remove standalone date fragments that appear mid-sentence (page headers)
        # Pattern: "January 29, 2025" appearing in the middle of text (not at start)
        standalone_date_pattern = re.compile(
            rf'\s+{months}\s+\d{{1,2}},\s+\d{{4}}\s+',
            re.IGNORECASE
        )
        # Only remove if it's followed by "Chair Powell" or appears to be a page header
        text = re.sub(
            rf'\s+{months}\s+\d{{1,2}},\s+\d{{4}}\s+(?=Chair\s+Powell|\'|$|\s+[A-Z]{{2,}}\.)',
            ' ',
            text,
            flags=re.IGNORECASE
        )
        
        # Clean up orphaned apostrophes and fragments
        text = re.sub(r'\s+\'\s+', ' ', text)  # Remove standalone apostrophes with spaces
        text = re.sub(r'\'\s+', ' ', text)  # Remove apostrophes at word boundaries
        
        # Remove "Chair Powell'" fragments that appear mid-sentence (page header remnants)
        text = re.sub(r'\s+Chair\s+Powell\'?\s+', ' ', text, flags=re.IGNORECASE)
        
        # Clean up excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([A-Z][A-Z\s]{2,}\.)\s+', r' \1 ', text)  # Ensure speaker names have proper spacing
        
        return text.strip()
    
    def text_to_html_paragraphs(self, text):
        """Convert text to HTML paragraphs with proper speaker detection"""
        html_lines = []
        
        # Pattern to match speaker names: ALL CAPS names followed by period
        # Examples: "CHAIR POWELL.", "MICHELLE SMITH.", "JEANNA SMIALEK."
        # Match pattern: 2+ uppercase words followed by period and space
        speaker_pattern = re.compile(
            r'([A-Z][A-Z\s]{2,}\.)\s+',
            re.MULTILINE
        )
        
        # Find all speaker markers and their positions
        segments = []
        last_end = 0
        
        for match in speaker_pattern.finditer(text):
            # Add text before this speaker as content of previous speaker
            if match.start() > last_end:
                segments.append(('content', text[last_end:match.start()]))
            
            # Add the speaker name
            speaker_name = match.group(1)
            segments.append(('speaker', speaker_name))
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            segments.append(('content', text[last_end:]))
        
        # Process segments
        current_speaker = None
        current_content = []
        
        for seg_type, seg_content in segments:
            if seg_type == 'speaker':
                # Output previous speaker's content
                if current_speaker and current_content:
                    content = ' '.join(current_content).strip()
                    if content:
                        self._add_speaker_content(html_lines, current_speaker, content)
                
                current_speaker = seg_content
                current_content = []
            else:
                # This is content
                content = seg_content.strip()
                if content:
                    current_content.append(content)
        
        # Output last speaker's content
        if current_speaker and current_content:
            content = ' '.join(current_content).strip()
            if content:
                self._add_speaker_content(html_lines, current_speaker, content)
        
        return html_lines
    
    def _add_speaker_content(self, html_lines, speaker, content):
        """Add speaker content with appropriate formatting"""
        # Clean up content - remove extra whitespace but preserve sentence structure
        content = re.sub(r'\s+', ' ', content).strip()
        if not content or len(content) < 5:  # Skip very short content
            return
        
        # Determine if it's a question
        # Questions are typically from reporters (not Chair Powell) and contain "?"
        is_question = 'CHAIR POWELL' not in speaker.upper() and 'POWELL' not in speaker.upper() and '?' in content
        
        html_lines.append(f'<div class="speaker">{speaker}</div>')
        
        # Split long content into paragraphs for better readability
        # Look for natural paragraph breaks: sentence endings followed by capital letters starting new sentences
        # This helps break up long opening statements
        if len(content) > 500:  # Only split if content is long
            # Split on sentence boundaries (period + space + capital letter)
            # But preserve the original content structure
            paragraphs = self._split_into_paragraphs(content)
            for para in paragraphs:
                para = para.strip()
                if para:
                    if is_question:
                        html_lines.append(f'<p class="question">{para}</p>')
                    else:
                        html_lines.append(f'<p class="answer">{para}</p>')
        else:
            if is_question:
                html_lines.append(f'<p class="question">{content}</p>')
            else:
                html_lines.append(f'<p class="answer">{content}</p>')
    
    def _split_into_paragraphs(self, text):
        """Split long text into logical paragraphs based on natural breaks"""
        # Common paragraph transition phrases in FOMC speeches
        transition_patterns = [
            r'\.\s+(In support of our goals|Recent indicators suggest|In the labor market|Inflation has|Our monetary policy|At today\'s meeting|We know that|In considering|As the economy|If the economy|As we previously|The Fed has been assigned|We remain committed|Our success)',
        ]
        
        paragraphs = [text]
        
        # Try to split on transition patterns
        for pattern in transition_patterns:
            new_paragraphs = []
            for para in paragraphs:
                splits = re.split(pattern, para, flags=re.IGNORECASE)
                if len(splits) > 1:
                    # Reconstruct: first part, then each transition phrase + following text
                    current = splits[0].strip()
                    for i in range(1, len(splits), 2):
                        if i + 1 < len(splits):
                            transition = splits[i]
                            following = splits[i + 1]
                            
                            # Add current paragraph if it has content
                            if current:
                                # Ensure it ends with period
                                if not current.rstrip().endswith(('.', '!', '?')):
                                    current += '.'
                                new_paragraphs.append(current)
                            
                            # Start new paragraph with transition phrase
                            current = (transition + following).strip()
                        else:
                            current += ' ' + splits[i] if i < len(splits) else ''
                    
                    if current.strip():
                        if not current.rstrip().endswith(('.', '!', '?')):
                            current += '.'
                        new_paragraphs.append(current)
                else:
                    new_paragraphs.append(para)
            
            if len(new_paragraphs) > len(paragraphs):
                paragraphs = new_paragraphs
                break
        
        # If still one long paragraph, try splitting by sentence count
        if len(paragraphs) == 1 and len(text) > 800:
            # Split into chunks of approximately 400-600 characters
            sentences = re.split(r'\.\s+', text)
            current_chunk = []
            current_length = 0
            chunks = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_length = len(sentence)
                if current_length + sentence_length > 500 and current_chunk:
                    chunks.append('. '.join(current_chunk) + '.')
                    current_chunk = [sentence]
                    current_length = sentence_length
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length + 2  # +2 for ". "
            
            if current_chunk:
                chunks.append('. '.join(current_chunk) + ('.' if not current_chunk[-1].endswith('.') else ''))
            
            if len(chunks) > 1:
                paragraphs = chunks
        
        return [p.strip() for p in paragraphs if p.strip()]
    
    def process_transcript(self, date_str, title, pdf_url=None):
        """Process a single transcript: download PDF and convert to HTML"""
        print(f"Processing: {title} ({date_str})")
        
        # Find PDF URL if not provided
        if not pdf_url:
            pdf_url = self.find_pdf_url(date_str, title)
            if not pdf_url:
                print(f"Could not find PDF URL for {date_str}")
                return None
        
        # Download PDF
        pdf_filename = f"fomc_{date_str}.pdf"
        pdf_path = self.download_pdf(pdf_url, pdf_filename)
        
        if not pdf_path:
            print(f"Failed to download PDF for {date_str}")
            return None
        
        # Convert to HTML
        html_filename = f"fomc_{date_str}.html"
        html_path = self.pdf_to_html(pdf_path, html_filename)
        
        if not html_path:
            print(f"Failed to convert PDF to HTML for {date_str}")
            return None
        
        # Create transcript entry
        try:
            pdf_relative = str(pdf_path.relative_to(Path.cwd()))
        except ValueError:
            # If path is not relative to cwd, use absolute path or just filename
            pdf_relative = f"data/pdfs/{pdf_filename}"
        
        transcript = {
            "date": date_str,
            "title": title,
            "pdf_url": pdf_url,
            "pdf_path": pdf_relative,
            "html_path": f"data/htmls/{html_filename}",
            "scraped_at": datetime.now().isoformat()
        }
        
        return transcript
    
    def add_transcript(self, date_str, title, pdf_url=None, force_reprocess=False):
        """Add a new transcript"""
        # Check if already exists
        existing = next((t for t in self.transcripts if t['date'] == date_str), None)
        if existing and not force_reprocess:
            print(f"Transcript for {date_str} already exists")
            return existing
        
        # Remove existing entry if forcing reprocess
        if existing and force_reprocess:
            self.transcripts = [t for t in self.transcripts if t['date'] != date_str]
        
        transcript = self.process_transcript(date_str, title, pdf_url)
        if transcript:
            self.transcripts.append(transcript)
            self.transcripts.sort(key=lambda x: x['date'], reverse=True)
            self.save_data()
            print(f"Successfully added transcript for {date_str}")
        
        return transcript


def main():
    """Example usage"""
    scraper = FOMCScraper()
    
    # Add transcripts - PDF URLs will be auto-generated from dates
    # Format: https://www.federalreserve.gov/mediacenter/files/FOMCpresconfYYYYMMDD.pdf
    transcripts_to_add = [
        {
            "date": "2025-01-29",
            "title": "January 2025 FOMC Press Conference",
            "pdf_url": None  # Will auto-generate: FOMCpresconf20250129.pdf
        },
        {
            "date": "2024-12-18",
            "title": "December 2024 FOMC Press Conference",
            "pdf_url": None  # Will auto-generate: FOMCpresconf20241218.pdf
        },
        {
            "date": "2024-11-07",
            "title": "November 2024 FOMC Press Conference",
            "pdf_url": None
        },
        {
            "date": "2024-09-18",
            "title": "September 2024 FOMC Press Conference",
            "pdf_url": None
        },
        {
            "date": "2024-07-31",
            "title": "July 2024 FOMC Press Conference",
            "pdf_url": None
        },
        # Add more transcripts here
    ]
    
    print("=" * 60)
    print("FOMC Press Conference Transcript Scraper")
    print("=" * 60)
    print(f"Processing {len(transcripts_to_add)} transcripts...\n")
    
    for i, transcript_info in enumerate(transcripts_to_add, 1):
        print(f"[{i}/{len(transcripts_to_add)}] Processing: {transcript_info['title']}")
        result = scraper.add_transcript(
            transcript_info["date"],
            transcript_info["title"],
            transcript_info.get("pdf_url"),
            force_reprocess=True  # Force reprocess to apply new formatting
        )
        
        if result:
            print(f"  ✓ Success! HTML saved to: {result['html_path']}\n")
        else:
            print(f"  ✗ Failed - PDF may not be available yet\n")
    
    print("=" * 60)
    print(f"Total transcripts in database: {len(scraper.transcripts)}")
    print(f"Data saved to: {scraper.data_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
