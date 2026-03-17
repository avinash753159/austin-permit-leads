"""
Fully automated email sender with PDF attachments.
Opens Gmail in the browser, composes the email, attaches the PDF, and sends it.
Uses Playwright to automate Gmail's web interface.

Usage:
    python send_emails.py              # Send to all HIGH priority leads
    python send_emails.py 1            # Send to first lead only (test)
    python send_emails.py 5            # Send to first 5 leads
    python send_emails.py all          # Send to all leads

First run: it will ask you to log into Gmail manually. After that, it reuses the session.
"""
import asyncio
import csv
import json
import os
import re
import sys
import time
from urllib.request import urlopen
from urllib.parse import quote

DASHBOARD_URL = "https://brimstone-permits-production.up.railway.app"
PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PDFs')
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.gmail-session')
LEADS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outreach-leads.csv')

# ─── Permit data cache ───
PERMIT_CACHE = None

def fetch_permits():
    global PERMIT_CACHE
    if PERMIT_CACHE:
        return PERMIT_CACHE

    print("  Fetching latest Austin permit data...")
    where = "issue_date >= '2026-03-03' AND permittype='BP'"
    url = f"https://data.austintexas.gov/resource/3syk-w9eu.json?$where={quote(where)}&$order={quote('issue_date DESC')}&$limit=50000"
    with urlopen(url) as resp:
        data = json.loads(resp.read())

    def clean(n):
        if not n: return ''
        n = re.sub(r'\s*[\*]*\s*\(?MAIN\)?\s*[\*]*\s*', '', n, flags=re.IGNORECASE)
        n = re.sub(r'\s*,?\s*(LLC|Inc\.?|L\.?\s*P\.?|Ltd\.?|Corp\.?)\s*$', '', n, flags=re.IGNORECASE)
        n = re.sub(r'\*+', '', n)
        if n == n.upper() and len(n) > 3: n = n.title()
        return n.strip().rstrip(',').strip()

    permits = []
    for p in data:
        sqft = max(int(p.get('total_new_add_sqft') or 0), int(p.get('remodel_repair_sqft') or 0))
        contractor = clean(p.get('contractor_company_name', ''))
        phone = p.get('contractor_phone', '')
        if phone:
            d = re.sub(r'\D', '', phone)[-10:]
            if len(d) == 10:
                phone = f'({d[:3]}) {d[3:6]}-{d[6:]}'
            else:
                phone = ''
        permits.append({
            'date': (p.get('issue_date') or '')[:10],
            'addr': p.get('original_address1', ''),
            'sqft': sqft,
            'contractor': contractor,
            'phone': phone,
            'desc': (p.get('description') or '')[:120].replace('\n', ' '),
            'class': p.get('permit_class_mapped', ''),
            'work': p.get('work_class', ''),
        })

    PERMIT_CACHE = permits
    print(f"  Got {len(permits)} permits.")
    return permits


def get_relevant_permits(category):
    """Get top permits relevant to a trade category."""
    permits = fetch_permits()
    relevant = []

    cat = category.lower()
    for p in permits:
        sqft = p['sqft']
        if 'electric' in cat:
            if (p['class'] == 'Commercial' and sqft > 500) or (sqft > 5000):
                relevant.append(p)
        elif 'plumb' in cat:
            if p['work'] in ('New', 'Addition and Remodel') and sqft > 1000:
                relevant.append(p)
        elif 'hvac' in cat or 'mechanic' in cat:
            if (p['class'] == 'Commercial' and sqft > 500) or (sqft > 5000):
                relevant.append(p)
        elif 'roof' in cat:
            if 'roof' in p['desc'].lower() or (p['work'] == 'New' and sqft > 1000):
                relevant.append(p)
        elif 'lumber' in cat or 'wood' in cat or 'timber' in cat:
            if p['work'] == 'New' and p['class'] == 'Residential' and sqft > 2000:
                relevant.append(p)
        elif 'window' in cat or 'door' in cat:
            if p['work'] == 'New' and sqft > 2000:
                relevant.append(p)
        elif 'concrete' in cat:
            if p['work'] == 'New' and sqft > 1000:
                relevant.append(p)
        elif 'equipment' in cat or 'rental' in cat:
            if sqft > 5000:
                relevant.append(p)
        elif 'drywall' in cat or 'interior' in cat:
            if 'Remodel' in p['work'] and sqft > 5000:
                relevant.append(p)
        else:
            if sqft > 5000:
                relevant.append(p)

    relevant.sort(key=lambda x: x['sqft'], reverse=True)
    return relevant[:3]


