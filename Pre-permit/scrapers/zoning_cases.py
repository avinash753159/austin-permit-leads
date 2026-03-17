"""
Source 2: Austin Board of Adjustment & Zoning Cases
Scrapes active zoning cases and site plan applications.
Stage: Zoning
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import BaseScraper
from config import SOURCES


class ZoningCasesScraper(BaseScraper):
    source_name = 'zoning_case'

    ZONING_KEYWORDS = [
        'zoning', 'rezone', 'site plan', 'subdivision', 'variance',
        'conditional use', 'special permit', 'pud', 'planned development',
    ]

    def _scrape_zoning_page(self):
        """Scrape the Austin zoning information page."""
        from bs4 import BeautifulSoup

        url = SOURCES['zoning_case']['fallback']  # austintexas.gov/zoning is more accessible
        html, used_url = self.fetch_with_fallback(url, SOURCES['zoning_case']['primary'])
        if not html:
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Look for links to active cases, pending cases, case status
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            lower = text.lower()
            href = link['href']

            if any(kw in lower for kw in ['case', 'zoning', 'pending', 'active', 'application', 'review']):
                if not href.startswith('http'):
                    href = 'https://www.austintexas.gov' + href
                self.add_result(href, text, f"Zoning Page Link: {text}")

    def _scrape_amanda_system(self):
        """Try to scrape the AMANDA public search for active cases."""
        from bs4 import BeautifulSoup

        url = SOURCES['zoning_case']['primary']
        html = self.fetch(url)
        if not html:
            self.logger.warning("[zoning_case] AMANDA system returned empty — may need Playwright")
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Look for search forms, case listings, or results tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                text = ' '.join(c.get_text(strip=True) for c in cells)
                lower = text.lower()

                if any(kw in lower for kw in self.ZONING_KEYWORDS):
                    link = row.find('a', href=True)
                    href = link['href'] if link else url
                    if not href.startswith('http'):
                        href = 'https://abc.austintexas.gov' + href
                    self.add_result(href, text[:200], f"Zoning Case: {text[:2000]}")

        # Also check for any list items or divs with case info
        for item in soup.find_all(['li', 'div'], string=re.compile(r'(?i)zoning|site plan|case')):
            text = item.get_text(strip=True)
            if len(text) > 20:
                self.add_result(url, text[:200], f"Zoning Item: {text[:2000]}")

    def scrape(self):
        """Run all zoning case scraping."""
        try:
            self._scrape_zoning_page()
        except Exception as e:
            self.logger.warning(f"[zoning_case] Zoning page failed: {e}")

        try:
            self._scrape_amanda_system()
        except Exception as e:
            self.logger.warning(f"[zoning_case] AMANDA system failed: {e}")


if __name__ == '__main__':
    scraper = ZoningCasesScraper()
    results = scraper.run()
    for r in results:
        print(f"  {r['title'][:80]}")
    print(f"\n  Total: {len(results)} zoning items")
