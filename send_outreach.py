"""
Opens Gmail compose windows in your browser with pre-filled outreach emails.
You just review and hit Send.

Usage:
    python send_outreach.py          # Opens all HIGH priority leads
    python send_outreach.py 5        # Opens first 5 leads
    python send_outreach.py all      # Opens all leads
"""
import csv
import sys
import webbrowser
import time
from urllib.parse import quote

DASHBOARD_URL = "https://permits.brimstonepartner.com"

def build_email_body(company, category):
    return f"""Hi,

I track every new building permit filed in Austin, San Antonio, and Dallas in real time.

This week alone there were hundreds of new permits filed — residential and commercial — with the GC's name, phone number, and project details on each one.

I put together a live dashboard where you can filter by project type, size, and contractor:

{DASHBOARD_URL}

You can also download the full list as a CSV.

I thought this might be useful for {company} since new permits mean new {category.lower()} opportunities. Happy to walk you through it in a quick call.

Best,
Avinash Nayak
Brimstone Partner
avinash@brimstonepartner.com"""


def build_subject(company):
    return f"New construction permits in Austin this week — thought this might be useful"


def main():
    limit = None
    priority_filter = "HIGH"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "all":
            priority_filter = None
        elif arg.isdigit():
            limit = int(arg)
        else:
            priority_filter = arg.upper()

    leads = []
    with open('outreach-leads.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if priority_filter and row.get('Priority', '') != priority_filter:
                continue
            if row.get('Email'):
                leads.append(row)

    if limit:
        leads = leads[:limit]

    if not leads:
        print("No leads found matching criteria.")
        return

    print(f"\nOpening {len(leads)} Gmail compose windows...")
    print(f"Review each one and hit Send.\n")

    for i, lead in enumerate(leads):
        company = lead['Company']
        email = lead['Email']
        category = lead['Category']

        subject = quote(build_subject(company))
        body = quote(build_email_body(company, category))

        gmail_url = f"https://mail.google.com/mail/?view=cm&to={email}&su={subject}&body={body}"

        print(f"  [{i+1}/{len(leads)}] {company} — {email}")
        webbrowser.open(gmail_url)

        if i < len(leads) - 1:
            time.sleep(2)  # Small delay so browser doesn't choke

    print(f"\nDone! {len(leads)} compose windows opened.")
    print("Review each email and hit Send.")


if __name__ == '__main__':
    main()
