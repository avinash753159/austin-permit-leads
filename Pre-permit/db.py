"""
SQLite database helpers for the Pre-Construction Intelligence Engine.
Handles table creation, inserts, queries, and deduplication.
"""
import sqlite3
import re
import os
from datetime import datetime
from config import DB_PATH


def get_conn():
    """Get a connection to the SQLite database, creating tables if needed."""
    is_new = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if is_new:
        create_tables(conn)
    return conn


def create_tables(conn):
    """Create the raw_scrapes and leads tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_scrapes (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            source_url TEXT,
            title TEXT,
            raw_text TEXT,
            scraped_at TEXT DEFAULT (datetime('now')),
            analyzed INTEGER DEFAULT 0,
            UNIQUE(source, source_url)
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY,
            raw_scrape_id INTEGER,
            discovered_date TEXT,
            source TEXT,
            project_name TEXT,
            address TEXT,
            city TEXT DEFAULT 'Austin',
            developer_owner TEXT,
            architect TEXT,
            contractor TEXT,
            description TEXT,
            estimated_value_raw TEXT,
            estimated_value_num REAL DEFAULT 0,
            estimated_sqft TEXT,
            estimated_sqft_num REAL DEFAULT 0,
            project_type TEXT,
            stage TEXT,
            source_url TEXT,
            contact_info TEXT,
            ai_confidence TEXT DEFAULT 'LOW',
            analysis_method TEXT DEFAULT 'regex',
            is_duplicate INTEGER DEFAULT 0,
            duplicate_of INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (raw_scrape_id) REFERENCES raw_scrapes(id)
        );

        CREATE INDEX IF NOT EXISTS idx_leads_address ON leads(address);
        CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
        CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
        CREATE INDEX IF NOT EXISTS idx_leads_discovered ON leads(discovered_date);
        CREATE INDEX IF NOT EXISTS idx_raw_analyzed ON raw_scrapes(analyzed);
    """)
    conn.commit()


def insert_raw_scrape(conn, source, source_url, title, raw_text):
    """Insert a raw scrape, skipping if same source+url already exists.
    Returns the row id or None if skipped."""
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO raw_scrapes (source, source_url, title, raw_text) VALUES (?, ?, ?, ?)",
            (source, source_url, title, raw_text)
        )
        conn.commit()
        if cur.lastrowid and cur.rowcount > 0:
            return cur.lastrowid
        # Already exists — return existing id
        row = conn.execute(
            "SELECT id FROM raw_scrapes WHERE source=? AND source_url=?",
            (source, source_url)
        ).fetchone()
        return row['id'] if row else None
    except Exception:
        return None