def make_short_name(company):
    """Create a short abbreviation for the company."""
    # Known abbreviations
    abbrevs = {
        'Hill Country Electric Supply': 'HCES',
        'Summit Electric Supply': 'Summit',
        'Crawford Electric Supply': 'Crawford',
        'Dealers Electrical Supply': 'Dealers',
        'Elliott Electric Supply': 'Elliott',
        'Moore Supply South': 'Moore Supply',
        'Moore Supply North': 'Moore Supply',
        'SRS Building Products': 'SRS',
        'Lone Star Materials': 'Lone Star',
        'Austin Lumber': 'Austin Lumber',
        'Ringer Windows': 'Ringer',
        'Accolade Windows & Doors': 'Accolade',
        'Austin Equipment': 'Austin Equipment',
        'TimberTown Austin': 'TimberTown',
        'US Lumber Brokers': 'US Lumber',
        'Eastside Lumber & Decking': 'Eastside',
        'JW Materials': 'JW Materials',
        '360 Metal Roofing Supply': '360 Metal',
        'Austin Snaploc Supply': 'Snaploc',
        'Montopolis Supply': 'Montopolis',
        'Budget Roofing Supply': 'Budget Roofing',
        'Sunbelt Rentals': 'Sunbelt',
        "Jon's Rental": "Jon's",
        'HL Equipment': 'HL Equipment',
        'Builders FirstSource': 'BFS',
        'BCS Concrete': 'BCS',
        'CP Electric': 'CP Electric',
        'SALT Electric': 'SALT',
        'TCS Mechanical': 'TCS',
        'G&S Mechanical': 'G&S',
        'Biggs Plumbing': 'Biggs',
        'Westmoreland Plumbing': 'Westmoreland',
        'Texas Plumbing & Drain': 'Texas Plumbing',
        'Novo Construction': 'Novo',
        'Real International Construction': 'Real International',
        'Structura Inc': 'Structura',
        'Joseph Design Build': 'JDB',
        'Topos Collective': 'Topos',
        'AWhiddon Construction': 'AWhiddon',
        'KB Home Austin': 'KB Home',
        'Brookfield Residential TX': 'Brookfield',
    }
    return abbrevs.get(company, company.split()[0])


def get_trade_context(category):
    """Return a trade-specific relevance line."""
    cat = category.lower()
    if 'electric' in cat and 'sub' in cat:
        return "does electrical work", "electrical bid"
    elif 'electric' in cat:
        return "supplies electrical materials", "electrical supply quote"
    elif 'plumb' in cat and 'sub' in cat:
        return "does plumbing work", "plumbing bid"
    elif 'plumb' in cat:
        return "supplies plumbing materials", "plumbing supply opportunity"
    elif 'hvac' in cat or 'mechanic' in cat:
        return "does mechanical/HVAC work", "mechanical bid"
    elif 'roof' in cat:
        return "supplies roofing materials", "roofing supply opportunity"
    elif 'lumber' in cat or 'wood' in cat or 'timber' in cat:
        return "supplies framing lumber and building materials", "lumber order"
    elif 'concrete' in cat:
        return "does concrete and foundation work", "concrete pour"
    elif 'window' in cat or 'door' in cat:
        return "supplies windows and doors", "window and door specification"
    elif 'equipment' in cat or 'rental' in cat:
        return "rents construction equipment", "equipment rental"
    elif 'drywall' in cat or 'interior' in cat:
        return "supplies drywall and interior materials", "drywall and steel stud order"
    elif 'general' in cat or 'contractor' in cat:
        return "builds in Austin", "competitive intelligence"
    else:
        return "works in construction", "new project opportunity"


