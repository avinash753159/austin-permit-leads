# Pre-Construction Intelligence Engine — Design Spec

**Date:** 2026-03-17
**Author:** Avinash Nayak / Claude
**Status:** Draft
**Location:** `austin-permits/Pre-permit/`

---

## 1. Purpose

Build a system that discovers Austin construction projects 3-12 months BEFORE permits are filed, replicating what Dodge Construction Network does with 500+ human reporters — but with automated scraping + AI analysis. This gives Brimstone Partner a competitive edge by surfacing leads that don't yet exist in the Austin Socrata permit API.

## 2. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Modular pipeline (Approach B) | Independent scrapers, shared DB, can test/run individually |
| Default analysis | Local regex/keyword extraction | Free to run, no API costs |
| Optional analysis | Claude API via `--use-api` flag | Higher accuracy when needed, pay-per-use |
| Output | SQLite DB + CSV + Markdown report | Immediate use for outreach, future dashboard integration |
| Scheduling | Manual now, cron-ready later | Avoid unnecessary API costs, add automation when proven |
| Dashboard | Future integration via Node.js API endpoint | Not built in v1, DB schema supports it |

## 3. Project Structure

```
Pre-permit/
├── scrape_all.py              # Coordinator — runs scrapers → analyze → report
├── analyze.py                 # Regex extraction (default) or Claude API (--use-api)
├── report.py                  # Generates CSV + markdown report from leads table
├── db.py                      # SQLite helpers: create tables, insert, query, dedupe
├── config.py                  # URLs, constants, API key detection
├── requirements.txt           # Python dependencies
├── scrapers/
│   ├── __init__.py
│   ├── base.py                # Base scraper class with shared HTTP, logging, error handling
│   ├── council_agendas.py     # Source 1: City Council & Planning Commission agendas
│   ├── zoning_cases.py        # Source 2: Board of Adjustment & Zoning cases
│   ├── news.py                # Source 3: Google News RSS + CultureMap
│   ├── public_bids.py         # Source 4: Austin vendor portal + TxSmartBuy
│   ├── firm_announcements.py  # Source 5: Google News RSS for arch/eng firms
│   └── plat_records.py        # Source 6: Travis County public records
├── pre_construction_leads.db  # SQLite database (generated)
├── pre-construction-leads.csv # CSV export (generated)
├── pre-construction-report.md # Markdown report (generated)
└── scrape.log                 # Log file (generated)
```

## 4. Database Schema

### Table: `raw_scrapes`
Stores unprocessed scraped text before analysis.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment |
| source | TEXT | 'council_agenda', 'zoning_case', 'news', 'public_bid', 'firm_announcement', 'plat_record' |
| source_url | TEXT | URL where the data was found |
| title | TEXT | Headline or title of the item |
| raw_text | TEXT | Full scraped text content |
| scraped_at | TEXT | Timestamp of scrape (DEFAULT CURRENT_TIMESTAMP) |
| analyzed | INTEGER | 0=pending, 1=processed (DEFAULT 0) |

### Table: `leads`
Structured leads after analysis (regex or API).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment |
| raw_scrape_id | INTEGER | FK to raw_scrapes.id |
| discovered_date | TEXT | Date the lead was first found |
| source | TEXT | Same source types as raw_scrapes |
| project_name | TEXT | Name of the project if identifiable |
| address | TEXT | Street address or location |
| city | TEXT | DEFAULT 'Austin' |
| developer_owner | TEXT | Developer or property owner |
| architect | TEXT | Architecture firm if mentioned |
| contractor | TEXT | GC or contractor if mentioned |
| description | TEXT | Project description |
| estimated_value | TEXT | Dollar value (normalized) |
| estimated_sqft | TEXT | Square footage |
| project_type | TEXT | 'Commercial', 'Residential', 'Mixed-Use', 'Infrastructure', 'Government' |
| stage | TEXT | 'Rumor', 'Planning', 'Zoning', 'Design', 'Bidding', 'Pre-Permit' |
| source_url | TEXT | Link to original source |
| contact_info | TEXT | Phone, email, or other contact if found |
| ai_confidence | TEXT | 'HIGH', 'MEDIUM', 'LOW' |
| analysis_method | TEXT | 'regex' or 'api' |
| is_duplicate | INTEGER | 1 if merged with another lead (DEFAULT 0) |
| duplicate_of | INTEGER | FK to the lead this is a duplicate of |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

