"""
Weekly Permit Report Email
Fetches last 7 days of Austin building permits and sends a formatted email digest.

Setup:
  1. Set environment variables:
     EMAIL_FROM=your-email@gmail.com
     EMAIL_PASSWORD=your-app-password  (Gmail: use App Password, not regular password)
     EMAIL_TO=recipient@email.com      (comma-separated for multiple)
     SMTP_HOST=smtp.gmail.com          (optional, defaults to Gmail)
     SMTP_PORT=587                     (optional)

  2. Run manually:
     python weekly_email.py

  3. Or schedule weekly via cron (every Monday 8am):
     0 8 * * 1 cd /path/to/austin-permits && python weekly_email.py

  4. Or use GitHub Actions (see .github/workflows/weekly-report.yml)
"""
import json
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.request import urlopen
from urllib.parse import quote
from datetime import datetime, timedelta
from collections import defaultdict

# ─── Config ───
CITIES = {
    'austin': {
        'name': 'Austin',
        'api': 'https://data.austintexas.gov/resource/3syk-w9eu.json',
        'dashboard': 'https://avinash753159.github.io/austin-permit-leads/?city=austin',
    },
    'sanantonio': {
        'name': 'San Antonio',
        'api': 'https://data.sanantonio.gov/api/3/action/datastore_search',
        'dashboard': 'https://avinash753159.github.io/austin-permit-leads/?city=sanantonio',
    }
}