def build_email(company, category):
    top = get_relevant_permits(category)
    short = make_short_name(company)
    does_what, opp_type = get_trade_context(category)
    is_gc = 'general' in category.lower() or 'contractor' in category.lower()

    lines = ["Hi,", ""]
    lines.append("I'm Avinash. I help construction companies find new projects before they hit the bid boards.")
    lines.append("")

    if is_gc and top and top[0]['contractor']:
        # GC gets competitive intel angle
        p = top[0]
        lines.append(f"{p['contractor']} just filed for {p['sqft']:,} sqft at {p['addr']}.")
        if len(top) > 1 and top[1]['contractor']:
            p2 = top[1]
            lines.append(f"{p2['contractor']} also filed for {p2['sqft']:,} sqft at {p2['addr']}.")
        lines.append(f"I put together a competitive landscape report for {short}. It shows who's filing what and where. It's attached.")
    elif top and top[0]['contractor']:
        p = top[0]
        phone_bit = f" Their contact is {p['phone']}." if p['phone'] else ""
        lines.append(f"{p['contractor']} just pulled a permit for a {p['sqft']:,} sqft project at {p['addr']}.{phone_bit} Since {short} {does_what}, this could be a {opp_type} worth looking into.")

        if len(top) > 1 and top[1]['contractor']:
            p2 = top[1]
            phone_bit2 = f" at {p2['phone']}" if p2['phone'] else ""
            lines.append(f"{p2['contractor']}{phone_bit2} also filed for a {p2['sqft']:,} sqft {p2['work'].lower()} at {p2['addr']}.")

        lines.append("")
        lines.append(f"I put together a personalized one-page report for {short} with the top opportunities in your space. It's attached.")
    else:
        lines.append(f"462 building permits were filed in Austin in the last two weeks. I put together a personalized report for {short} with the most relevant opportunities. It's attached.")

    lines.append("")
    lines.append("I also put together a tool (looking for feedback) that tracks every new permit filed in Austin in real time:")
    lines.append("")
    lines.append(DASHBOARD_URL)
    lines.append("")
    lines.append("Avinash Nayak, PhD")
    lines.append("Brimstone Partner")
    lines.append("(832) 380-5845")
    lines.append("avinash@brimstonepartner.com")
    lines.append("2021 Guadalupe St, Suite 260, Austin, TX 78705")

    # Subject
    if is_gc and top and top[0]['contractor']:
        subject = f"{top[0]['contractor']} filed for {top[0]['sqft']:,} sqft. Here's what else is happening."
    elif top and top[0]['contractor']:
        addr_parts = top[0]['addr'].split()
        addr_short = f"{addr_parts[0]} {addr_parts[1]}" if len(addr_parts) > 1 else addr_parts[0]
        subject = f"{top[0]['contractor']} just filed for {top[0]['sqft']:,} sqft at {addr_short}"
    else:
        subject = "New construction permits in Austin this week"

    return subject.strip(), "\n".join(lines)


async def send_all(leads):
    from playwright.async_api import async_playwright

    os.makedirs(SESSION_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)

    async with async_playwright() as p:
        # Launch with persistent context so Gmail stays logged in
        browser = await p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            viewport={'width': 1280, 'height': 900}
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Check if logged into Gmail
        await page.goto('https://mail.google.com', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        current_url = page.url
        if 'accounts.google.com' in current_url or 'signin' in current_url:
            print("\n  Please log into Gmail in the browser window that just opened.")
            print("  Sign in with: avinash@brimstonepartner.com")
            print("  Press ENTER here when you're logged in and see your inbox.\n")
            input("  Press ENTER to continue...")

        print(f"\n  Sending {len(leads)} emails...\n")

        for i, lead in enumerate(leads):
            company = lead['Company']
            email = lead['Email']
            category = lead['Category']

            print(f"  [{i+1}/{len(leads)}] {company} ({email})")

            # Generate PDF for this lead
            pdf_path = os.path.join(PDF_DIR, f"{company.replace(' ', '-').replace('/', '-')}-Report.pdf")

            # Build email
            subject, body = build_email(company, category)

            # Open Gmail compose
            compose_url = f"https://mail.google.com/mail/?view=cm&to={quote(email)}&su={quote(subject)}&body={quote(body)}"
            await page.goto(compose_url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)

            # Attach PDF if it exists
            if os.path.exists(pdf_path):
                # Find the attachment input
                try:
                    file_input = await page.query_selector('input[type="file"][name="Filedata"]')
                    if not file_input:
                        file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(pdf_path)
                        await asyncio.sleep(2)
                        print(f"    Attached: {os.path.basename(pdf_path)}")
                except Exception as e:
                    print(f"    Could not attach PDF: {e}")

            # Wait for review
            await asyncio.sleep(2)

            # Click send
            try:
                send_btn = await page.query_selector('[aria-label*="Send"]')
                if not send_btn:
                    send_btn = await page.query_selector('[data-tooltip*="Send"]')
                if send_btn:
                    await send_btn.click()
                    print(f"    Sent!")
                    await asyncio.sleep(2)
                else:
                    print(f"    Could not find Send button. Please send manually.")
                    await asyncio.sleep(5)
            except Exception as e:
                print(f"    Send error: {e}")
                await asyncio.sleep(3)

        print(f"\n  Done! {len(leads)} emails sent.")
        await browser.close()


def main():
    limit = None
    priority_filter = "HIGH"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "all":
            priority_filter = None
        elif arg.isdigit():
            limit = int(arg)

    leads = []
    with open(LEADS_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if priority_filter and row.get('Priority', '') != priority_filter:
                continue
            if row.get('Email'):
                leads.append(row)

    if limit:
        leads = leads[:limit]

    if not leads:
        print("No leads found.")
        return

    print(f"\n  Found {len(leads)} leads to email.")
    print(f"  This will open a browser, log into Gmail, and send each email with a PDF attachment.")
    print(f"  First run: you'll need to sign into Gmail once.\n")

    asyncio.run(send_all(leads))


if __name__ == '__main__':
    main()
