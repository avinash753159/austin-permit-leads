"""
Source 6: Travis County & City of Austin Public Records
Searches for plat filings and large property transfers.
Stage: Planning
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import BaseScraper
from config import SOURCES


class PlatRecordsScraper(BaseScraper):
    source_name = 'plat_record'

    def _scrape_travis_county(self):
        """Try to scrape Travis County public search for plat records."""
        from bs4 import BeautifulSoup

        url = SOURCES['plat_record']['primary']
        html = self.fetch(url)
        if not html:
            self.logger.warning("[plat_record] Travis County public search returned empty — may need Playwright")
            return

        soup = BeautifulSoup(html, 'html.parser')

        # This site is likely JS-rendered — look for any accessible content
        text = soup.get_text(' ', strip=True)
        if len(text) < 100:
            self.logger.warning("[plat_record] Travis County page appears JS-rendered — limited data available")
            return

        # Search for plat-related content
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            lower = link_text.lower()
            if any(kw in lower for kw in ['plat', 'subdivision', 'deed', 'survey', 'land']):
                href = link['href']
                if not href.startswith('http'):
                    href = 'https://travis.tx.publicsearch.us' + href
                self.add_result(href, link_text, f"Plat Record: {link_text}")

    def _scrape_google_plat_news(self):
        """Fallback: Search Google News for Travis County plat/land transaction news."""
        import xml.etree.ElementTree as ET
        from html import unescape
        from urllib.parse import quote
        from config import RSS_DELAY

        queries = [
            '"Travis County" "plat" OR "subdivision" OR "land sale" construction',
            '"Austin TX" "acres" "developer" OR "purchased" OR "acquired" commercial',
        ]

        for query in queries:
            encoded = quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

            xml_text = self.fetch(url, delay=RSS_DELAY)
            if not xml_text:
                continue

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError:
                continue

            for item in root.findall('.//item'):
                title_el = item.find('title')
                link_el = item.find('link')
                desc_el = item.find('description')

                title = unescape(title_el.text) if title_el is not None and title_el.text else ''
                link = link_el.text if link_el is not None and link_el.text else ''
                desc = unescape(desc_el.text) if desc_el is not None and desc_el.text else ''
                desc = re.sub(r'<[^>]+>', ' ', desc).strip()

                combined = (title + ' ' + desc).lower()
                if 'austin' not in combined and 'travis' not in combined:
                    continue

                raw_text = f"Title: {title}\nDescription: {desc}"
                self.add_result(link, title, raw_text)

    def scrape(self):
        """Run plat record scraping."""
        try:
            self._scrape_travis_county()
        except Exception as e:
            self.logger.warning(f"[plat_record] Travis County failed: {e}")

        try:
            self._scrape_google_plat_news()
        except Exception as e:
            self.logger.warning(f"[plat_record] Google plat news failed: {e}")


if __name__ == '__main__':
    scraper = PlatRecordsScraper()
    results = scraper.run()
    for r in results:
        print(f"  {r['title'][:80]}")
    print(f"\n  Total: {len(results)} plat records")