## 5. Scraper Details

### 5.1 Base Scraper (`scrapers/base.py`)
All scrapers inherit from a `BaseScraper` class that provides:
- HTTP requests with proper User-Agent header: `"Brimstone Partner Research Bot (avinash@brimstonepartner.com)"`
- 2-second delay between requests (configurable)
- Retry logic: 3 attempts with exponential backoff (2s, 4s, 8s)
- Logging to `scrape.log`
- Error handling that returns empty list on failure (never crashes the pipeline)
- A `scrape()` method that returns `List[dict]` with keys: `source`, `source_url`, `title`, `raw_text`

### 5.2 Source 1: Council Agendas (`council_agendas.py`)
- **Primary URL:** `https://www.austintexas.gov/department/city-council/meetings`
- **Fallback URL:** `https://www.austintexas.gov/planning-commission`
- **Method:** Fetch meeting pages, extract agenda PDFs/text links, scan for zoning/planning keywords
- **Keywords:** "zoning change", "site plan", "PUD", "conditional use", "variance", "rezoning", "planned unit development"
- **Fallback:** If main page structure changes, try scraping the city's Legistar/agenda management system
- **Stage assignment:** "Zoning" or "Planning"

### 5.3 Source 2: Zoning Cases (`zoning_cases.py`)
- **Primary URL:** `https://abc.austintexas.gov/web/permit/public-search-other` (AMANDA system)
- **Fallback URL:** `https://www.austintexas.gov/zoning`
- **Method:** Search for active zoning cases, site plan applications in review
- **Note:** AMANDA system may be JS-rendered — use Playwright if requests fail
- **Stage assignment:** "Zoning"

### 5.4 Source 3: Local News (`news.py`)
- **Primary:** Google News RSS feed searches for Austin construction keywords
- **Search queries:**
  - `"Austin TX" "planned development" OR "breaks ground" OR "mixed-use"`
  - `"Austin TX" "square feet" OR "units" construction project`
  - `"Austin" developer "files plans" OR "proposed project"`
- **Fallback 1:** CultureMap Austin real estate RSS: `https://austin.culturemap.com/feeds/rss/`
- **Fallback 2:** Direct scrape of CultureMap real estate section
- **Note:** Paywalled sites (ABJ, Statesman) — only headlines/snippets from RSS, no full articles
- **Stage assignment:** "Rumor"

### 5.5 Source 4: Public Bids (`public_bids.py`)
- **Primary URL:** `https://www.austintexas.gov/financeonline/vendor_connection/index.cfm`
- **Fallback 1:** `https://www.txsmartbuy.com/sp` (state procurement)
- **Fallback 2:** `https://www.civcastusa.com` (multi-city bid portal)
- **Method:** Search for construction-related solicitations (RFP, RFQ, IFB)
- **Keywords:** "construction", "renovation", "building", "facility", "infrastructure"
- **Stage assignment:** "Bidding"

### 5.6 Source 5: Firm Announcements (`firm_announcements.py`)
- **Primary:** Google News RSS search
- **Search queries:**
  - `"Austin" "selected as architect" OR "awarded design contract"`
  - `"Austin" "engineering firm" "new project" OR "awarded contract"`
- **Method:** Parse RSS results, extract firm names, project descriptions
- **Stage assignment:** "Design"

