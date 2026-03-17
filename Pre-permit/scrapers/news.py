"""
Source 3: Local News — Google News RSS + CultureMap Austin
Searches for Austin construction project announcements.
Stage: Rumor
"""
import sys
import os
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import BaseScraper
from config import SOURCES, RSS_DELAY, CONSTRUCTION_KEYWORDS


class NewsScraper(BaseScraper):
    source_name = 'news'

    def _parse_google_rss(self, query):
        """Search Google News RSS for a query and parse results."""
        encoded = quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

        xml_text = self.fetch(url, delay=RSS_DELAY)
        if not xml_text:
            return

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            self.logger.warning(f"[news] RSS parse error for query '{query[:50]}': {e}")
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

            # Strip HTML tags from description
            desc = re.sub(r'<[^>]+>', ' ', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()

            # Check if the result is actually about Austin construction
            combined = (title + ' ' + desc).lower()
            if 'austin' not in combined:
                continue

            has_keyword = any(kw in combined for kw in CONSTRUCTION_KEYWORDS)
            if not has_keyword:
                continue

            raw_text = f"Title: {title}\nDate: {pub_date}\nDescription: {desc}"
            self.add_result(link, title, raw_text)

    def _scrape_culturemap(self):
        """Scrape CultureMap Austin real estate section."""
        from bs4 import BeautifulSoup

        url = SOURCES['news']['culturemap']
        html = self.fetch(url)
        if not html:
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Find article links in the real estate section
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'post|article|story|card'))

        for article in articles[:15]:
            # Find the title/link
            link_tag = article.find('a', href=True)
            if not link_tag:
                continue

            href = link_tag.get('href', '')
            if not href.startswith('http'):
                href = 'https://austin.culturemap.com' + href

            title = link_tag.get_text(strip=True)
            if not title:
                h_tag = article.find(['h1', 'h2', 'h3', 'h4'])
                title = h_tag.get_text(strip=True) if h_tag else ''

            # Get snippet/description
            desc_tag = article.find(['p', 'div'], class_=re.compile(r'excerpt|summary|desc|teaser|snippet'))
            desc = desc_tag.get_text(strip=True) if desc_tag else ''

            if not title:
                continue

            combined = (title + ' ' + desc).lower()
            has_keyword = any(kw in combined for kw in CONSTRUCTION_KEYWORDS)
            if not has_keyword:
                continue

            raw_text = f"Title: {title}\nSource: CultureMap Austin\nDescription: {desc}"
            self.add_result(href, title, raw_text)

    def scrape(self):
        """Run all news scraping."""
        # Google News RSS queries
        queries = SOURCES['news']['rss_queries']
        for query in queries:
            self._parse_google_rss(query)

        # CultureMap
        try:
            self._scrape_culturemap()
        except Exception as e:
            self.logger.warning(f"[news] CultureMap scrape failed: {e}")


if __name__ == '__main__':
    scraper = NewsScraper()
    results = scraper.run()
    for r in results:
        print(f"  {r['title'][:80]}")
    print(f"\n  Total: {len(results)} news items")
