"""
Generates personalized 1-page A4 PDF reports for all 41 outreach leads.
Each PDF is tailored to the lead's trade category with relevant permit data.

Usage:
    python generate_pdfs.py
"""
import asyncio
import csv
import json
import os
import re
from urllib.request import urlopen
from urllib.parse import quote
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'PDFs')
LEADS_FILE = os.path.join(BASE_DIR, 'outreach-leads.csv')

os.makedirs(PDF_DIR, exist_ok=True)


def clean(n):
    if not n: return ''
    n = re.sub(r'\s*[\*]*\s*\(?MAIN\)?\s*[\*]*\s*', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s*,?\s*(LLC|Inc\.?|L\.?\s*P\.?|Ltd\.?|Corp\.?)\s*$', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\*+', '', n)
    if n == n.upper() and len(n) > 3: n = n.title()
    return n.strip().rstrip(',').strip()


def fmt_phone(p):
    if not p: return ''
    d = re.sub(r'\D', '', p)[-10:]
    if len(d) == 10: return f'({d[:3]}) {d[3:6]}-{d[6:]}'
    return ''


def fetch_permits():
    print("Fetching Austin permit data...")
    where = "issue_date >= '2026-03-03' AND permittype='BP'"
    url = f"https://data.austintexas.gov/resource/3syk-w9eu.json?$where={quote(where)}&$order={quote('issue_date DESC')}&$limit=50000"
    with urlopen(url) as resp:
        data = json.loads(resp.read())

    permits = []
    for p in data:
        sqft = max(int(p.get('total_new_add_sqft') or 0), int(p.get('remodel_repair_sqft') or 0))
        permits.append({
            'date': (p.get('issue_date') or '')[:10],
            'addr': p.get('original_address1', ''),
            'sqft': sqft,
            'contractor': clean(p.get('contractor_company_name', '')),
            'phone': fmt_phone(p.get('contractor_phone', '')),
            'desc': (p.get('description') or '')[:120].replace('\n', ' '),
            'cls': p.get('permit_class_mapped', ''),
            'work': p.get('work_class', ''),
        })
    print(f"  Got {len(permits)} permits.")
    return permits


def get_relevant(permits, category):
    cat = category.lower()
    out = []
    for p in permits:
        s = p['sqft']
        if 'electric' in cat:
            if (p['cls'] == 'Commercial' and s > 500) or s > 5000: out.append(p)
        elif 'plumb' in cat:
            if p['work'] in ('New', 'Addition and Remodel') and s > 1000: out.append(p)
        elif 'hvac' in cat or 'mechanic' in cat:
            if (p['cls'] == 'Commercial' and s > 500) or s > 5000: out.append(p)
        elif 'roof' in cat:
            if 'roof' in p['desc'].lower() or (p['work'] == 'New' and s > 1000): out.append(p)
        elif 'lumber' in cat or 'wood' in cat or 'timber' in cat:
            if p['work'] == 'New' and p['cls'] == 'Residential' and s > 2000: out.append(p)
        elif 'window' in cat or 'door' in cat:
            if p['work'] == 'New' and s > 2000: out.append(p)
        elif 'concrete' in cat:
            if p['work'] == 'New' and s > 1000: out.append(p)
        elif 'equipment' in cat or 'rental' in cat:
            if s > 5000: out.append(p)
        elif 'drywall' in cat or 'interior' in cat:
            if 'Remodel' in p['work'] and s > 5000: out.append(p)
        elif 'general' in cat or 'contractor' in cat:
            if s > 3000: out.append(p)
        else:
            if s > 5000: out.append(p)
    out.sort(key=lambda x: x['sqft'], reverse=True)
    return out[:8]


def get_top_contractors(relevant):
    counts = {}
    for p in relevant:
        c = p['contractor']
        if not c: continue
        if c not in counts:
            counts[c] = {'permits': 0, 'sqft': 0, 'phone': ''}
        counts[c]['permits'] += 1
        counts[c]['sqft'] += p['sqft']
        counts[c]['phone'] = counts[c]['phone'] or p['phone']
    return sorted(counts.items(), key=lambda x: x[1]['sqft'], reverse=True)[:4]