### 5.7 Source 6: Plat Records (`plat_records.py`)
- **Primary URL:** `https://travis.tx.publicsearch.us/`
- **Method:** Search for recent plat filings, commercial property transfers
- **Note:** This is the hardest source to automate. May require Playwright. If it fails, scraper returns empty gracefully.
- **Fallback:** Skip entirely in v1 if too complex — log a warning and move on
- **Stage assignment:** "Planning"

## 6. Analysis Engine (`analyze.py`)

### 6.1 Regex Mode (Default)

**Address extraction:**
```
\d{1,5}\s+[A-Z][a-zA-z]+(\s+[A-Za-z]+)*\s+(St|Dr|Blvd|Ave|Rd|Ln|Way|Ct|Pkwy|Hwy|Street|Drive|Boulevard|Avenue|Road|Lane|Circle|Trail|Place)\.?
```
Plus known Austin landmarks: "IH-35", "Mopac", "Loop 360", "Congress Ave", "Lamar Blvd".

**Dollar values:**
```
\$\s*[\d,.]+\s*(million|M|billion|B|k|K)?
```
Normalizes to consistent format. "$50M" → "$50,000,000", "$2.5 million" → "$2,500,000".

**Square footage:**
```
[\d,]+\s*[-]?\s*(sq\.?\s*ft\.?|square\s*feet|SF|sqft|s\.f\.)
```

**Unit counts:**
```
(\d[\d,]*)\s*[-]?\s*(unit|apartment|condo|home|lot|townhome|townhouse|dwelling)s?
```

**Company/person extraction:**
- Look for capitalized multi-word phrases near keywords: "developer", "builder", "architect", "contractor", "owner", "applicant"
- Pattern: `((?:[A-Z][a-zA-Z]+\s+){1,4}(?:LLC|Inc|Corp|Group|Partners|Development|Construction|Homes|Builders|Properties|Realty|Architecture|Design)?)`

**Project type classification:**
Keyword scoring system:
- Residential keywords: "apartment", "condo", "residential", "home", "housing", "townhome", "single-family", "duplex"
- Commercial keywords: "office", "retail", "commercial", "warehouse", "industrial", "hotel", "restaurant", "store"
- Mixed-Use keywords: "mixed-use", "mixed use", "live-work"
- Infrastructure keywords: "road", "bridge", "water", "sewer", "utility", "transit", "park"
- Government keywords: "city of", "county", "state", "federal", "school district", "university"
- If both residential and commercial keywords present → "Mixed-Use"

**Confidence scoring:**
- HIGH: 3+ fields extracted (address + value/sqft + developer/contractor)
- MEDIUM: 2 fields extracted
- LOW: 1 field only or just keyword match

### 6.2 Claude API Mode (`--use-api`)

When `ANTHROPIC_API_KEY` is set and `--use-api` flag is passed:

- Sends each raw_scrape text to Claude Haiku (cheapest, fast enough for extraction)
- System prompt instructs Claude to return JSON with all lead fields
- Batch processes: groups up to 5 raw scrapes per API call to reduce costs
- Sets `analysis_method = 'api'` on resulting leads
- Estimated cost: ~$0.01-0.03 per lead analyzed

## 7. Deduplication (`db.py`)

After analysis, deduplication runs on the leads table:

1. **Exact match:** Same address + same source → skip insert
2. **Fuzzy match:** Normalize address (lowercase, strip "St/Street/Dr/Drive" variants, strip unit numbers) and compare. If two leads from different sources have matching normalized addresses → mark newer one as `is_duplicate=1, duplicate_of=<older_lead_id>`
3. **Project name match:** Lowercase + strip punctuation. "801 Barton Springs Mixed-Use" matches "801 Barton Springs Blvd Development"

## 8. Report Output (`report.py`)

### CSV: `pre-construction-leads.csv`
Columns: discovered_date, source, project_name, address, developer_owner, architect, contractor, description, estimated_value, estimated_sqft, project_type, stage, source_url, contact_info, ai_confidence, analysis_method

