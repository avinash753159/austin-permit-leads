"""
Source 5: Architecture & Engineering Firm Announcements
Searches Google News RSS for firms announcing Austin-area project awards.
Stage: Design
"""
import sys
import os
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import BaseScraper
from config import SOURCES, RSS_DELAY


class FirmAnnouncementsScraper(BaseScraper):
    source_name = 'firm_announcement'

    def _parse_google_rss(self, query):
        """Search Google News RSS for firm announcements."""
        encoded = quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

        xml_text = self.fetch(url, delay=RSS_DELAY)
        if not xml_text:
            return

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            self.logger.warning(f"[firm_announcement] RSS parse error: {e}")
            return

        for item in root.findall('.//item'):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            pub_el = item.find('pubDate')

            title = unescape(title_el.text) if title_el is not None and title_el.text else ''
            link = link_el.text if link_el is not None and link_el.text else ''
            desc = unescape(desc_el.text) if desc_el is not None and desc_el.text else ''
            pub_date = pub_el.text if pub_el is not None and pub_el.text else ''

            # Strip HTML
            desc = re.sub(r'<[^>]+>', ' ', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()

            # Must mention Austin
            combined = (title + ' ' + desc).lower()
            if 'austin' not in combined and 'central texas' not in combined:
                continue

            # Must be about architecture/engineering/design
            design_kw = ['architect', 'design', 'engineering', 'awarded', 'selected',
                         'contract', 'project', 'commission', 'master plan']
            if not any(kw in combined for kw in design_kw):
                continue

            raw_text = f"Title: {title}\nDate: {pub_date}\nDescription: {desc}"
            self.add_result(link, title, raw_text)

    def scrape(self):
        """Run all firm announcement searches."""
        queries = SOURCES['firm_announcement']['rss_queries']
        for query in queries:
            self._parse_google_rss(query)


if __name__ == '__main__':
    scraper = FirmAnnouncementsScraper()
    results = scraper.run()
    for r in results:
        print(f"  {r['title'][:80]}")
    print(f"\n  Total: {len(results)} firm announcements")