def get_unanalyzed_scrapes(conn):
    """Get all raw scrapes that haven't been analyzed yet."""
    rows = conn.execute(
        "SELECT * FROM raw_scrapes WHERE analyzed=0 ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def mark_analyzed(conn, scrape_id):
    """Mark a raw scrape as analyzed."""
    conn.execute("UPDATE raw_scrapes SET analyzed=1 WHERE id=?", (scrape_id,))
    conn.commit()


def normalize_value(raw_value):
    """Normalize a dollar value string to a number.
    '$50M' -> 50000000, '$2.5 million' -> 2500000, '$500K' -> 500000
    Returns (raw_string, numeric_value)"""
    if not raw_value:
        return '', 0

    raw = raw_value.strip()
    # Extract the number part
    num_match = re.search(r'[\d,.]+', raw)
    if not num_match:
        return raw, 0

    num_str = num_match.group().replace(',', '')
    try:
        num = float(num_str)
    except ValueError:
        return raw, 0

    # Check for multiplier
    lower = raw.lower()
    if 'billion' in lower or lower.endswith('b'):
        num *= 1_000_000_000
    elif 'million' in lower or lower.endswith('m'):
        num *= 1_000_000
    elif lower.endswith('k'):
        num *= 1_000

    return raw, num


def normalize_sqft(raw_sqft):
    """Normalize a square footage string to a number.
    Returns (raw_string, numeric_value)"""
    if not raw_sqft:
        return '', 0

    raw = raw_sqft.strip()
    num_match = re.search(r'[\d,.]+', raw)
    if not num_match:
        return raw, 0

    num_str = num_match.group().replace(',', '')
    try:
        num = float(num_str)
    except ValueError:
        return raw, 0

    return raw, num


def normalize_address(addr):
    """Normalize an address for dedup comparison.
    Lowercase, strip suffixes, remove unit numbers."""
    if not addr:
        return ''
    a = addr.lower().strip()
    # Remove unit/suite/apt numbers
    a = re.sub(r'\s*(unit|suite|ste|apt|#)\s*\w+', '', a)
    # Normalize street suffixes
    replacements = {
        ' street': ' st', ' drive': ' dr', ' boulevard': ' blvd',
        ' avenue': ' ave', ' road': ' rd', ' lane': ' ln',
        ' court': ' ct', ' circle': ' cir', ' parkway': ' pkwy',
        ' place': ' pl', ' trail': ' trl', ' way': ' way',
    }
    for full, short in replacements.items():
        a = a.replace(full, short)
    # Remove periods and extra spaces
    a = a.replace('.', '').strip()
    a = re.sub(r'\s+', ' ', a)
    return a


def insert_lead(conn, lead_dict):
    """Insert a lead with deduplication check.
    Returns the lead id or None if it's a duplicate."""
    addr = lead_dict.get('address', '')
    source = lead_dict.get('source', '')
    norm_addr = normalize_address(addr)

    # Check exact duplicate: same normalized address + same source
    if norm_addr:
        existing = conn.execute("""
            SELECT id, address FROM leads
            WHERE is_duplicate=0
        """).fetchall()

        for row in existing:
            if normalize_address(row['address']) == norm_addr and row['address']:
                # Same address already exists — check if same source
                same_source = conn.execute(
                    "SELECT id FROM leads WHERE id=? AND source=?",
                    (row['id'], source)
                ).fetchone()
                if same_source:
                    return None  # Exact duplicate, skip

                # Different source, same address — mark as duplicate but keep
                lead_dict['is_duplicate'] = 1
                lead_dict['duplicate_of'] = row['id']
                break

    # Normalize values
    val_raw, val_num = normalize_value(lead_dict.get('estimated_value_raw', ''))
    sqft_raw, sqft_num = normalize_sqft(lead_dict.get('estimated_sqft', ''))

    cur = conn.execute("""
        INSERT INTO leads (
            raw_scrape_id, discovered_date, source, project_name, address, city,
            developer_owner, architect, contractor, description,
            estimated_value_raw, estimated_value_num, estimated_sqft, estimated_sqft_num,
            project_type, stage, source_url, contact_info,
            ai_confidence, analysis_method, is_duplicate, duplicate_of
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead_dict.get('raw_scrape_id'),
        lead_dict.get('discovered_date', datetime.now().strftime('%Y-%m-%d')),
        source,
        lead_dict.get('project_name', ''),
        addr,
        lead_dict.get('city', 'Austin'),
        lead_dict.get('developer_owner', ''),
        lead_dict.get('architect', ''),
        lead_dict.get('contractor', ''),
        lead_dict.get('description', ''),
        val_raw, val_num,
        sqft_raw, sqft_num,
        lead_dict.get('project_type', ''),
        lead_dict.get('stage', ''),
        lead_dict.get('source_url', ''),
        lead_dict.get('contact_info', ''),
        lead_dict.get('ai_confidence', 'LOW'),
        lead_dict.get('analysis_method', 'regex'),
        lead_dict.get('is_duplicate', 0),
        lead_dict.get('duplicate_of'),
    ))
    conn.commit()
    return cur.lastrowid


def get_all_leads(conn, include_duplicates=False):
    """Get all leads, optionally excluding duplicates."""
    if include_duplicates:
        rows = conn.execute("SELECT * FROM leads ORDER BY discovered_date DESC, estimated_value_num DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM leads WHERE is_duplicate=0 ORDER BY discovered_date DESC, estimated_value_num DESC").fetchall()
    return [dict(r) for r in rows]


def get_leads_by_stage(conn):
    """Get lead counts by stage."""
    rows = conn.execute("""
        SELECT stage, COUNT(*) as cnt FROM leads WHERE is_duplicate=0
        GROUP BY stage ORDER BY cnt DESC
    """).fetchall()
    return {r['stage']: r['cnt'] for r in rows}


def get_leads_by_source(conn):
    """Get lead counts by source."""
    rows = conn.execute("""
        SELECT source, COUNT(*) as cnt FROM leads WHERE is_duplicate=0
        GROUP BY source ORDER BY cnt DESC
    """).fetchall()
    return {r['source']: r['cnt'] for r in rows}


def get_recent_leads(conn, days=7):
    """Get leads discovered in the last N days."""
    cutoff = datetime.now().strftime('%Y-%m-%d')
    rows = conn.execute("""
        SELECT * FROM leads
        WHERE is_duplicate=0 AND discovered_date >= date(?, '-' || ? || ' days')
        ORDER BY estimated_value_num DESC
    """, (cutoff, days)).fetchall()
    return [dict(r) for r in rows]


def get_top_leads_by_value(conn, limit=10):
    """Get top leads sorted by estimated value."""
    rows = conn.execute("""
        SELECT * FROM leads
        WHERE is_duplicate=0 AND estimated_value_num > 0
        ORDER BY estimated_value_num DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_stats(conn):
    """Get summary statistics."""
    total = conn.execute("SELECT COUNT(*) as c FROM leads WHERE is_duplicate=0").fetchone()['c']
    by_method = conn.execute("""
        SELECT analysis_method, COUNT(*) as c FROM leads WHERE is_duplicate=0
        GROUP BY analysis_method
    """).fetchall()
    return {
        'total': total,
        'by_method': {r['analysis_method']: r['c'] for r in by_method},
    }