Sorted by discovered_date DESC. Excludes rows where `is_duplicate=1`.

### Markdown: `pre-construction-report.md`
Sections:
1. Summary — total leads, new in last 7 days, analysis method breakdown
2. By Source — count per scraper
3. By Stage — count per stage (Rumor/Planning/Zoning/Design/Bidding)
4. Top Leads by Estimated Value — top 10 with all fields
5. New This Week — table of leads discovered in last 7 days
6. Scraper Health — which sources succeeded/failed on last run

## 9. Error Handling & Fallbacks

| Scenario | Handling |
|----------|----------|
| Source website is down | Scraper returns empty list, logs warning, pipeline continues |
| Source HTML structure changed | Try fallback URL if available, else return empty |
| JS-rendered page (requests fails) | Fallback to Playwright headless browser |
| Rate limited by Google | 5-second delays between RSS requests, max 10 queries per source |
| No results from any source | Report generates with "0 leads found" message, no crash |
| SQLite DB doesn't exist | `db.py` auto-creates on first run |
| Malformed scraped text | Regex returns empty fields, lead saved with LOW confidence |
| Claude API error (when using --use-api) | Falls back to regex for that batch, logs error |
| Network timeout | 3 retries with exponential backoff per request |
| Duplicate leads across sources | Dedupe engine marks them, excluded from CSV/report |

## 10. Dependencies

```
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.1
playwright>=1.40
anthropic>=0.40
feedparser>=6.0
```

`feedparser` is new — needed for Google News RSS parsing. Everything else is already installed or standard library.

## 11. Usage

```bash
# Default run — all scrapers, regex analysis
cd Pre-permit
python scrape_all.py

# Run a single scraper only
python -m scrapers.news
python -m scrapers.public_bids

# With Claude API for higher accuracy
python scrape_all.py --use-api

# Or set env var
set ANTHROPIC_API_KEY=sk-ant-...
python scrape_all.py --use-api
```

## 12. Future Integration

When ready to add to the dashboard:
1. Add a new endpoint to `server.js`: `GET /api/pre-construction` that reads from `pre_construction_leads.db`
2. Add a "Pre-Construction" tab to `index-dashboard.html` that fetches and displays these leads
3. Add cron job (Windows Task Scheduler or Railway cron) to run `scrape_all.py` daily

## 13. Verification Checklist

Each module must pass these checks before moving to the next:

### Per-Module Verification Loop:
1. **Write the module**
2. **Check 1 — Does it run without errors?** `python -c "from module import ..."`
3. **Check 2 — Does it produce expected output?** Run the module, verify DB entries or return values
4. **Check 3 — Does it handle failure gracefully?** Test with bad URL / no network
5. **Check 4 — Does it integrate with the pipeline?** Run `scrape_all.py` and verify the module's output appears in the final report

### Build Order:
1. `config.py` → verify constants load
2. `db.py` → verify tables created, insert/query works
3. `scrapers/base.py` → verify HTTP requests, retries, logging
4. `scrapers/news.py` → verify RSS parsing, raw_scrapes populated (easiest source, test pipeline end-to-end)
5. `analyze.py` (regex mode) → verify leads extracted from raw_scrapes
6. `report.py` → verify CSV + markdown generated
7. `scrape_all.py` → verify full pipeline coordinator works
8. `scrapers/public_bids.py` → verify bid scraping
9. `scrapers/firm_announcements.py` → verify firm news scraping
10. `scrapers/council_agendas.py` → verify agenda scraping
11. `scrapers/zoning_cases.py` → verify zoning case scraping
12. `scrapers/plat_records.py` → verify plat record scraping (may skip for v1)
13. `analyze.py` (API mode) → verify Claude API extraction works when key is set
14. **Full integration test** — run `scrape_all.py`, verify all outputs
