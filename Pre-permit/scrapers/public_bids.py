"""
Source 4: Texas Public Bid Solicitations
Scrapes City of Austin vendor portal and TxSmartBuy for construction RFPs/RFQs.
Stage: Bidding
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import BaseScraper
from config import SOURCES, CONSTRUCTION_KEYWORDS


class PublicBidsScraper(BaseScraper):
    source_name = 'public_bid'

    def _scrape_austin_vendor_portal(self):
        """Scrape the City of Austin vendor connection portal for open bids."""
        from bs4 import BeautifulSoup

        url = SOURCES['public_bid']['primary']
        html = self.fetch(url)
        if not html:
            self.logger.warning("[public_bid] Austin vendor portal returned empty")
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Look for bid/solicitation tables or lists
        # The vendor connection page has various formats — try multiple selectors
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue

                text = ' '.join(c.get_text(strip=True) for c in cells)
                lower = text.lower()

                # Filter for construction-related bids
                has_keyword = any(kw in lower for kw in [
                    'construction', 'renovation', 'building', 'facility',
                    'infrastructure', 'roofing', 'hvac', 'plumbing', 'electrical',
                    'demolition', 'paving', 'concrete', 'site work',
                ])
                if not has_keyword:
                    continue

                # Try to find a link
                link = row.find('a', href=True)
                href = link['href'] if link else url
                if not href.startswith('http'):
                    href = 'https://www.austintexas.gov' + href

                title = cells[0].get_text(strip=True)[:200] if cells else ''
                self.add_result(href, title, f"Bid: {text}")

        # Also look for direct links to solicitations
        links = soup.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            lower = text.lower()
            if any(kw in lower for kw in ['solicitation', 'rfp', 'rfq', 'ifb', 'bid']):
                href = link['href']
                if not href.startswith('http'):
                    href = 'https://www.austintexas.gov' + href
                # Check if construction related
                if any(kw in lower for kw in CONSTRUCTION_KEYWORDS):
                    self.add_result(href, text, f"Solicitation: {text}")

    def _scrape_txsmartbuy(self):
        """Scrape TxSmartBuy for state construction procurement in Austin area."""
        from bs4 import BeautifulSoup

        url = SOURCES['public_bid']['txsmartbuy']
        html = self.fetch(url)
        if not html:
            self.logger.warning("[public_bid] TxSmartBuy returned empty")
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Look for solicitation listings
        items = soup.find_all(['tr', 'div', 'li'], class_=re.compile(r'solicitation|bid|listing|result|item'))
        if not items:
            items = soup.find_all('tr')

        for item in items:
            text = item.get_text(strip=True)
            lower = text.lower()

            # Must be construction related AND Austin area
            is_construction = any(kw in lower for kw in [
                'construction', 'renovation', 'building', 'facility', 'roofing',
                'hvac', 'plumbing', 'electrical', 'demolition', 'paving',
            ])
            is_austin = any(loc in lower for loc in ['austin', 'travis county', 'central texas'])

            if is_construction and is_austin:
                link = item.find('a', href=True)
                href = link['href'] if link else url
                if not href.startswith('http'):
                    href = 'https://www.txsmartbuy.com' + href
                title = text[:200]
                self.add_result(href, title, f"State Bid: {text[:1000]}")

    def scrape(self):
        """Run all bid scraping."""
        try:
            self._scrape_austin_vendor_portal()
        except Exception as e:
            self.logger.warning(f"[public_bid] Austin vendor portal failed: {e}")

        try:
            self._scrape_txsmartbuy()
        except Exception as e:
            self.logger.warning(f"[public_bid] TxSmartBuy failed: {e}")


if __name__ == '__main__':
    scraper = PublicBidsScraper()
    results = scraper.run()
    for r in results:
        print(f"  {r['title'][:80]}")
    print(f"\n  Total: {len(results)} bid items")
