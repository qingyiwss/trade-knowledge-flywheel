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
FROM_NAME = "ThinkingShirt"
FROM_EMAIL = "ud.xiaoshan@gmail.com"

# 产品卖点（沧州化妆刷）
FEATURES = """Our Cangzhou factory offers:
- OEM/ODM with your brand logo & custom packaging
- 50+ brush styles (face, eye, lip, kabuki, silicone)
- MOQ as low as 500 pcs per style
- Vegan/cruelty-free certification available
- 15-20 day production lead time
- Factory-direct pricing: $1-5/pc (retail $10-30 in Middle East)"""

FOLLOWUP_BODY = """Hi,

Just following up on my previous message about Cangzhou makeup brushes.

No pressure at all — I know you're busy. If now isn't the right time, I'm happy to reconnect when you're reviewing your beauty tools category.

Best regards,
{sender_name}
{sender_email}
Cangzhou, Hebei, China"""

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

    salutation = f"Dear {contact_name}," if contact_name else "Dear Purchasing Team,"

    if is_followup:
        body = FOLLOWUP_BODY.format(sender_name=FROM_NAME, sender_email=FROM_EMAIL)
        subject = f"Re: Cangzhou Makeup Brushes — OEM Partnership for {company}"
    else:
        body = f"""{salutation}

I came across {company} and was impressed by your presence in the {country} beauty market.

I'm from Cangzhou, China — the world's largest makeup brush manufacturing hub, producing over 70% of global cosmetic brushes.

{FEATURES}

We currently supply brands in multiple markets and are looking for a reliable distribution partner in {country}. Would you be open to a brief call or sample shipment to explore fit?

Best regards,
{FROM_NAME}
{FROM_EMAIL}
WhatsApp: [your number]
Cangzhou, Hebei, China"""

    subject = f"Cangzhou Makeup Brushes — OEM/ODM for {company}"

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
