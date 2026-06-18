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
| SMTP 配置 | ⚠️ | 待用户开启阿里云 SMTP + 客户端密码 |
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

1. **邮件发送**：需在阿里云邮箱后台 → 开启 SMTP → 生成客户端专用密码
2. **LinkedIn 自动化**：需安装完整 Chromium + Playwright（apt install chromium-browser 二进制缺失）