def trade_focus(category):
    cat = category.lower()
    if 'electric' in cat and 'sub' in cat: return 'Electrical Subcontractor', 'electrical projects to bid on'
    if 'electric' in cat: return 'Electrical Supply', 'projects needing electrical material quotes'
    if 'plumb' in cat and 'sub' in cat: return 'Plumbing Subcontractor', 'plumbing projects to bid on'
    if 'plumb' in cat: return 'Plumbing Supply', 'projects needing plumbing materials'
    if 'hvac' in cat or 'mechanic' in cat: return 'HVAC/Mechanical', 'projects needing mechanical bids'
    if 'roof' in cat: return 'Roofing Supply', 'projects needing roofing materials'
    if 'lumber' in cat or 'wood' in cat or 'timber' in cat: return 'Lumber Supply', 'new builds needing framing lumber'
    if 'concrete' in cat: return 'Concrete', 'projects needing foundation pours'
    if 'window' in cat or 'door' in cat: return 'Windows & Doors', 'builds needing window/door specification'
    if 'equipment' in cat or 'rental' in cat: return 'Equipment Rental', 'projects needing equipment on site'
    if 'drywall' in cat or 'interior' in cat: return 'Drywall & Interior', 'remodels needing drywall and steel studs'
    if 'general' in cat or 'contractor' in cat: return 'Competitive Intelligence', 'competitor permit activity'
    return 'Building Materials', 'construction opportunities'


def why_it_matters(p, category):
    cat = category.lower()
    w = p['work']
    if 'electric' in cat:
        if 'Shell' in w: return 'Full electrical fit-out from scratch.'
        if 'Remodel' in w: return 'Rewiring, panel upgrades likely.'
        if 'New' in w: return 'New build, full electrical needed.'
        return 'Electrical supply opportunity.'
    if 'plumb' in cat:
        if 'New' in w: return 'Full plumbing rough-in needed.'
        if 'Remodel' in w: return 'Plumbing retrofit opportunity.'
        return 'Plumbing work needed.'
    if 'hvac' in cat or 'mechanic' in cat:
        if 'hvac' in p['desc'].lower(): return 'HVAC system work specified.'
        if 'Remodel' in w: return 'Mechanical retrofit likely needed.'
        return 'Mechanical bid opportunity.'
    if 'roof' in cat:
        if 'roof' in p['desc'].lower(): return 'Roofing work specified in permit.'
        return 'New build, roofing materials needed.'
    if 'lumber' in cat or 'wood' in cat:
        return f"{p['sqft']:,} sqft of framing lumber needed."
    if 'concrete' in cat:
        return 'Foundation pour required.'
    if 'window' in cat or 'door' in cat:
        return f"{p['sqft']:,} sqft build, windows/doors to spec."
    if 'equipment' in cat or 'rental' in cat:
        return 'Heavy equipment needed on site.'
    if 'drywall' in cat or 'interior' in cat:
        return 'Interior finish-out, drywall needed.'
    if 'general' in cat or 'contractor' in cat:
        return f"Competitor activity, {p['sqft']:,} sqft."
    return 'Construction opportunity.'


