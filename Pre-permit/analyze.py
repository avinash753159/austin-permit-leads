"""
Analysis engine for the Pre-Construction Intelligence Engine.
Default: regex/keyword extraction (free).
Optional: Claude API for higher accuracy (--use-api flag).
"""
import re
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ANTHROPIC_API_KEY, STAGE_MAP, PROJECT_TYPE_KEYWORDS
from db import get_conn, get_unanalyzed_scrapes, mark_analyzed, insert_lead
from scrapers.base import setup_logging

logger = setup_logging()


# ── Regex Patterns ──

ADDRESS_PATTERN = re.compile(
    r'\b(\d{1,5}\s+[A-Z][a-zA-Z]+(?:\s+[A-Za-z]+)*\s+'
    r'(?:St|Dr|Blvd|Ave|Rd|Ln|Way|Ct|Pkwy|Hwy|Street|Drive|Boulevard|Avenue|Road|Lane|Circle|Trail|Place|Loop|Expy|Expressway)\.?)'
    r'(?:\s*,?\s*(?:Suite|Ste|Unit|Apt|#)\s*\w+)?',
    re.IGNORECASE
)

DOLLAR_PATTERN = re.compile(
    r'\$\s*([\d,.]+)\s*(billion|million|mil|M|B|k|K)?',
    re.IGNORECASE
)

SQFT_PATTERN = re.compile(
    r'([\d,]+)\s*[-]?\s*(?:sq\.?\s*ft\.?|square\s*feet|SF|sqft|s\.f\.)',
    re.IGNORECASE
)

UNIT_PATTERN = re.compile(
    r'(\d[\d,]*)\s*[-]?\s*(?:unit|apartment|condo|home|lot|townhome|townhouse|dwelling)s?',
    re.IGNORECASE
)

PHONE_PATTERN = re.compile(
    r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
)

EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)

# Company name pattern — capitalized multi-word phrases near construction keywords
COMPANY_PATTERN = re.compile(
    r'(?:by|developer|builder|architect|contractor|owner|applicant|firm|company|partner)[:\s]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,4}(?:\s+(?:LLC|Inc|Corp|Group|Partners|Development|Construction|Homes|Builders|Properties|Realty|Architecture|Design|Engineers?))?)',
    re.IGNORECASE
)

# Alternate: Just find capitalized multi-word sequences
ENTITY_PATTERN = re.compile(
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s+(?:LLC|Inc|Corp|Group|Partners|Development|Construction|Homes|Builders|Properties)\b'
)


def extract_address(text):
    """Extract street addresses from text."""
    matches = ADDRESS_PATTERN.findall(text)
    if matches:
        # Return the longest match (most complete address)
        return max(matches, key=len).strip() if isinstance(matches[0], str) else matches[0]
    return ''


def extract_dollar_value(text):
    """Extract dollar values and return the largest one."""
    matches = DOLLAR_PATTERN.findall(text)
    if not matches:
        return ''

    best_val = 0
    best_raw = ''
    for num_str, multiplier in matches:
        try:
            num = float(num_str.replace(',', ''))
        except ValueError:
            continue

        mult_lower = multiplier.lower() if multiplier else ''
        if mult_lower in ('billion', 'b'):
            num *= 1_000_000_000
        elif mult_lower in ('million', 'mil', 'm'):
            num *= 1_000_000
        elif mult_lower in ('k',):
            num *= 1_000

        if num > best_val:
            best_val = num
            best_raw = f"${num_str}{multiplier}"

    return best_raw


def extract_sqft(text):
    """Extract square footage."""
    matches = SQFT_PATTERN.findall(text)
    if matches:
        # Return largest
        values = []
        for m in matches:
            try:
                values.append(int(m.replace(',', '')))
            except ValueError:
                pass
        if values:
            best = max(values)
            return f"{best:,} sq ft"
    return ''


def extract_units(text):
    """Extract unit counts (apartments, condos, etc.)."""
    matches = UNIT_PATTERN.findall(text)
    if matches:
        values = []
        for m in matches:
            try:
                values.append(int(m.replace(',', '')))
            except ValueError:
                pass
        if values:
            return str(max(values))
    return ''


def extract_company(text):
    """Extract developer/company names."""
    # Try the keyword-context pattern first
    matches = COMPANY_PATTERN.findall(text)
    if matches:
        return matches[0].strip()

    # Fall back to entity pattern
    matches = ENTITY_PATTERN.findall(text)
    if matches:
        return matches[0].strip()

    return ''


def extract_contact(text):
    """Extract phone numbers or emails."""
    phones = PHONE_PATTERN.findall(text)
    emails = EMAIL_PATTERN.findall(text)
    parts = []
    if phones:
        parts.append(phones[0])
    if emails:
        parts.append(emails[0])
    return ', '.join(parts)


def classify_project_type(text):
    """Classify project type based on keywords."""
    lower = text.lower()

    # Check Mixed-Use first (takes priority)
    for kw in PROJECT_TYPE_KEYWORDS['Mixed-Use']:
        if kw in lower:
            return 'Mixed-Use'

    scores = {}
    for ptype, keywords in PROJECT_TYPE_KEYWORDS.items():
        if ptype == 'Mixed-Use':
            continue
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[ptype] = score

    if not scores:
        return ''

    # If both Residential and Commercial have hits, it's Mixed-Use
    if 'Residential' in scores and 'Commercial' in scores:
        return 'Mixed-Use'

    return max(scores, key=scores.get)


