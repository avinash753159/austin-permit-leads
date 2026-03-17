"""
Pull unique contractor leads from Austin permit data.
Outputs a CSV of contractors with contact info and permit stats.
"""
import json
import csv
import re
import sys
from urllib.request import urlopen
from urllib.parse import quote
from collections import defaultdict
from datetime import datetime, timedelta

def clean_name(name):
    if not name:
        return ""
    # Remove all variations of MAIN markers
    name = re.sub(r'\s*[\*]*\s*\(?MAIN\)?\s*[\*]*\s*', '', name, flags=re.IGNORECASE)
    # Remove (formally ...) / (formerly ...)
    name = re.sub(r'\s*[\{\(]\s*formal?ly.*?[\}\)]\s*', '', name, flags=re.IGNORECASE)
    # Remove (d/b/a ...) trade name blocks
    name = re.sub(r'\s*\(d/b/a.*?\)\s*', ' ', name, flags=re.IGNORECASE)
    # Remove (registered trade name) etc
    name = re.sub(r'\s*\(registered trade name\)\s*', '', name, flags=re.IGNORECASE)
    # Clean up stray asterisks, trailing commas, extra spaces
    name = re.sub(r'\*+', '', name)
    name = re.sub(r'\s{2,}', ' ', name)
    name = name.strip().rstrip(',').strip()
    return name

def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    print(f"Fetching Austin building permits from last {days} days...")

    where = f"issue_date >= '{since}' AND permittype='BP'"
    url = f"https://data.austintexas.gov/resource/3syk-w9eu.json?$where={quote(where)}&$order={quote('issue_date DESC')}&$limit=5000"

    with urlopen(url) as resp:
        data = json.loads(resp.read())

    print(f"Got {len(data)} permits.")

    # Aggregate by contractor
    contractors = defaultdict(lambda: {
        'phone': '', 'city': '', 'zip': '',
        'permit_count': 0, 'total_sqft': 0,
        'residential': 0, 'commercial': 0,
        'newest_permit': '', 'addresses': []
    })

    for p in data:
        name = clean_name(p.get('contractor_company_name', ''))
        if not name:
            continue

        c = contractors[name]
        c['permit_count'] += 1
        c['phone'] = c['phone'] or p.get('contractor_phone', '')
        c['city'] = c['city'] or p.get('contractor_city', '')
        c['zip'] = c['zip'] or p.get('contractor_zip', '').split('-')[0]

        sqft = max(int(p.get('total_new_add_sqft') or 0), int(p.get('remodel_repair_sqft') or 0))
        c['total_sqft'] += sqft

        if p.get('permit_class_mapped') == 'Residential':
            c['residential'] += 1
        else:
            c['commercial'] += 1

        if not c['newest_permit'] or p.get('issue_date', '') > c['newest_permit']:
            c['newest_permit'] = p.get('issue_date', '')

        addr = p.get('original_address1', '')
        if addr and len(c['addresses']) < 3:
            c['addresses'].append(addr)

    # Sort by permit count
    sorted_contractors = sorted(contractors.items(), key=lambda x: x[1]['permit_count'], reverse=True)

    # Write CSV
    outfile = f"austin-contractor-leads-{days}d.csv"
    with open(outfile, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([
            'Contractor', 'Phone', 'City', 'Zip',
            'Permits', 'Total Sq Ft', 'Residential', 'Commercial',
            'Most Recent Permit', 'Recent Project Addresses'
        ])
        for name, c in sorted_contractors:
            w.writerow([
                name,
                c['phone'],
                c['city'],
                c['zip'],
                c['permit_count'],
                c['total_sqft'],
                c['residential'],
                c['commercial'],
                c['newest_permit'][:10] if c['newest_permit'] else '',
                ' | '.join(c['addresses'])
            ])

    print(f"\nWrote {len(sorted_contractors)} contractor leads to {outfile}")
    print(f"\nTop 15 most active contractors:")
    print(f"{'Contractor':<45} {'Permits':>7} {'Sq Ft':>10} {'Phone':<16}")
    print("-" * 82)
    for name, c in sorted_contractors[:15]:
        sqft = f"{c['total_sqft']:,}" if c['total_sqft'] else '--'
        print(f"{name:<45} {c['permit_count']:>7} {sqft:>10} {c['phone'] or '--':<16}")

if __name__ == '__main__':
    main()