def build_html(company, short_name, category, relevant, top_gcs, all_permits):
    focus_label, focus_desc = trade_focus(category)
    is_gc = 'general' in category.lower() or 'contractor' in category.lower()

    total = len(all_permits)
    commercial = len([p for p in all_permits if p['cls'] == 'Commercial'])
    residential = len([p for p in all_permits if p['cls'] == 'Residential' and p['work'] == 'New'])
    top_sqft = sum(g[1]['sqft'] for g in top_gcs) if top_gcs else 0

    # Stat cards
    if is_gc:
        stat4_num = len(top_gcs)
        stat4_label = 'Active Competitors'
    else:
        stat4_num = len(top_gcs)
        stat4_label = 'Target GCs'

    # Build opportunity rows (max 8)
    opp_rows = ''
    for p in relevant[:8]:
        wim = why_it_matters(p, category)
        phone_cell = f'<td class="cp">{p["phone"]}</td>' if p['phone'] else '<td style="color:#ccc;font-size:7px;">On dashboard</td>'
        opp_rows += f'''<tr>
            <td>{p["addr"]}</td>
            <td class="cs">{p["sqft"]:,}</td>
            <td>{p["work"]}</td>
            <td class="cn">{p["contractor"] or "On file"}</td>
            {phone_cell}
            <td class="cw">{wim}</td>
        </tr>'''

    # Build contractor rows (max 4)
    gc_rows = ''
    for name, info in top_gcs:
        if is_gc:
            action = f'{info["permits"]} permits, {info["sqft"]:,} sqft of activity.'
        else:
            action = f'Call {info["phone"]}. {info["permits"]} permits, {info["sqft"]:,} sqft.' if info['phone'] else f'{info["permits"]} permits, {info["sqft"]:,} sqft.'
        gc_rows += f'''<tr>
            <td class="cn">{name}</td>
            <td>{info["permits"]}</td>
            <td class="cs">{info["sqft"]:,}</td>
            <td class="cw">{action}</td>
        </tr>'''

    # Key insight
    if top_gcs:
        top_name = top_gcs[0][0]
        top_info = top_gcs[0][1]
        if is_gc:
            insight = f'<strong>{top_name}</strong> is the most active GC with {top_info["permits"]} permits totaling <strong>{top_info["sqft"]:,} sqft</strong>. This is your primary competitor to watch.'
        else:
            phone_bit = f' at {top_info["phone"]}' if top_info['phone'] else ''
            insight = f'<strong>{top_name}</strong>{phone_bit} filed {top_info["permits"]} permits totaling <strong>{top_info["sqft"]:,} sqft</strong>. This is your highest-value outreach target this week.'
    else:
        insight = f'{total} permits filed in Austin in the last two weeks. See the opportunity table below for the most relevant projects.'

    # Strategy
    if is_gc:
        if len(top_gcs) >= 2:
            strategy = f'{top_gcs[0][0]} leads with {top_gcs[0][1]["sqft"]:,} sqft. {top_gcs[1][0]} follows with {top_gcs[1][1]["sqft"]:,} sqft. Track these two to understand where the market is moving.'
        else:
            strategy = f'Monitor {top_gcs[0][0]} closely. They are setting the pace in your market.'
    else:
        if len(top_gcs) >= 3:
            calls = []
            total_sqft = 0
            for n, i in top_gcs[:3]:
                if i['phone']:
                    calls.append(f'<strong>{n}</strong> {i["phone"]} = {i["sqft"]:,} sqft')
                else:
                    calls.append(f'<strong>{n}</strong> = {i["sqft"]:,} sqft')
                total_sqft += i['sqft']
            strategy = f'{". ".join(calls)}. Total: <strong>{total_sqft:,} sqft from {len(calls)} contacts.</strong>'
        elif top_gcs:
            n, i = top_gcs[0]
            phone_bit = f' at {i["phone"]}' if i['phone'] else ''
            strategy = f'Start with <strong>{n}</strong>{phone_bit}. {i["permits"]} active permits, {i["sqft"]:,} sqft of work.'
        else:
            strategy = 'Check the dashboard for the latest permits and GC contact info.'

    # GC section header
    gc_header = 'Competitor Activity' if is_gc else 'Target Contractors'
    gc_last_col = 'Activity' if is_gc else 'Recommended Action'
    strategy_label = 'Market Position' if is_gc else 'Go-to-Market Move'

    today = datetime.now().strftime('%B %d, %Y')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{short_name} Report</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', system-ui, sans-serif; color: #1a1a2e; background: white; padding: 36px 40px; max-width: 820px; margin: 0 auto; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.header {{ display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 12px; border-bottom: 2px solid #2C3E6B; margin-bottom: 14px; }}
