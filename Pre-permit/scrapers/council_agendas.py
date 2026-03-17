"""
Source 1: Austin City Council & Planning Commission Agendas
Scrapes meeting agendas for zoning changes, site plans, variances.
Stage: Zoning / Planning
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import BaseScraper
from config import SOURCES


class CouncilAgendaScraper(BaseScraper):
    source_name = 'council_agenda'

    ZONING_KEYWORDS = [
        'zoning change', 'rezoning', 'rezone', 'site plan', 'pud',
        'planned unit development', 'conditional use', 'variance',
        'special exception', 'subdivision', 'annexation',
        'land use', 'comprehensive plan amendment', 'future land use',
        'density bonus', 'planned development agreement',
    ]

    def _scrape_meetings_page(self):
        """Scrape the City Council meetings page for agenda items."""
        from bs4 import BeautifulSoup

        url = SOURCES['council_agenda']['primary']
        html, used_url = self.fetch_with_fallback(url, SOURCES['council_agenda']['fallback'])
        if not html:
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Look for links to meeting agendas/minutes
        agenda_links = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            href = link['href']
            if any(kw in text for kw in ['agenda', 'meeting', 'minutes', 'council']):
                if not href.startswith('http'):
                    href = 'https://www.austintexas.gov' + href
                agenda_links.append((href, link.get_text(strip=True)))

        # Fetch each agenda page and look for zoning items
        for href, link_text in agenda_links[:10]:  # Limit to 10 most recent
            self._parse_agenda_page(href, link_text)

    def _parse_agenda_page(self, url, page_title):
        """Parse an individual agenda page for zoning/planning items."""
        from bs4 import BeautifulSoup

        html = self.fetch(url)
        if not html:
            return

        soup = BeautifulSoup(html, 'html.parser')
        full_text = soup.get_text(' ', strip=True)

        # Split by common agenda item patterns (numbered items, bullet points)
        # Look for zoning-related sections
        items = re.split(r'(?:\n\s*\d+[\.\)]\s+|\n\s*Item\s+\d+)', full_text)

        for item_text in items:
            lower = item_text.lower()
            if any(kw in lower for kw in self.ZONING_KEYWORDS):
                # Found a zoning-related agenda item
                title = item_text.strip()[:200]
                self.add_result(url, f"{page_title}: {title}", f"Council Agenda Item:\n{item_text.strip()[:2000]}")

    def _scrape_planning_commission(self):
        """Scrape the Planning Commission page."""
        from bs4 import BeautifulSoup

        url = SOURCES['council_agenda']['fallback']
        html = self.fetch(url)
        if not html:
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Look for planning cases and agenda items
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            lower = text.lower()
            if any(kw in lower for kw in self.ZONING_KEYWORDS + ['case', 'application', 'hearing']):
                href = link['href']
                if not href.startswith('http'):
                    href = 'https://www.austintexas.gov' + href
                self.add_result(href, text, f"Planning Commission: {text}")

    def scrape(self):
        """Run all council/planning scraping."""
        try:
            self._scrape_meetings_page()
        except Exception as e:
            self.logger.warning(f"[council_agenda] Meetings page failed: {e}")

        try:
            self._scrape_planning_commission()
        except Exception as e:
            self.logger.warning(f"[council_agenda] Planning commission failed: {e}")


if __name__ == '__main__':
    scraper = CouncilAgendaScraper()
    results = scraper.run()
    for r in results:
        print(f"  {r['title'][:80]}")
    print(f"\n  Total: {len(results)} agenda items")