def compute_confidence(lead):
    """Score confidence based on how many fields were extracted."""
    filled = 0
    for field in ['address', 'estimated_value_raw', 'estimated_sqft', 'developer_owner', 'contractor', 'architect']:
        if lead.get(field):
            filled += 1

    if filled >= 3:
        return 'HIGH'
    elif filled >= 2:
        return 'MEDIUM'
    return 'LOW'


def analyze_with_regex(scrape):
    """Analyze a raw scrape using regex extraction."""
    text = scrape['raw_text'] or ''
    title = scrape['title'] or ''
    combined = title + '\n' + text

    address = extract_address(combined)
    value = extract_dollar_value(combined)
    sqft = extract_sqft(combined)
    units = extract_units(combined)
    company = extract_company(combined)
    contact = extract_contact(combined)
    ptype = classify_project_type(combined)
    stage = STAGE_MAP.get(scrape['source'], 'Rumor')

    # Build project name from title or key info
    project_name = title[:150] if title else ''
    if not project_name and address:
        project_name = f"Project at {address}"

    # Build description
    desc_parts = []
    if sqft:
        desc_parts.append(f"{sqft}")
    if units:
        desc_parts.append(f"{units} units")
    if ptype:
        desc_parts.append(ptype.lower())
    if value:
        desc_parts.append(value)
    description = ', '.join(desc_parts) if desc_parts else text[:300]

    lead = {
        'raw_scrape_id': scrape['id'],
        'discovered_date': datetime.now().strftime('%Y-%m-%d'),
        'source': scrape['source'],
        'project_name': project_name,
        'address': address,
        'city': 'Austin',
        'developer_owner': company,
        'architect': '',
        'contractor': '',
        'description': description,
        'estimated_value_raw': value,
        'estimated_sqft': sqft,
        'project_type': ptype,
        'stage': stage,
        'source_url': scrape['source_url'],
        'contact_info': contact,
        'analysis_method': 'regex',
    }

    # Try to split developer vs architect vs contractor
    lower = combined.lower()
    if 'architect' in lower:
        arch_match = re.search(r'architect[:\s]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})', combined)
        if arch_match:
            lead['architect'] = arch_match.group(1).strip()

    lead['ai_confidence'] = compute_confidence(lead)
    return lead


def analyze_with_api(scrapes):
    """Analyze scrapes using Claude API. Requires ANTHROPIC_API_KEY."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed. Run: pip install anthropic")
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = []

    for scrape in scrapes:
        text = scrape['raw_text'] or ''
        title = scrape['title'] or ''

        prompt = f"""Extract structured construction project information from this text.
Return a JSON object with these fields (use empty string if not found):
- project_name: Name or title of the project
- address: Street address
- developer_owner: Developer or property owner
- architect: Architecture firm
- contractor: General contractor
- description: Brief project description
- estimated_value: Dollar value (e.g. "$50M")
- estimated_sqft: Square footage (e.g. "150,000 sq ft")
- project_type: One of: Commercial, Residential, Mixed-Use, Infrastructure, Government
- contact_info: Phone or email if found

Text:
Title: {title}
{text}

Return ONLY the JSON object, no other text."""

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            data = json.loads(response.content[0].text)

            lead = {
                'raw_scrape_id': scrape['id'],
                'discovered_date': datetime.now().strftime('%Y-%m-%d'),
                'source': scrape['source'],
                'project_name': data.get('project_name', title[:150]),
                'address': data.get('address', ''),
                'city': 'Austin',
                'developer_owner': data.get('developer_owner', ''),
                'architect': data.get('architect', ''),
                'contractor': data.get('contractor', ''),
                'description': data.get('description', ''),
                'estimated_value_raw': data.get('estimated_value', ''),
                'estimated_sqft': data.get('estimated_sqft', ''),
                'project_type': data.get('project_type', ''),
                'stage': STAGE_MAP.get(scrape['source'], 'Rumor'),
                'source_url': scrape['source_url'],
                'contact_info': data.get('contact_info', ''),
                'analysis_method': 'api',
            }
            lead['ai_confidence'] = compute_confidence(lead)
            results.append(lead)

        except Exception as e:
            logger.warning(f"API analysis failed for scrape {scrape['id']}: {e}")
            # Fall back to regex for this one
            results.append(analyze_with_regex(scrape))

    return results


def run_analysis(use_api=False):
    """Run analysis on all unanalyzed scrapes."""
    conn = get_conn()
    scrapes = get_unanalyzed_scrapes(conn)

    if not scrapes:
        logger.info("No unanalyzed scrapes found.")
        return 0

    logger.info(f"Analyzing {len(scrapes)} scrapes (method: {'api' if use_api else 'regex'})...")

    count = 0
    if use_api and ANTHROPIC_API_KEY:
        leads = analyze_with_api(scrapes)
        for lead in leads:
            lid = insert_lead(conn, lead)
            if lid:
                count += 1
            mark_analyzed(conn, lead['raw_scrape_id'])
    else:
        for scrape in scrapes:
            lead = analyze_with_regex(scrape)
            lid = insert_lead(conn, lead)
            if lid:
                count += 1
            mark_analyzed(conn, scrape['id'])

    conn.close()
    logger.info(f"Analysis complete — {count} new leads extracted from {len(scrapes)} scrapes.")
    return count


if __name__ == '__main__':
    use_api = '--use-api' in sys.argv
    run_analysis(use_api=use_api)
