#!/usr/bin/env python3
"""
Example usage of FOMC Scraper
This script shows how to add transcripts with known PDF URLs
"""

from scraper import FOMCScraper

def main():
    scraper = FOMCScraper()
    
    # Example: Add transcripts with known PDF URLs
    # You can find PDF URLs from:
    # https://www.federalreserve.gov/newsevents/pressreleases/monetary-policy-actions.htm
    
    transcripts_to_add = [
        {
            "date": "2024-12-18",
            "title": "December 2024 FOMC Press Conference",
            "pdf_url": None  # Will try to find automatically, or provide direct URL
        },
        {
            "date": "2024-11-07",
            "title": "November 2024 FOMC Press Conference",
            "pdf_url": None
        },
        # Add more transcripts here with their PDF URLs
        # Example with direct URL:
        # {
        #     "date": "2024-09-18",
        #     "title": "September 2024 FOMC Press Conference",
        #     "pdf_url": "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20240918.pdf"
        # },
    ]
    
    print("Starting to process transcripts...")
    for transcript_info in transcripts_to_add:
        result = scraper.add_transcript(
            transcript_info["date"],
            transcript_info["title"],
            transcript_info.get("pdf_url")
        )
        
        if result:
            print(f"✓ Successfully processed: {transcript_info['title']}")
        else:
            print(f"✗ Failed to process: {transcript_info['title']}")
            print("  Tip: Try providing the PDF URL directly")
    
    print(f"\nTotal transcripts: {len(scraper.transcripts)}")
    print(f"Data saved to: {scraper.data_file}")

if __name__ == "__main__":
    main()