def clean_name(name):
    if not name:
        return ""
    name = re.sub(r'\s*[\*]*\s*\(?MAIN\)?\s*[\*]*\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[\{\(]\s*formal?ly.*?[\}\)]\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(d/b/a.*?\)\s*', ' ', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(registered trade name\)\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\*+', '', name)
    name = re.sub(r'\s{2,}', ' ', name)
    return name.strip().rstrip(',').strip()

def fetch_austin(since_str):
    where = f"issue_date >= '{since_str}' AND permittype='BP'"
    url = f"{CITIES['austin']['api']}?$where={quote(where)}&$order={quote('issue_date DESC')}&$limit=5000"
    with urlopen(url) as resp:
        data = json.loads(resp.read())
    permits = []
    for p in data:
        sqft = max(int(p.get('total_new_add_sqft') or 0), int(p.get('remodel_repair_sqft') or 0))
        permits.append({
            'date': (p.get('issue_date') or '')[:10],
            'address': p.get('original_address1') or p.get('permit_location') or '',
            'type': p.get('permit_class_mapped') or '',
            'work': p.get('work_class') or '',
            'sqft': sqft,
            'value': float(p.get('total_job_valuation') or 0),
            'contractor': clean_name(p.get('contractor_company_name') or p.get('contractor_full_name') or ''),
            'phone': p.get('contractor_phone') or '',
        })
    return permits

def fetch_sanantonio(since_str):
    url = f"{CITIES['sanantonio']['api']}?resource_id=c21106f9-3ef5-4f3a-8604-f992b4db7512&limit=5000&sort=DATE ISSUED desc"
    with urlopen(url.replace(' ', '%20')) as resp:
        data = json.loads(resp.read())
    permits = []
    for r in data.get('result', {}).get('records', []):
        issued = r.get('DATE ISSUED') or ''
        if issued < since_str:
            continue
        pt = (r.get('PERMIT TYPE') or '').lower()
        ptype = 'Residential' if 'res' in pt else ('Commercial' if 'comm' in pt else '')
        permits.append({
            'date': issued,
            'address': r.get('ADDRESS') or r.get('PROJECT NAME') or '',
            'type': ptype,
            'work': r.get('WORK TYPE') or '',
            'sqft': float(r.get('AREA (SF)') or 0),
            'value': float(r.get('DECLARED VALUATION') or 0),
            'contractor': clean_name(r.get('PRIMARY CONTACT') or ''),
            'phone': '',
        })
    return permits

def build_email_html(city_name, permits, dashboard_url):
    total = len(permits)
    total_sqft = sum(p['sqft'] for p in permits)
    total_value = sum(p['value'] for p in permits)
    residential = sum(1 for p in permits if p['type'] == 'Residential')
    commercial = sum(1 for p in permits if p['type'] == 'Commercial')

    # Top contractors
    counts = defaultdict(lambda: {'count': 0, 'sqft': 0, 'phone': ''})
    for p in permits:
        if p['contractor']:
            c = counts[p['contractor']]
            c['count'] += 1
            c['sqft'] += p['sqft']
            c['phone'] = c['phone'] or p['phone']
    top = sorted(counts.items(), key=lambda x: x[1]['count'], reverse=True)[:10]

    def fmt_sqft(v):
        if v >= 1e6: return f"{v/1e6:.1f}M"
        if v >= 1e3: return f"{v/1e3:,.0f}K"
        return f"{v:,.0f}"

    def fmt_money(v):
        if v <= 1: return ''
        if v >= 1e6: return f"${v/1e6:.1f}M"
        if v >= 1e3: return f"${v/1e3:,.0f}K"
        return f"${v:,.0f}"

    def fmt_phone(p):
        d = re.sub(r'\D', '', p)
        if len(d) == 10:
            return f"({d[:3]}) {d[3:6]}-{d[6:]}"
        return p

    # Build HTML
    top_rows = ""
    for name, info in top:
        phone_html = f'<a href="tel:{re.sub(r"[^0-9]", "", info["phone"])}" style="color:#C4763A;">{fmt_phone(info["phone"])}</a>' if info['phone'] else '—'
        top_rows += f"""<tr>
            <td style="padding:10px 12px;border-bottom:1px solid #f0ece6;font-weight:600;color:#2C1810;">{name}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0ece6;text-align:center;">{info['count']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0ece6;text-align:center;">{fmt_sqft(info['sqft']) if info['sqft'] else '—'}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0ece6;">{phone_html}</td>
        </tr>"""

    value_line = f" &middot; {fmt_money(total_value)} total value" if total_value > 100 else ""

    html = f"""
    <div style="max-width:640px;margin:0 auto;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#2C1810;background:#FDFBF7;">
      <div style="padding:32px 24px;text-align:center;border-bottom:1px solid #f0ece6;">
        <div style="display:inline-block;background:#F0F2EC;color:#7A8B6F;font-size:10px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;padding:5px 14px;border-radius:100px;margin-bottom:16px;">
          &#x1F7E2; {city_name} &middot; Weekly Permit Report
        </div>
        <h1 style="font-family:Georgia,serif;font-size:28px;font-weight:400;color:#2C1810;margin:0;line-height:1.2;">
          {total} new permits this week
        </h1>
        <p style="color:#8C7E73;font-size:14px;margin-top:8px;">
          {residential} residential &middot; {commercial} commercial &middot; {fmt_sqft(total_sqft)} sq ft{value_line}
        </p>
      </div>

      <div style="padding:24px;">
        <h2 style="font-family:Georgia,serif;font-size:18px;font-weight:400;color:#2C1810;margin:0 0 16px;">Most active contractors</h2>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="border-bottom:2px solid #f0ece6;">
              <th style="padding:8px 12px;text-align:left;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#B8ADA5;">Contractor</th>
              <th style="padding:8px 12px;text-align:center;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#B8ADA5;">Permits</th>
              <th style="padding:8px 12px;text-align:center;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#B8ADA5;">Sq Ft</th>
              <th style="padding:8px 12px;text-align:left;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#B8ADA5;">Phone</th>
            </tr>
          </thead>
          <tbody>{top_rows}</tbody>
        </table>
      </div>

      <div style="padding:24px;text-align:center;">
        <a href="{dashboard_url}" style="display:inline-block;padding:14px 32px;background:#2C1810;color:#FDFBF7;border-radius:100px;text-decoration:none;font-size:14px;font-weight:600;">
          View full dashboard &rarr;
        </a>
      </div>

      <div style="padding:16px 24px;text-align:center;border-top:1px solid #f0ece6;">
        <p style="font-size:11px;color:#B8ADA5;">
          Data from {city_name} open data portal. Updated weekly.<br>
          <a href="{dashboard_url}" style="color:#8C7E73;">Unsubscribe</a>
        </p>
      </div>
    </div>
    """
    return html

def send_email(subject, html_body, to_emails):
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    email_from = os.environ['EMAIL_FROM']
    email_pass = os.environ['EMAIL_PASSWORD']

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = ', '.join(to_emails)
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(email_from, email_pass)
        server.sendmail(email_from, to_emails, msg.as_string())

    print(f"Email sent to {', '.join(to_emails)}")

def main():
    since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    to_emails = [e.strip() for e in os.environ.get('EMAIL_TO', '').split(',') if e.strip()]

    if not to_emails:
        print("No EMAIL_TO set. Set it as an environment variable.")
        print("Example: EMAIL_TO=you@email.com python weekly_email.py")
        return

    for city_key in ['austin', 'sanantonio']:
        city = CITIES[city_key]
        print(f"\nFetching {city['name']} permits since {since}...")

        if city_key == 'austin':
            permits = fetch_austin(since)
        elif city_key == 'sanantonio':
            permits = fetch_sanantonio(since)
        else:
            continue

        if not permits:
            print(f"  No permits found for {city['name']}. Skipping.")
            continue

        print(f"  Got {len(permits)} permits.")

        html = build_email_html(city['name'], permits, city['dashboard'])
        subject = f"{city['name']}: {len(permits)} new building permits this week"
        send_email(subject, html, to_emails)

if __name__ == '__main__':
    main()
