"""
Creates Gmail DRAFTS with personalized emails and PDF attachments.
Does NOT send anything. You review the drafts in Gmail and send manually.

Usage:
    python send_emails.py              # Draft all HIGH priority leads
    python send_emails.py 1            # Draft first lead only (test)
    python send_emails.py 5            # Draft first 5 leads
    python send_emails.py all          # Draft all leads

First run: it will ask you to log into Gmail manually. After that, it reuses the session.
PDFs must exist in the PDFs/ folder. Run generate_pdfs.py first.
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'PDFs')
PDF_NEW_DIR = os.path.join(BASE_DIR, 'PDFs-New')
SESSION_DIR = os.path.join(BASE_DIR, '.gmail-session')
LEADS_FILE = os.path.join(BASE_DIR, 'outreach-leads.csv')
LEADS_NEW_FILE = os.path.join(BASE_DIR, 'outreach-leads-new.csv')

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
        n = re.sub(r'\s*[\{\(]\s*formal?ly[^}\)]*[\}\)]\s*', '', n, flags=re.IGNORECASE)
        n = re.sub(r'\s*\(d/b/a[^)]*\)\s*', ' ', n, flags=re.IGNORECASE)
        n = re.sub(r'\s*,?\s*(LLC|Inc\.?|L\.?\s*P\.?|Ltd\.?|Corp\.?|Company|Co\.?)\s*$', '', n, flags=re.IGNORECASE)
        n = re.sub(r'\*+', '', n)
        # Fix missing spaces before capital letters (e.g. "ReedConstruction" -> "Reed Construction")
        n = re.sub(r'([a-z])([A-Z])', r'\1 \2', n)
        n = re.sub(r'\s{2,}', ' ', n)
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
            'addr': (p.get('original_address1', '') or '').title(),
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


# Track which permits have been used so each email is unique
used_permits = set()

def get_relevant_permits(category):
    """Get top permits relevant to a trade category. Rotates so each email is unique."""
    global used_permits
    permits = fetch_permits()
    relevant = []

    cat = category.lower()
    for p in permits:
        sqft = p['sqft']
        # Create a unique key for this permit
        pkey = f"{p['contractor']}_{p['addr']}_{sqft}"

        if 'electric' in cat:
            if (p['class'] == 'Commercial' and sqft > 500) or (sqft > 5000):
                relevant.append((pkey, p))
        elif 'plumb' in cat:
            if p['work'] in ('New', 'Addition and Remodel') and sqft > 1000:
                relevant.append((pkey, p))
        elif 'hvac' in cat or 'mechanic' in cat:
            if (p['class'] == 'Commercial' and sqft > 500) or (sqft > 5000):
                relevant.append((pkey, p))
        elif 'roof' in cat:
            if 'roof' in p['desc'].lower() or (p['work'] == 'New' and sqft > 1000):
                relevant.append((pkey, p))
        elif 'lumber' in cat or 'wood' in cat or 'timber' in cat:
            if p['work'] == 'New' and p['class'] == 'Residential' and sqft > 2000:
                relevant.append((pkey, p))
        elif 'window' in cat or 'door' in cat:
            if p['work'] == 'New' and sqft > 2000:
                relevant.append((pkey, p))
        elif 'concrete' in cat:
            if p['work'] == 'New' and sqft > 1000:
                relevant.append((pkey, p))
        elif 'equipment' in cat or 'rental' in cat:
            if sqft > 5000:
                relevant.append((pkey, p))
        elif 'drywall' in cat or 'interior' in cat:
            if 'Remodel' in p['work'] and sqft > 5000:
                relevant.append((pkey, p))
        elif 'fire' in cat or 'sprinkler' in cat:
            if p['class'] == 'Commercial' and sqft > 500:
                relevant.append((pkey, p))
        elif 'steel' in cat or 'iron' in cat or 'metal fab' in cat or 'weld' in cat:
            if (p['class'] == 'Commercial' and sqft > 2000) or sqft > 5000:
                relevant.append((pkey, p))
        elif 'paint' in cat:
            if sqft > 3000:
                relevant.append((pkey, p))
        elif 'demol' in cat or 'excavat' in cat or 'paving' in cat or 'site' in cat:
            if p['work'] == 'New' and sqft > 2000:
                relevant.append((pkey, p))
        elif 'fence' in cat:
            if p['work'] == 'New' and p['class'] == 'Residential' and sqft > 1500:
                relevant.append((pkey, p))
        elif 'glass' in cat or 'glaz' in cat:
            if (p['class'] == 'Commercial' and sqft > 1000) or (p['work'] == 'New' and sqft > 3000):
                relevant.append((pkey, p))
        elif 'floor' in cat or 'tile' in cat:
            if 'Remodel' in p['work'] and sqft > 3000:
                relevant.append((pkey, p))
        else:
            if sqft > 5000:
                relevant.append((pkey, p))

    relevant.sort(key=lambda x: x[1]['sqft'], reverse=True)

    # Pick permits not yet used, fall back to used ones if needed
    result = []
    for pkey, p in relevant:
        if pkey not in used_permits:
            result.append(p)
            used_permits.add(pkey)
            if len(result) >= 3:
                break

    # If not enough unique ones, fill from top
    if len(result) < 2:
        for pkey, p in relevant:
            if p not in result:
                result.append(p)
                if len(result) >= 3:
                    break

    return result


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
        '360 Electrical Contractors': '360 Electric',
        'Fire King LLC': 'Fire King',
        'Concrete Contractors of Austin': 'CCA',
        'Comanche Roofing': 'Comanche',
        'Austin Iron': 'Austin Iron',
        'Clarke Kent Plumbing': 'Clarke Kent',
        'Stallion Paving': 'Stallion',
        'Patriot Erectors': 'Patriot',
        'Tex Painting': 'Tex Painting',
        'Venditti Demolition': 'Venditti',
        'Allied Fence & Security': 'Allied Fence',
        'Austin Glass & Mirror': 'Austin Glass',
        'Floor Masters ATX': 'Floor Masters',
        'Binswanger Glass': 'Binswanger',
        'EmpireWorks': 'EmpireWorks',
        'BEC Austin': 'BEC',
        'Apple Fence Company': 'Apple Fence',
        'Reliant Plumbing': 'Reliant',
        'Welding Austin': 'Welding Austin',
        'Reconstruction Experts': 'ReconExp',
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
    elif 'fire' in cat or 'sprinkler' in cat:
        return "installs fire protection systems", "fire sprinkler bid"
    elif 'steel' in cat or 'iron' in cat or 'metal fab' in cat or 'weld' in cat:
        return "does steel fabrication and erection", "structural steel bid"
    elif 'paint' in cat:
        return "does commercial and residential painting", "painting contract"
    elif 'demol' in cat or 'excavat' in cat or 'paving' in cat or 'site' in cat:
        return "handles demolition and site prep", "site work opportunity"
    elif 'fence' in cat:
        return "installs commercial and residential fencing", "fencing contract"
    elif 'glass' in cat or 'glaz' in cat:
        return "does commercial glazing and glass work", "glazing bid"
    elif 'floor' in cat or 'tile' in cat:
        return "installs commercial flooring", "flooring contract"
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
        p = top[0]
        line = f"{p['contractor']} just filed for {p['sqft']:,} sqft at {p['addr']}."
        if len(top) > 1 and top[1]['contractor']:
            p2 = top[1]
            line += f" {p2['contractor']} also filed for {p2['sqft']:,} sqft at {p2['addr']}."
        lines.append(line)
        lines.append(f"I put together a competitive landscape report for {short} showing who's filing what and where. It's attached.")
    elif top and top[0]['contractor']:
        p = top[0]
        phone_bit = f" at {p['phone']}" if p['phone'] else ""
        line = f"{p['contractor']} just pulled a permit for a {p['sqft']:,} sqft project at {p['addr']}{phone_bit}."

        if len(top) > 1 and top[1]['contractor']:
            p2 = top[1]
            if p2['contractor'] == p['contractor']:
                # Same contractor, merge into one sentence
                line += f" They also filed for a {p2['sqft']:,} sqft {p2['work'].lower()} at {p2['addr']}."
            else:
                phone_bit2 = f" at {p2['phone']}" if p2['phone'] else ""
                line += f" {p2['contractor']}{phone_bit2} also filed for a {p2['sqft']:,} sqft {p2['work'].lower()} at {p2['addr']}."

        line += f" Since {short} {does_what}, these could be worth looking into."
        lines.append(line)
        lines.append("")
        lines.append(f"I put together a personalized one-page report for {short} with the top opportunities in your space. It's attached.")
    else:
        lines.append(f"462 building permits were filed in Austin in the last two weeks. I put together a personalized report for {short} with the most relevant opportunities. It's attached.")

    lines.append("")
    lines.append(f"I also put together a tool (looking for feedback) that tracks every new permit filed in Austin in real time:\n{DASHBOARD_URL}")
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
            pdf_path = os.path.join(PDF_DIR, f"{company.replace(' ', '-').replace('/', '-').replace('&', 'and')}-Report.pdf")

            # Build email
            subject, body = build_email(company, category)

            try:
                # Open compose in a new tab
                page = await browser.new_page()
                compose_url = f"https://mail.google.com/mail/?view=cm&to={quote(email)}&su={quote(subject)}"
                await page.goto(compose_url, wait_until='commit', timeout=15000)
                await asyncio.sleep(5)

                # Wait for compose window to appear
                body_field = None
                for selector in ['[aria-label="Message Body"]', '[role="textbox"][g_editable="true"]', '.Am.aiL.Al.editable', '[contenteditable="true"]']:
                    try:
                        body_field = await page.wait_for_selector(selector, timeout=5000)
                        if body_field:
                            break
                    except:
                        continue

                if body_field:
                    await body_field.click()
                    await page.keyboard.type(body, delay=1)
                    await asyncio.sleep(1)
                    print(f"    Filled email body")
                else:
                    print(f"    Could not find body field, saving partial draft")

                # Attach PDF
                if os.path.exists(pdf_path):
                    file_inputs = await page.query_selector_all('input[type="file"]')
                    attached = False
                    for fi in file_inputs:
                        try:
                            await fi.set_input_files(pdf_path)
                            print(f"    Attached: {os.path.basename(pdf_path)}")
                            attached = True
                            await asyncio.sleep(3)
                            break
                        except:
                            continue
                    if not attached:
                        print(f"    Could not attach PDF")

                # Save as draft (close compose, Gmail auto-saves)
                await asyncio.sleep(1)

                # Try Save & Close button first
                saved = False
                for label in ['Save & close', 'Save & Close', 'Close']:
                    try:
                        btn = await page.query_selector(f'[aria-label="{label}"]')
                        if btn:
                            await btn.click()
                            saved = True
                            break
                    except:
                        continue

                if not saved:
                    # Ctrl+S to force save, then Escape to close
                    await page.keyboard.press('Control+s')
                    await asyncio.sleep(1)
                    await page.keyboard.press('Escape')

                await asyncio.sleep(2)
                print(f"    Saved as draft!")
                await page.close()

            except Exception as e:
                print(f"    Error: {e}")
                try:
                    await page.close()
                except:
                    pass

        print(f"\n  Done! {len(leads)} drafts created in Gmail.")
        print(f"  Go to Gmail > Drafts to review and send.")
        await browser.close()


def main():
    global PDF_DIR
    limit = None
    priority_filter = "HIGH"
    use_new = False
    leads_file = LEADS_FILE

    args = sys.argv[1:]
    if "--new" in args:
        use_new = True
        args.remove("--new")
        leads_file = LEADS_NEW_FILE
        PDF_DIR = PDF_NEW_DIR
        priority_filter = None  # Send all new leads by default
        print("\n  ** NEW LEADS ONLY MODE — using 20 new contacts **")

    if args:
        arg = args[0]
        if arg == "all":
            priority_filter = None
        elif arg.isdigit():
            limit = int(arg)

    leads = []
    with open(leads_file, 'r', encoding='utf-8') as f:
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
    print(f"  This will open a browser, log into Gmail, and create each draft with a PDF attachment.")
    print(f"  First run: you'll need to sign into Gmail once.\n")

    asyncio.run(send_all(leads))


if __name__ == '__main__':
    main()
