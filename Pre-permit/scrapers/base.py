"""
Base scraper class with shared HTTP, logging, retries, and error handling.
All scrapers inherit from this.
"""
import logging
import os
import sys
import time
import requests
from datetime import datetime

# Add parent dir to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_AGENT, REQUEST_DELAY, MAX_RETRIES, RETRY_BACKOFF, REQUEST_TIMEOUT, LOG_PATH


def setup_logging():
    """Set up logging to both file and console."""
    logger = logging.getLogger('pre_construction')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(LOG_PATH, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s'))
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('  %(message)s'))
    logger.addHandler(ch)

    return logger


class BaseScraper:
    """Base class for all scrapers."""

    source_name = 'unknown'

    def __init__(self):
        self.logger = setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.results = []

    def fetch(self, url, delay=None, **kwargs):
        """Fetch a URL with retries and exponential backoff.
        Returns response text or None on failure."""
        if delay is None:
            delay = REQUEST_DELAY

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if delay > 0 and attempt == 1:
                    time.sleep(delay)

                resp = self.session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
                resp.raise_for_status()
                return resp.text

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 'unknown'
                self.logger.warning(f"[{self.source_name}] HTTP {status} on {url} (attempt {attempt}/{MAX_RETRIES})")
                if status == 403 or status == 429:
                    # Forbidden or rate limited — wait longer
                    wait = RETRY_BACKOFF ** attempt * 2
                    self.logger.info(f"  Waiting {wait}s before retry...")
                    time.sleep(wait)
                elif attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF ** attempt)
                else:
                    return None

            except requests.exceptions.ConnectionError:
                self.logger.warning(f"[{self.source_name}] Connection error on {url} (attempt {attempt}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF ** attempt)
                else:
                    return None

            except requests.exceptions.Timeout:
                self.logger.warning(f"[{self.source_name}] Timeout on {url} (attempt {attempt}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF ** attempt)
                else:
                    return None

            except Exception as e:
                self.logger.error(f"[{self.source_name}] Unexpected error on {url}: {e}")
                return None

        return None

    def fetch_with_fallback(self, primary_url, fallback_url=None, **kwargs):
        """Try primary URL first, then fallback if it fails."""
        result = self.fetch(primary_url, **kwargs)
        if result:
            return result, primary_url

        if fallback_url:
            self.logger.info(f"[{self.source_name}] Primary failed, trying fallback: {fallback_url}")
            result = self.fetch(fallback_url, **kwargs)
            if result:
                return result, fallback_url

        return None, None

    def add_result(self, source_url, title, raw_text):
        """Add a scraped result to the results list."""
        if raw_text and len(raw_text.strip()) > 20:
            self.results.append({
                'source': self.source_name,
                'source_url': source_url or '',
                'title': (title or '').strip()[:500],
                'raw_text': raw_text.strip()[:5000],
            })

    def scrape(self):
        """Main scrape method. Override in subclasses.
        Returns list of dicts with keys: source, source_url, title, raw_text"""
        raise NotImplementedError

    def run(self):
        """Run the scraper safely, catching all errors."""
        self.results = []
        try:
            self.logger.info(f"[{self.source_name}] Starting scrape...")
            self.scrape()
            self.logger.info(f"[{self.source_name}] Done — {len(self.results)} items scraped.")
        except Exception as e:
            self.logger.error(f"[{self.source_name}] FAILED: {e}")
        return self.results