.brand {{ font-size: 9px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: #2C3E6B; }}
.gold-rule {{ width: 36px; height: 2px; background: #D4A843; margin: 6px 0; }}
.report-title {{ font-size: 15px; font-weight: 800; color: #2C3E6B; line-height: 1.2; }}
.report-for {{ font-size: 9px; font-weight: 600; color: #999; letter-spacing: 0.06em; text-transform: uppercase; }}
.report-company {{ font-size: 12px; font-weight: 700; color: #2C3E6B; margin-top: 2px; }}
.report-date {{ font-size: 8px; color: #aaa; margin-top: 3px; }}
.stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: #e5e7ed; border-radius: 6px; overflow: hidden; margin: 14px 0; }}
.stat {{ background: white; padding: 14px 10px; text-align: center; }}
.stat-num {{ font-size: 22px; font-weight: 800; color: #2C3E6B; line-height: 1; }}
.stat-label {{ font-size: 7.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #999; margin-top: 5px; }}
.callout {{ background: #faf8f3; border-left: 2.5px solid #D4A843; padding: 10px 14px; margin: 12px 0; }}
.callout-label {{ font-size: 7.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #D4A843; margin-bottom: 3px; }}
.callout p {{ font-size: 9.5px; color: #333; line-height: 1.5; }}
.callout strong {{ color: #2C3E6B; }}
.callout-strat {{ background: #f3f5fa; border-left-color: #2C3E6B; }}
.callout-strat .callout-label {{ color: #2C3E6B; }}
h2 {{ font-size: 8.5px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #2C3E6B; margin: 14px 0 4px; padding-bottom: 3px; border-bottom: 1.5px solid #D4A843; }}
table {{ width: 100%; border-collapse: collapse; font-size: 8.5px; margin: 5px 0; }}
thead th {{ background: #2C3E6B; color: white; padding: 6px 7px; text-align: left; font-size: 7px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
thead th:first-child {{ border-radius: 3px 0 0 0; }}
thead th:last-child {{ border-radius: 0 3px 0 0; }}
tbody td {{ padding: 5px 7px; border-bottom: 1px solid #f0f0f0; }}
tbody tr:nth-child(even) {{ background: #fafbfc; }}
.cn {{ font-weight: 700; color: #2C3E6B; }}
.cp {{ color: #D4A843; font-weight: 600; white-space: nowrap; }}
.cs {{ font-weight: 700; }}
.cw {{ font-size: 7.5px; color: #555; line-height: 1.3; }}
.footer {{ margin-top: 14px; padding-top: 8px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 7.5px; color: #aaa; }}
.footer a {{ color: #2C3E6B; text-decoration: none; }}
.cta-inline {{ display: inline-block; background: #2C3E6B; color: white; padding: 3px 10px; border-radius: 3px; font-size: 7px; font-weight: 700; margin-left: 6px; }}
.cta-inline span {{ color: #D4A843; }}
@page {{ size: A4; margin: 0; }}
@media print {{ body {{ padding: 28px 32px; }} }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="brand">Brimstone Partner | Texas Construction Intelligence</div>
    <div class="gold-rule"></div>
    <div class="report-title">{focus_label} Opportunity Report</div>
  </div>
  <div style="text-align:right;">
    <div class="report-for">Prepared for</div>
    <div class="report-company">{company}</div>
    <div class="report-date">{today} &bull; Last 14 Days &bull; Austin, TX</div>
  </div>
</div>
<div class="stats">
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Permits Filed</div></div>
  <div class="stat"><div class="stat-num">{residential}</div><div class="stat-label">Residential New</div></div>
  <div class="stat"><div class="stat-num">{commercial}</div><div class="stat-label">Commercial</div></div>
  <div class="stat"><div class="stat-num">{stat4_num}</div><div class="stat-label">{stat4_label}</div></div>
</div>
<div class="callout">
  <div class="callout-label">Key Insight</div>
  <p>{insight}</p>
</div>
<h2>Top Opportunities for {short_name}</h2>
<table>
  <thead><tr><th>Address</th><th>Sq Ft</th><th>Work</th><th>Contractor</th><th>Phone</th><th>Why It Matters</th></tr></thead>
  <tbody>{opp_rows}</tbody>
</table>
<h2>{gc_header}</h2>
<table>
  <thead><tr><th>Contractor</th><th>Permits</th><th>Total Sq Ft</th><th>{gc_last_col}</th></tr></thead>
  <tbody>{gc_rows}</tbody>
</table>
<div class="callout callout-strat">
  <div class="callout-label">{strategy_label}</div>
  <p>{strategy}</p>
</div>
<div class="footer">
  <div>Brimstone Partner &bull; Texas Construction Intelligence <a class="cta-inline" href="https://brimstone-permits-production.up.railway.app">Full Dashboard &rarr; <span>brimstone-permits-production.up.railway.app</span></a></div>
  <div>Avinash Nayak, PhD &bull; (832) 380-5845 &bull; <a href="mailto:avinash@brimstonepartner.com">avinash@brimstonepartner.com</a></div>
</div>
</body>
</html>'''


# Short name mapping
SHORT_NAMES = {
    'Hill Country Electric Supply': 'HCES', 'Summit Electric Supply': 'Summit',
    'Crawford Electric Supply': 'Crawford', 'Dealers Electrical Supply': 'Dealers',
    'Elliott Electric Supply': 'Elliott', 'Moore Supply South': 'Moore South',
    'Moore Supply North': 'Moore North', 'SRS Building Products': 'SRS',
    'Lone Star Materials': 'Lone Star', 'Austin Lumber': 'Austin Lumber',
    'Ringer Windows': 'Ringer', 'Accolade Windows & Doors': 'Accolade',
    'Austin Equipment': 'Austin Equipment', 'TimberTown Austin': 'TimberTown',
    'US Lumber Brokers': 'US Lumber', 'Eastside Lumber & Decking': 'Eastside',
    'JW Materials': 'JW Materials', '360 Metal Roofing Supply': '360 Metal',
    'Austin Snaploc Supply': 'Snaploc', 'Montopolis Supply': 'Montopolis',
    'Budget Roofing Supply': 'Budget Roofing', 'Sunbelt Rentals': 'Sunbelt',
    "Jon's Rental": "Jon's", 'HL Equipment': 'HL Equipment',
    'Builders FirstSource': 'BFS', 'BCS Concrete': 'BCS',
    'CP Electric': 'CP Electric', 'SALT Electric': 'SALT',
    'TCS Mechanical': 'TCS', 'G&S Mechanical': 'G&S',
    'Biggs Plumbing': 'Biggs', 'Westmoreland Plumbing': 'Westmoreland',
    'Texas Plumbing & Drain': 'Texas Plumbing', 'Novo Construction': 'Novo',
    'Real International Construction': 'Real International',
    'Structura Inc': 'Structura', 'Joseph Design Build': 'JDB',
    'Topos Collective': 'Topos', 'AWhiddon Construction': 'AWhiddon',
    'KB Home Austin': 'KB Home', 'Brookfield Residential TX': 'Brookfield',
}


async def main():
    permits = fetch_permits()

    leads = []
    with open(LEADS_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('Email'):
                leads.append(row)

    print(f"\nGenerating {len(leads)} personalized PDFs...\n")

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        for i, lead in enumerate(leads):
            company = lead['Company']
            category = lead['Category']
            short = SHORT_NAMES.get(company, company.split()[0])

            relevant = get_relevant(permits, category)
            top_gcs = get_top_contractors(relevant)

            html_content = build_html(company, short, category, relevant, top_gcs, permits)

            # Write temp HTML
            safe_name = company.replace(' ', '-').replace('/', '-').replace('&', 'and')
            html_path = os.path.join(PDF_DIR, f'{safe_name}-Report.html')
            pdf_path = os.path.join(PDF_DIR, f'{safe_name}-Report.pdf')

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Generate PDF
            page = await browser.new_page()
            await page.goto(f'file:///{html_path.replace(os.sep, "/")}', wait_until='networkidle')
            await page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                margin={'top': '0.4in', 'bottom': '0.4in', 'left': '0.4in', 'right': '0.4in'}
            )
            await page.close()

            # Clean up HTML
            os.remove(html_path)

            print(f"  [{i+1}/{len(leads)}] {company} -> {os.path.basename(pdf_path)}")

        await browser.close()

    print(f"\nDone! {len(leads)} PDFs saved to {PDF_DIR}")


if __name__ == '__main__':
    asyncio.run(main())
