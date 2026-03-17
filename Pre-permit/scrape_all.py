"""
Pre-Construction Intelligence Engine — Main Coordinator
Runs all scrapers, analyzes results, generates reports.

Usage:
    python scrape_all.py              # Run all scrapers with regex analysis
    python scrape_all.py --use-api    # Run all scrapers with Claude API analysis
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrapers.base import setup_logging
from db import get_conn, insert_raw_scrape, create_tables
from analyze import run_analysis
from report import generate_all

logger = setup_logging()


def run_all_scrapers():
    """Run all 6 scrapers and store raw results in the database."""
    conn = get_conn()
    create_tables(conn)

    # Import all scrapers
    from scrapers.news import NewsScraper
    from scrapers.public_bids import PublicBidsScraper
    from scrapers.firm_announcements import FirmAnnouncementsScraper
    from scrapers.council_agendas import CouncilAgendaScraper
    from scrapers.zoning_cases import ZoningCasesScraper
    from scrapers.plat_records import PlatRecordsScraper

    scrapers = [
        NewsScraper(),
        PublicBidsScraper(),
        FirmAnnouncementsScraper(),
        CouncilAgendaScraper(),
        ZoningCasesScraper(),
        PlatRecordsScraper(),
    ]

    total_scraped = 0
    succeeded = 0
    failed = 0
    scraper_results = {}

    for scraper in scrapers:
        name = scraper.source_name
        try:
            results = scraper.run()
            count = 0
            for item in results:
                rid = insert_raw_scrape(
                    conn,
                    item['source'],
                    item['source_url'],
                    item['title'],
                    item['raw_text'],
                )
                if rid:
                    count += 1

            total_scraped += count
            succeeded += 1
            scraper_results[name] = count
            logger.info(f"  [{name}] {count} new items stored")

        except Exception as e:
            failed += 1
            scraper_results[name] = 0
            logger.error(f"  [{name}] FAILED: {e}")

    conn.close()

    logger.info(f"\nScraping complete: {succeeded}/{len(scrapers)} sources succeeded, {total_scraped} total items")
    if failed > 0:
        logger.warning(f"  {failed} source(s) failed — check scrape.log for details")

    return scraper_results, total_scraped


def main():
    use_api = '--use-api' in sys.argv

    print()
    print("  ============================================")
    print("  Brimstone Pre-Construction Intelligence Engine")
    print("  ============================================")
    print()

    start = time.time()

    # Step 1: Run all scrapers
    print("  Step 1/3: Scraping public data sources...")
    print()
    scraper_results, total_scraped = run_all_scrapers()
    print()

    # Step 2: Analyze raw scrapes
    method = "Claude API" if use_api else "regex/keyword"
    print(f"  Step 2/3: Analyzing scraped data ({method})...")
    new_leads = run_analysis(use_api=use_api)
    print()

    # Step 3: Generate reports
    print("  Step 3/3: Generating reports...")
    lead_count = generate_all()
    print()

    elapsed = time.time() - start

    # Summary
    print("  ============================================")
    print("  RESULTS")
    print("  ============================================")
    print()
    for name, count in scraper_results.items():
        status = f"{count} items" if count > 0 else "0 items (check log)"
        print(f"    {name:25s} {status}")
    print()
    print(f"    Total scraped:    {total_scraped}")
    print(f"    New leads:        {new_leads}")
    print(f"    Total in DB:      {lead_count}")
    print(f"    Analysis method:  {method}")
    print(f"    Time:             {elapsed:.1f}s")
    print()
    print(f"  Outputs:")
    print(f"    CSV:    Pre-permit/pre-construction-leads.csv")
    print(f"    Report: Pre-permit/pre-construction-report.md")
    print(f"    DB:     Pre-permit/pre_construction_leads.db")
    print()


if __name__ == '__main__':
    main()
