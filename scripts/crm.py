#!/usr/bin/env python3
"""
外贸客户 CRM — SQLite 轻量客户关系管理
用法:
  python crud.py add "公司名" "国家" "邮箱" "电话" "备注"
  python crud.py list [--status new|contacted|replied|negotiating|closed]
  python crud.py update <id> --status <status> [--notes "..."]
  python crud.py log <id> "沟通记录"
  python crud.py next  # 查看需要跟进的客户
  python crud.py stats # 统计概览
"""

import sqlite3, sys, os, json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "crm.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            country TEXT,
            website TEXT,
            category TEXT,
            source TEXT,
            status TEXT DEFAULT 'new',
            priority INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            name TEXT,
            title TEXT,
            email TEXT,
            phone TEXT,
            whatsapp TEXT,
            linkedin TEXT,
            is_primary INTEGER DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            channel TEXT,  -- email, whatsapp, linkedin, phone
            direction TEXT DEFAULT 'outbound',
            content TEXT,
            status TEXT,  -- sent, delivered, replied, bounced
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """)
    conn.commit()
    conn.close()

def cmd_add(args):
    if len(args) < 2:
        print("Usage: add 'Company' 'Country' ['Email'] ['Phone'] ['Notes']")
        return
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO customers (company_name, country, status, priority) VALUES (?,?, 'new', 3)",
        (args[0], args[1])
    )
    cid = cur.lastrowid
    if len(args) > 2 and args[2]:
        conn.execute("INSERT INTO contacts (customer_id, email) VALUES (?,?)", (cid, args[2]))
    if len(args) > 3 and args[3]:
        conn.execute("INSERT INTO contacts (customer_id, phone) VALUES (?,?)", (cid, args[3]))
    conn.commit()
    print(f"✅ Added customer #{cid}: {args[0]} ({args[1]})")

def cmd_list(args):
    status = None
    if "--status" in args:
        idx = args.index("--status")
        status = args[idx+1] if idx+1 < len(args) else None
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM customers WHERE status=? ORDER BY priority DESC, updated_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM customers ORDER BY priority DESC, updated_at DESC LIMIT 50"
        ).fetchall()
    if not rows:
        print("(empty)")
        return
    print(f"{'ID':>4} {'Status':>12} {'Pri':>3} {'Company':<25} {'Country':<12} {'Last Contact':<12}")
    print("-"*80)
    for r in rows:
        last = r['updated_at'][:10] if r['updated_at'] else '-'
        print(f"{r['id']:>4} {r['status']:>12} {r['priority']:>3} {r['company_name']:<25} {r['country'] or '-':<12} {last:<12}")

def cmd_update(args):
    if len(args) < 2:
        print("Usage: update <id> --status <status> [--notes '...'] [--priority N]")
        return
    cid = args[0]
    conn = get_db()
    updates = []
    params = []
    if "--status" in args:
        idx = args.index("--status")
        updates.append("status=?")
        params.append(args[idx+1])
    if "--priority" in args:
        idx = args.index("--priority")
        updates.append("priority=?")
        params.append(int(args[idx+1]))
    if "--notes" in args:
        idx = args.index("--notes")
        conn.execute("INSERT INTO outreach_log (customer_id, channel, content, status) VALUES (?, 'note', ?, 'note')",
                     (cid, args[idx+1]))
    if updates:
        updates.append("updated_at=CURRENT_TIMESTAMP")
        params.append(cid)
        conn.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        print(f"✅ Updated customer #{cid}: {', '.join(updates)}")
    else:
        print("No changes specified")

def cmd_log(args):
    if len(args) < 2:
        print("Usage: log <id> 'message' [--channel email|whatsapp|phone] [--status sent|replied]")
        return
    cid = args[0]
    msg = args[1]
    channel = "note"
    status = "note"
    if "--channel" in args:
        channel = args[args.index("--channel")+1]
    if "--status" in args:
        status = args[args.index("--status")+1]
    conn = get_db()
    conn.execute("INSERT INTO outreach_log (customer_id, channel, content, status) VALUES (?,?,?,?)",
                 (cid, channel, msg, status))
    conn.execute("UPDATE customers SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (cid,))
    conn.commit()
    print(f"✅ Logged for customer #{cid}: [{channel}] {status}")

def cmd_next(args=None):
    """Show customers needing follow-up: new or no contact in 7+ days"""
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, MAX(o.created_at) as last_outreach
        FROM customers c
        LEFT JOIN outreach_log o ON c.id = o.customer_id
        WHERE c.status IN ('new', 'contacted')
        GROUP BY c.id
        HAVING last_outreach IS NULL OR last_outreach < datetime('now', '-7 days')
        ORDER BY c.priority DESC
        LIMIT 20
    """).fetchall()
    if not rows:
        print("✅ All caught up! No customers need follow-up right now.")
        return
    print(f"{'ID':>4} {'Pri':>3} {'Company':<25} {'Status':>12} {'Last Outreach':<16}")
    print("-"*65)
    for r in rows:
        last = r['last_outreach'][:16] if r['last_outreach'] else 'never'
        print(f"{r['id']:>4} {r['priority']:>3} {r['company_name']:<25} {r['status']:>12} {last:<16}")

def cmd_stats(args=None):
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    by_status = conn.execute("SELECT status, COUNT(*) FROM customers GROUP BY status").fetchall()
    print(f"📊 Total customers: {total}")
    print(f"{'Status':<15} {'Count':>5}")
    print("-"*22)
    for s in by_status:
        print(f"{s[0]:<15} {s[1]:>5}")

def cmd_import(args):
    """Import customers from JSON file"""
    if len(args) < 1:
        print("Usage: import <file.json>")
        return
    with open(args[0]) as f:
        data = json.load(f)
    conn = get_db()
    count = 0
    for c in data:
        conn.execute(
            "INSERT INTO customers (company_name, country, website, category, source, status, priority) VALUES (?,?,?,?,?,?,?)",
            (c.get('company'), c.get('country'), c.get('website'), c.get('category'), c.get('source'), c.get('status','new'), c.get('priority',3))
        )
        count += 1
    conn.commit()
    print(f"✅ Imported {count} customers")

if __name__ == "__main__":
    init_db()
    if len(sys.argv) < 2:
        print("Commands: add, list, update, log, next, stats, import")
        print("Example: python crud.py add 'Al Jamal' 'UAE' 'hijas@aljamalenterprises.com' '+971509805211'")
        sys.exit(0)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    {"add": cmd_add, "list": cmd_list, "update": cmd_update, "log": cmd_log, "next": cmd_next, "stats": cmd_stats, "import": cmd_import}.get(cmd, lambda a: print(f"Unknown command: {cmd}"))(args)
