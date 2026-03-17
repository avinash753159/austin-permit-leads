"""
Report generator for the Pre-Construction Intelligence Engine.
Produces CSV export, markdown report, and dashboard HTML from the leads database.
"""
import csv
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CSV_PATH, REPORT_PATH, BASE_DIR
from db import (get_conn, get_all_leads, get_leads_by_stage, get_leads_by_source,
                get_recent_leads, get_top_leads_by_value, get_stats)
from scrapers.base import setup_logging

logger = setup_logging()

CSV_COLUMNS = [
    'discovered_date', 'source', 'project_name', 'address', 'developer_owner',
    'architect', 'contractor', 'description', 'estimated_value_raw',
    'estimated_sqft', 'project_type', 'stage', 'source_url', 'contact_info',
    'ai_confidence', 'analysis_method',
]


def generate_csv():
    """Generate CSV export of all leads."""
    conn = get_conn()
    leads = get_all_leads(conn, include_duplicates=False)
    conn.close()

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)

    logger.info(f"CSV exported: {len(leads)} leads -> {CSV_PATH}")
    return len(leads)


def generate_report():
    """Generate markdown report."""
    conn = get_conn()
    stats = get_stats(conn)
    by_source = get_leads_by_source(conn)
    by_stage = get_leads_by_stage(conn)
    top_leads = get_top_leads_by_value(conn, limit=15)
    recent = get_recent_leads(conn, days=7)
    all_leads = get_all_leads(conn, include_duplicates=False)
    conn.close()

    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    method_str = ', '.join(f"{v} {k}" for k, v in stats['by_method'].items()) if stats['by_method'] else 'none'

    source_labels = {
        'news': 'Local News',
        'public_bid': 'Public Bids',
        'firm_announcement': 'Firm Announcements',
        'council_agenda': 'Council Agendas',
        'zoning_case': 'Zoning Cases',
        'plat_record': 'Plat Records',
    }

    lines = []
    lines.append(f"# Pre-Construction Intelligence Report")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Coverage:** Austin, TX")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append(f"- **{stats['total']}** total leads found")
    lines.append(f"- **{len(recent)}** new leads in last 7 days")
    lines.append(f"- Analysis method: {method_str}")
    lines.append("")

    # By Source
    lines.append("## By Source")
    for src, cnt in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        label = source_labels.get(src, src)
        lines.append(f"- {label}: **{cnt}** leads")
    lines.append("")

    # By Stage
    lines.append("## By Stage")
    stage_order = ['Rumor', 'Planning', 'Zoning', 'Design', 'Bidding', 'Pre-Permit']
    for stage in stage_order:
        cnt = by_stage.get(stage, 0)
        if cnt > 0:
            lines.append(f"- {stage}: **{cnt}**")
    lines.append("")

    # Top Leads by Value
    if top_leads:
        lines.append("## Top Leads by Estimated Value")
        lines.append("")
        lines.append("| # | Project | Address | Value | Developer | Stage | Source |")
        lines.append("|---|---------|---------|-------|-----------|-------|--------|")
        for i, lead in enumerate(top_leads, 1):
            name = (lead['project_name'] or 'Unknown')[:50]
            addr = (lead['address'] or 'N/A')[:30]
            val = lead['estimated_value_raw'] or 'N/A'
            dev = (lead['developer_owner'] or 'N/A')[:25]
            stage = lead['stage'] or 'N/A'
            src = source_labels.get(lead['source'], lead['source'])
            lines.append(f"| {i} | {name} | {addr} | {val} | {dev} | {stage} | {src} |")
        lines.append("")

    # New This Week
    if recent:
        lines.append("## New This Week")
        lines.append("")
        lines.append("| Date | Project | Address | Value | Stage | Confidence |")
        lines.append("|------|---------|---------|-------|-------|------------|")
        for lead in recent[:20]:
            date = lead['discovered_date'] or ''
            name = (lead['project_name'] or 'Unknown')[:50]
            addr = (lead['address'] or 'N/A')[:30]
            val = lead['estimated_value_raw'] or 'N/A'
            stage = lead['stage'] or 'N/A'
            conf = lead['ai_confidence'] or 'LOW'
            lines.append(f"| {date} | {name} | {addr} | {val} | {stage} | {conf} |")
        lines.append("")

    # All Leads (compact)
    if all_leads:
        lines.append("## All Leads")
        lines.append("")
        lines.append("| # | Project | Address | Value | Sq Ft | Type | Stage | Confidence |")
        lines.append("|---|---------|---------|-------|-------|------|-------|------------|")
        for i, lead in enumerate(all_leads, 1):
            name = (lead['project_name'] or 'Unknown')[:45]
            addr = (lead['address'] or 'N/A')[:25]
            val = lead['estimated_value_raw'] or ''
            sqft = lead['estimated_sqft'] or ''
            ptype = lead['project_type'] or ''
            stage = lead['stage'] or ''
            conf = lead['ai_confidence'] or 'LOW'
            lines.append(f"| {i} | {name} | {addr} | {val} | {sqft} | {ptype} | {stage} | {conf} |")
        lines.append("")

    report = '\n'.join(lines)

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"Report generated: {REPORT_PATH}")
    return stats['total']


def generate_dashboard():
    """Generate the dashboard HTML with embedded lead data (no fetch needed)."""
    conn = get_conn()
    leads = get_all_leads(conn, include_duplicates=False)
    conn.close()

    # Convert leads to JSON-safe list
    json_leads = []
    for lead in leads:
        json_leads.append({
            'discovered_date': lead.get('discovered_date', ''),
            'source': lead.get('source', ''),
            'project_name': lead.get('project_name', ''),
            'address': lead.get('address', ''),
            'developer_owner': lead.get('developer_owner', ''),
            'architect': lead.get('architect', ''),
            'contractor': lead.get('contractor', ''),
            'description': lead.get('description', ''),
            'estimated_value_raw': lead.get('estimated_value_raw', ''),
            'estimated_sqft': lead.get('estimated_sqft', ''),
            'project_type': lead.get('project_type', ''),
            'stage': lead.get('stage', ''),
            'source_url': lead.get('source_url', ''),
            'contact_info': lead.get('contact_info', ''),
            'ai_confidence': lead.get('ai_confidence', 'LOW'),
            'analysis_method': lead.get('analysis_method', 'regex'),
        })

    # Read the dashboard template
    dashboard_path = os.path.join(BASE_DIR, 'dashboard.html')
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Embed data directly into the initial ALL_LEADS declaration
    json_str = json.dumps(json_leads, ensure_ascii=True)

    # Replace the empty array initialization with actual data
    old_init = 'let ALL_LEADS = [];'
    new_init = f'let ALL_LEADS = {json_str};'
    html = html.replace(old_init, new_init, 1)

    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"Dashboard updated with {len(json_leads)} embedded leads")


def generate_all():
    """Generate CSV, report, and dashboard."""
    csv_count = generate_csv()
    report_count = generate_report()
    generate_dashboard()
    return csv_count


if __name__ == '__main__':
    generate_all()
