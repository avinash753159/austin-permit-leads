"""
Configuration for the Pre-Construction Intelligence Engine.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'pre_construction_leads.db')
CSV_PATH = os.path.join(BASE_DIR, 'pre-construction-leads.csv')
REPORT_PATH = os.path.join(BASE_DIR, 'pre-construction-report.md')
LOG_PATH = os.path.join(BASE_DIR, 'scrape.log')
PDF_DIR = os.path.join(BASE_DIR, 'PDFs')

# Anthropic API key — optional, enables enhanced AI analysis
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# HTTP settings
USER_AGENT = 'Brimstone Partner Research Bot (avinash@brimstonepartner.com)'
REQUEST_DELAY = 2        # seconds between requests within a scraper
RSS_DELAY = 5            # seconds between Google News RSS queries
MAX_RETRIES = 3          # retry attempts per request
RETRY_BACKOFF = 2        # exponential backoff multiplier (2s, 4s, 8s)
REQUEST_TIMEOUT = 15     # seconds

# Scraper source URLs
SOURCES = {
    'council_agenda': {
        'primary': 'https://www.austintexas.gov/department/city-council/meetings',
        'fallback': 'https://www.austintexas.gov/planning-commission',
    },
    'zoning_case': {
        'primary': 'https://abc.austintexas.gov/web/permit/public-search-other',
        'fallback': 'https://www.austintexas.gov/zoning',
    },
    'news': {
        'rss_queries': [
            '"Austin TX" "planned development" OR "breaks ground" OR "mixed-use" construction',
            '"Austin TX" "square feet" OR "units" construction project developer',
            '"Austin" developer "files plans" OR "proposed project" OR "new development"',
        ],
        'culturemap': 'https://austin.culturemap.com/news/real-estate/',
    },
    'public_bid': {
        'primary': 'https://www.austintexas.gov/financeonline/vendor_connection/index.cfm',
        'txsmartbuy': 'https://www.txsmartbuy.com/sp',
    },
    'firm_announcement': {
        'rss_queries': [
            '"Austin" "selected as architect" OR "awarded design contract" OR "design-build"',
            '"Austin Texas" "engineering firm" OR "architecture firm" "new project" OR "awarded"',
        ],
    },
    'plat_record': {
        'primary': 'https://travis.tx.publicsearch.us/',
    },
}

# Keywords for filtering construction-related content
CONSTRUCTION_KEYWORDS = [
    'construction', 'development', 'building', 'permit', 'zoning',
    'residential', 'commercial', 'mixed-use', 'mixed use',
    'apartment', 'condo', 'townhome', 'single-family',
    'office', 'retail', 'warehouse', 'industrial', 'hotel',
    'renovation', 'remodel', 'demolition', 'infrastructure',
    'square feet', 'sq ft', 'sqft', 'acres',
    'million', 'breaks ground', 'groundbreaking',
    'architect', 'contractor', 'developer', 'builder',
    'site plan', 'plat', 'subdivision', 'variance',
    'RFP', 'RFQ', 'IFB', 'bid', 'solicitation',
]

# Stage assignments by source
STAGE_MAP = {
    'council_agenda': 'Zoning',
    'zoning_case': 'Zoning',
    'news': 'Rumor',
    'public_bid': 'Bidding',
    'firm_announcement': 'Design',
    'plat_record': 'Planning',
}

# Project type keywords
PROJECT_TYPE_KEYWORDS = {
    'Residential': ['apartment', 'condo', 'residential', 'home', 'housing', 'townhome',
                     'single-family', 'duplex', 'multifamily', 'dwelling', 'units'],
    'Commercial': ['office', 'retail', 'commercial', 'warehouse', 'industrial', 'hotel',
                    'restaurant', 'store', 'shopping', 'medical', 'clinic'],
    'Mixed-Use': ['mixed-use', 'mixed use', 'live-work', 'live/work'],
    'Infrastructure': ['road', 'bridge', 'water', 'sewer', 'utility', 'transit',
                        'park', 'trail', 'drainage', 'stormwater'],
    'Government': ['city of', 'county', 'state of texas', 'federal', 'school district',
                    'university', 'library', 'fire station', 'police'],
}
