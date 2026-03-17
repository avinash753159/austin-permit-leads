"""
Generates outreach targets for pre-construction leads.
Identifies who would benefit from early-stage project intel and creates
a CSV of potential outreach targets + a summary of the best leads to pitch.
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BASE_DIR, PDF_DIR
from db import get_conn, get_all_leads, get_top_leads_by_value

OUTREACH_CSV = os.path.join(BASE_DIR, 'outreach-targets.csv')
PITCH_REPORT = os.path.join(BASE_DIR, 'pitch-report.md')

# The existing 61 outreach contacts from the post-permit system
# We load these to identify who would ALSO benefit from pre-construction intel
EXISTING_LEADS_FILE = os.path.join(os.path.dirname(BASE_DIR), 'outreach-leads.csv')


def load_existing_contacts():
    """Load existing outreach contacts from the post-permit system."""
    contacts = []
    if not os.path.exists(EXISTING_LEADS_FILE):
        return contacts

    with open(EXISTING_LEADS_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('Email'):
                contacts.append(row)
    return contacts


def identify_pre_construction_targets(contacts, leads):
    """Identify which existing contacts would benefit most from pre-construction intel.
    Returns a list of targets with matched leads."""

    # Subcontractors and suppliers benefit most from early project intel
    high_value_categories = [
        'Electrical Subcontractor', 'Plumbing Subcontractor', 'HVAC Subcontractor',
        'Concrete Subcontractor', 'Roofing Subcontractor', 'Steel Fabrication',
        'Painting Subcontractor', 'Demolition/Excavation', 'Fence Subcontractor',
        'Glass/Glazing', 'Flooring Subcontractor', 'Metal Fabrication',
        'Fire Protection Subcontractor', 'Concrete/Paving',
        'Electrical Supply', 'Plumbing Supply', 'Roofing/Building Materials',
        'Drywall/Interior Materials', 'Building Materials',
    ]

    targets = []
    for contact in contacts:
        category = contact.get('Category', '')
        priority = contact.get('Priority', 'LOW')

        # Check if this contact's category benefits from pre-construction data
        is_target = any(cat.lower() in category.lower() for cat in high_value_categories)

        if is_target:
            # Find relevant leads for this contact
            relevant = find_relevant_leads(category, leads)
            targets.append({
                'company': contact['Company'],
                'email': contact['Email'],
                'phone': contact.get('Phone', ''),
                'category': category,
                'priority': priority,
                'relevant_leads': len(relevant),
                'top_lead': relevant[0] if relevant else None,
            })

    # Sort by priority then by number of relevant leads
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    targets.sort(key=lambda x: (priority_order.get(x['priority'], 3), -x['relevant_leads']))

    return targets


def find_relevant_leads(category, leads):
    """Find pre-construction leads relevant to a trade category."""
    cat = category.lower()
    relevant = []

    for lead in leads:
        ptype = (lead.get('project_type') or '').lower()
        desc = (lead.get('description') or '').lower()
        value = lead.get('estimated_value_num', 0) or 0

        # Match based on trade
        match = False
        if 'electric' in cat and ('commercial' in ptype or value > 1000000):
            match = True
        elif 'plumb' in cat and value > 500000:
            match = True
        elif 'hvac' in cat or 'mechanic' in cat:
            if 'commercial' in ptype or value > 1000000:
                match = True
        elif 'concrete' in cat or 'paving' in cat:
            if value > 500000:
                match = True
        elif 'roof' in cat:
            if 'commercial' in ptype or value > 500000:
                match = True
        elif 'steel' in cat or 'iron' in cat or 'metal' in cat:
            if 'commercial' in ptype or value > 2000000:
                match = True
        elif 'paint' in cat:
            if value > 1000000:
                match = True
        elif 'glass' in cat or 'glaz' in cat:
            if 'commercial' in ptype:
                match = True
        elif 'floor' in cat:
            if 'commercial' in ptype or 'mixed' in ptype:
                match = True
        elif 'fire' in cat:
            if 'commercial' in ptype:
                match = True
        elif 'fence' in cat:
            if 'residential' in ptype:
                match = True
        elif 'supply' in cat or 'material' in cat:
            if value > 500000:
                match = True
        else:
            if value > 2000000:
                match = True

        if match:
            relevant.append(lead)

    # Sort by value
    relevant.sort(key=lambda x: x.get('estimated_value_num', 0) or 0, reverse=True)
    return relevant[:5]


def generate_outreach_csv(targets):
    """Generate CSV of outreach targets."""
    with open(OUTREACH_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Company', 'Email', 'Phone', 'Category', 'Priority',
                        'Relevant Pre-Construction Leads', 'Top Lead'])
        for t in targets:
            top = ''
            if t['top_lead']:
                tl = t['top_lead']
                top = f"{tl.get('project_name', '')[:50]} | {tl.get('estimated_value_raw', '')} | {tl.get('stage', '')}"
            writer.writerow([
                t['company'], t['email'], t['phone'], t['category'],
                t['priority'], t['relevant_leads'], top
            ])

    print(f"  Outreach targets CSV: {len(targets)} contacts -> {OUTREACH_CSV}")


def generate_pitch_report(targets, leads):
    """Generate a pitch report showing which leads to mention to which contacts."""
    top_leads = sorted(
        [l for l in leads if (l.get('estimated_value_num') or 0) > 0],
        key=lambda x: x.get('estimated_value_num', 0) or 0,
        reverse=True
    )[:10]

    lines = []
    lines.append("# Pre-Construction Outreach Pitch Report")
    lines.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y')}")
    lines.append("")

    lines.append("## Top Pre-Construction Leads to Pitch")
    lines.append("")
    if top_leads:
        for i, lead in enumerate(top_leads, 1):
            name = lead.get('project_name', 'Unknown')[:60]
            val = lead.get('estimated_value_raw', 'N/A')
            addr = lead.get('address', 'N/A')
            stage = lead.get('stage', 'N/A')
            dev = lead.get('developer_owner', 'N/A')
            lines.append(f"### {i}. {name}")
            lines.append(f"- **Value:** {val}")
            lines.append(f"- **Address:** {addr}")
            lines.append(f"- **Stage:** {stage}")
            lines.append(f"- **Developer:** {dev}")
            lines.append(f"- **Source:** {lead.get('source_url', 'N/A')}")
            lines.append("")
    else:
        lines.append("No high-value leads found yet. Run scrape_all.py to populate.")
        lines.append("")

    lines.append("## Outreach Targets (from existing contacts)")
    lines.append("")
    lines.append(f"**{len(targets)}** existing contacts would benefit from pre-construction intel:")
    lines.append("")
    lines.append("| Company | Category | Priority | Matching Leads |")
    lines.append("|---------|----------|----------|----------------|")
    for t in targets[:30]:
        lines.append(f"| {t['company']} | {t['category']} | {t['priority']} | {t['relevant_leads']} |")
    lines.append("")

    lines.append("## Pitch Template")
    lines.append("")
    lines.append("**Subject:** [Developer] planning [value] project at [address] — 6 months before permit")
    lines.append("")
    lines.append("Hi,")
    lines.append("")
    lines.append("I track construction projects in Austin at the pre-permit stage — before they show up on any bid board.")
    lines.append("")
    lines.append("[Developer] is planning a [value] [type] project at [address]. It's currently in the [stage] stage.")
    lines.append("Since [Company] [does what], this could be worth tracking for an early bid.")
    lines.append("")
    lines.append("I put together a report with [X] early-stage projects. Attached.")
    lines.append("")
    lines.append("Full pre-construction dashboard: [dashboard link]")
    lines.append("")
    lines.append("Avinash Nayak, PhD")
    lines.append("Brimstone Partner")
    lines.append("(832) 380-5845")
    lines.append("avinash@brimstonepartner.com")

    with open(PITCH_REPORT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  Pitch report: {PITCH_REPORT}")


def main():
    conn = get_conn()
    leads = get_all_leads(conn, include_duplicates=False)
    conn.close()

    print(f"\n  Found {len(leads)} pre-construction leads in database.")

    contacts = load_existing_contacts()
    print(f"  Loaded {len(contacts)} existing contacts from post-permit system.")

    targets = identify_pre_construction_targets(contacts, leads)
    print(f"  Identified {len(targets)} contacts who benefit from pre-construction intel.")
    print()

    generate_outreach_csv(targets)
    generate_pitch_report(targets, leads)
    print()


if __name__ == '__main__':
    main()
