# 外贸自动化客户开发系统 — 架构文档

## 系统能力总览

```
┌─────────────────────────────────────────┐
│         外贸自动化客户开发系统 V1        │
├─────────────┬──────────────┬────────────┤
│ 📊 CRM 跟踪  │ 📬 邮件触达   │ 🔍 自动搜索 │
│ SQLite DB   │ himalaya CLI │ cron每周  │
│ Python CLI  │ SMTP待配     │ web_search │
├─────────────┴──────────────┴────────────┤
│          ⏰ 自动化调度 (Cron)            │
│  每日提醒 + 每周搜索 + 手动补充         │
└─────────────────────────────────────────┘
```

## 已安装组件

| 组件 | 状态 | 位置 |
|------|:---:|------|
| CRM 数据库 | ✅ | /root/code/trade-knowledge-flywheel/crm.db |
| CRM CLI | ✅ | /root/code/trade-knowledge-flywheel/scripts/crm.py |
| himalaya CLI | ✅ | himalaya v1.2.0 |
| SMTP 配置 | ✅ | Gmail: ud.xiaoshan@gmail.com (587/TLS) |
| Chromium CDP | ❌ | 二进制缺失，Linux headless 不可用 |
| 跟进提醒 Cron | ✅ | 每日北京时间 9:00 (job: 0bf6f85886aa) |
| 自动搜索 Cron | ✅ | 每周日北京时间 9:00 (job: 3153cc71974c) |

## CRM 命令速查

```bash
cd /root/code/trade-knowledge-flywheel

# 添加客户
python3 scripts/crm.py add "公司名" "国家" "邮箱" "电话" "备注"

# 查看所有客户
python3 scripts/crm.py list

# 查看需要跟进的
python3 scripts/crm.py next

# 更新状态
python3 scripts/crm.py update <ID> --status contacted

# 记录沟通
python3 scripts/crm.py log <ID> "WhatsApp已发开发信"

# 统计
python3 scripts/crm.py stats
```

## 待修复

1. **LinkedIn 自动化**：需安装完整 Chromium + Playwright（apt install chromium-browser 二进制缺失）

## 自动发信命令

```bash
cd /root/code/trade-knowledge-flywheel

# 预览开发信（不发送）
python3 scripts/send_email.py --dry 1

# 给客户 #1 发送开发信
python3 scripts/send_email.py 1

# 给所有待开发客户群发
python3 scripts/send_email.py --all-new

# 跟进 7 天前联系过的客户
python3 scripts/send_email.py --followup 7
```
