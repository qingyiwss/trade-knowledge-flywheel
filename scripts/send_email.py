#!/usr/bin/env python3
"""
外贸自动开发信发送脚本
用法:
  python3 send_email.py <customer_id>          # 发送给指定客户
  python3 send_email.py --dry <customer_id>    # 预览不发送
  python3 send_email.py --all-new              # 给所有 new 状态客户发送
  python3 send_email.py --followup <days>      # 给 N 天前联系过的发跟进
"""

import sys, os, subprocess, sqlite3

DB_PATH = "/root/code/trade-knowledge-flywheel/crm.db"
CRM_SCRIPT = "/root/code/trade-knowledge-flywheel/scripts/crm.py"
FROM_NAME = "Lao Wei"
FROM_EMAIL = "ud.xiaoshan@gmail.com"

# 产品卖点（沧州化妆刷）— 口语化
FEATURES = """Here's what we can do together:
- OEM/ODM — your brand, your design, your packaging
- 50+ brush styles, from eye to kabuki
- MOQ starts at just 500 pcs, so you can test the market risk-free
- Vegan & cruelty-free certified (big plus for today's market)
- 15-20 day turnaround
- Factory price $1-5/pc — you sell at $10-30 in the Middle East, nice margin for both of us"""

FOLLOWUP_BODY = """Hey,

Just checking in on my earlier message about the Cangzhou brushes.

No rush at all — I know how busy things get. If the timing's not right, no worries. I'll circle back when it makes more sense.

All the best,
{sender_name}
Cangzhou, China"""

def get_customer(cid):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    contacts = conn.execute("SELECT * FROM contacts WHERE customer_id=? ORDER BY is_primary DESC", (cid,)).fetchall()
    conn.close()
    if not c:
        return None, None
    return c, contacts

def generate_email(customer, contacts, is_followup=False):
    company = customer['company_name']
    country = customer['country'] or 'your region'

    # Pick first contact with email
    email_to = None
    contact_name = ""
    for ct in contacts:
        if ct['email']:
            email_to = ct['email']
            contact_name = ct['name'] or ""
            break

    if not email_to:
        return None, None, "No email found"

    salutation = f"Hi {contact_name}," if contact_name else "Hello,"

    if is_followup:
        body = FOLLOWUP_BODY.format(sender_name=FROM_NAME, sender_email=FROM_EMAIL)
        subject = f"Re: Cangzhou Makeup Brushes — OEM Partnership for {company}"
    else:
        body = f"""{salutation}

I noticed {company} — you guys have a solid presence in the {country} beauty market.

My name's Lao Wei. I'm based in Cangzhou, China — that's the city that makes over 70% of the world's makeup brushes. Not a factory salesman, just someone who knows the right people here.

{FEATURES}

If this sounds interesting, happy to send a few samples your way — no commitment, just to see if there's a fit.

Cheers,
{FROM_NAME}
Cangzhou, China"""

    subject = f"Makeup brushes from Cangzhou — {company}"

    return email_to, subject, body

def send_email(to, subject, body, dry_run=False):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}To: {to}")
    print(f"Subject: {subject}")
    print(f"---")
    print(body)
    print(f"---")

    if dry_run:
        return True

    email_content = f"""From: {FROM_NAME} <{FROM_EMAIL}>
To: {to}
Subject: {subject}

{body}"""

    result = subprocess.run(
        ["himalaya", "template", "send"],
        input=email_content,
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode == 0:
        print(f"✅ Sent successfully")
        return True
    else:
        print(f"❌ Failed: {result.stderr.strip()}")
        return False

def log_outreach(cid, email_to, success):
    status = "sent" if success else "failed"
    subprocess.run([
        "python3", CRM_SCRIPT, "log", str(cid),
        f"Cold email sent to {email_to}",
        "--channel", "email",
        "--status", status
    ], capture_output=True)
    if success:
        subprocess.run([
            "python3", CRM_SCRIPT, "update", str(cid), "--status", "contacted"
        ], capture_output=True)

def main():
    dry_run = "--dry" in sys.argv
    followup = None
    all_new = "--all-new" in sys.argv

    if "--followup" in sys.argv:
        idx = sys.argv.index("--followup")
        followup = int(sys.argv[idx+1]) if idx+1 < len(sys.argv) else 7

    if all_new:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id FROM customers WHERE status='new'").fetchall()
        conn.close()
        ids = [str(r['id']) for r in rows]
    elif followup:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT c.id FROM customers c LEFT JOIN outreach_log o ON c.id=o.customer_id "
            "WHERE c.status IN ('new','contacted') GROUP BY c.id "
            "HAVING MAX(o.created_at) < datetime('now', ?) OR MAX(o.created_at) IS NULL",
            (f'-{followup} days',)
        ).fetchall()
        conn.close()
        ids = [str(r['id']) for r in rows]
    else:
        ids = [a for a in sys.argv[1:] if a.isdigit()]

    if not ids:
        print("Usage: send_email.py <id> [--dry] [--all-new] [--followup 7]")
        return

    for cid in ids:
        customer, contacts = get_customer(cid)
        if not customer:
            print(f"❌ Customer #{cid} not found")
            continue

        email_to, subject, body = generate_email(customer, contacts, is_followup=bool(followup))
        if not email_to:
            print(f"⚠️  Customer #{cid} ({customer['company_name']}) has no email — skipping")
            continue

        success = send_email(email_to, subject, body, dry_run=dry_run)
        if not dry_run:
            log_outreach(cid, email_to, success)

if __name__ == "__main__":
    main()
