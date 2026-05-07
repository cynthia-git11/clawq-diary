# 🚀 ClawQ Chronicles · Launch Checklist

**Date drafted:** 2026-05-04 (Day 58)
**Status:** Site is LIVE at https://cynthia-git11.github.io/clawq-diary/ · 中英双语 · LP 区机构级 · 自动推广基建 v1 已上线

This file lists the **manual steps you (Cynthia) need to complete** outside this codebase. AI 自动化无法替你执行的事项都在这里。

---

## ✅ 已完成（在网站上）

- [x] 中文版 + 英文版双语网站
- [x] 机构级 LP 区（媒体认证条 / 8 项核心指标 / 12 张被投 LOGO / GP 双卡 / Fund Structure 8 维 / 4 步投资流程 / LP 引用 / NDA-gated CTA）
- [x] sitemap.xml · robots.txt · atom.xml RSS feed
- [x] Schema.org JSON-LD（Person + Blog + Organization）
- [x] Open Graph + Twitter Card 全套
- [x] hreflang CN/EN 互链
- [x] 社交分享按钮（X / 微博 / LinkedIn / 复制链接 / 微信扫码 / RSS）
- [x] 邮件订阅表单（FormSubmit.co · 零账号注册即用）
- [x] Plausible 分析 script 已嵌入（待激活）
- [x] 每天 7AM 自动更新（GitHub Actions cron 任务运行中）

---

## 🔴 高优先级 · 你这周需要做

### 1. 配置邮箱 `lp@futurex.capital`（30 分钟）

**为什么重要**：网站上所有 LP CTA 都指向这个邮箱，目前可能还没有设置。

**步骤**：
1. 登录 futurex.capital 域名的邮箱管理后台（多半是阿里云邮箱 / 腾讯企业邮）
2. 创建别名 `lp@futurex.capital`，转发到你和核心 IR 同事的邮箱
3. 测试一封邮件能正常收到 + 能正常回信

### 2. 激活邮件订阅（FormSubmit）（10 分钟）

**为什么**：第一个订阅者发表单后，FormSubmit 会向 `lp@futurex.capital` 发送一封确认邮件，**点击确认链接**才会激活，否则后续订阅都不会到达。

**步骤**：
1. 用任意邮箱测试订阅一次（在 https://cynthia-git11.github.io/clawq-diary/ 拉到底部，输入邮箱）
2. 检查 lp@futurex.capital 收件箱，找到 FormSubmit 的确认邮件
3. 点击 "Confirm" 激活
4. 完成后所有订阅都会自动落到这个邮箱

### 3. 注册 Plausible 分析账号（10 分钟，免费 30 天）

**为什么**：网站已嵌入 script，但需要在 Plausible 平台注册才能看到数据。

**步骤**：
1. 访问 https://plausible.io/register
2. 添加站点：`cynthia-git11.github.io`（或者升级到自定义域名后改成新域名）
3. 完成后 24 小时内会有第一批访问数据
4. **如果你想替换为完全免费且可自托管的方案**：可以用 Umami（自己部署）或者用 Cloudflare Web Analytics（免费，零配置）

**Cloudflare Web Analytics 替代方案**（如果 Plausible 30 天试用过期不想付费）：
- 注册 cloudflare.com（免费账号）
- Analytics → Web Analytics → Add a site
- 复制 beacon snippet 替换 index.html / en.html 中的 Plausible script

### 4. 提交到 Google Search Console（15 分钟）

**为什么**：让 Google 第一时间发现并收录新条目。每天的新日记当天就会被搜索引擎收录。

**步骤**：
1. 访问 https://search.google.com/search-console
2. 添加属性：`https://cynthia-git11.github.io/clawq-diary/`
3. 验证方式选 "HTML 标签"，复制 `<meta name="google-site-verification" content="..." />`
4. 把这行 meta 标签贴给我，我加到 `index.html` 和 `en.html` 的 `<head>`
5. 验证完成后，提交 sitemap：`https://cynthia-git11.github.io/clawq-diary/sitemap.xml`

### 5. 提交到 Bing Webmaster Tools（10 分钟）

**为什么**：Bing 是 ChatGPT / Copilot 的搜索引擎来源。海外 LP 用 Bing 也常见。

**步骤**：
1. 访问 https://www.bing.com/webmasters
2. 用同一个 Google 账号登录（可以从 Google Search Console 一键导入）
3. 自动同步已提交的 sitemap

### 6. 提交到百度站长平台（20 分钟）

**为什么**：国内 LP 通过百度搜索"张倩"或"天际资本"时，让这个网站出现在前列。

**步骤**：
1. 访问 https://ziyuan.baidu.com
2. 用百度账号登录 → 添加网站
3. 验证方式：HTML 标签（同 Google）→ 把 `<meta>` 贴给我加到 head
4. 提交 sitemap.xml
5. **额外**：开启"自动推送"——这是百度的实时推送，每天新日记发布后立刻通知百度

---

## 🟡 中优先级 · 这两周做完

### 7. 创建 LP 数据室（Notion/腾讯文档/Google Drive）

**目的**：当合格投资者通过私下渠道询问后，你需要一个内部材料库可以准备资料。

**建议结构**：
```
LP Data Room/
├── 1. Fund Deck (PDF)
├── 2. Track Record/
│   ├── Realized Returns Detail.xlsx
│   ├── Bytedance 5 Rounds Case.pdf
│   └── Portfolio Performance Q1 2026.pdf
├── 3. Current Portfolio/
│   ├── Full 40+ Companies List.xlsx
│   ├── LinkCrux AI Memo (latest).pdf
│   └── ...
├── 4. Team & Org/
│   └── Cynthia Bio + Team Bios.pdf
├── 5. Legal/
│   ├── NDA Template.pdf
│   └── LPA Draft.pdf
└── 6. Diary Archive (PDF export, monthly)
```

**工具推荐**：
- **Notion** (中英文都好用，权限分级)
- **DocSend** (海外 LP 标配，能追踪谁看了哪一页)
- **Carta Investor Portal** (如果用 Carta 管基金)

### 8. 注册自定义域名（可选，但显著提升机构级专业感）

当前域名：`cynthia-git11.github.io/clawq-diary` (GitHub 子域)
建议域名：`diary.futurex.capital` 或 `chronicles.futurex.capital`

**步骤**：
1. 在 futurex.capital 的 DNS 后台添加 CNAME 记录：
   - `diary` → `cynthia-git11.github.io`
2. 在 GitHub repo Settings → Pages → Custom domain 填入 `diary.futurex.capital`
3. 创建 `CNAME` 文件（我可以帮你做这一步）
4. 等 24 小时 DNS 生效

### 9. 跨平台分发自动化（可选，进阶）

目前每天 7AM 网站自动更新一条新 entry。下一步可以加：

- **公众号自动同步**：用 wxauto / itchat-pro 把每日新 entry 自动发到草稿箱
- **微博自动发布**：用微博 API 推 140 字摘要 + 链接
- **小红书图文卡**：每天自动生成"金句海报"图，挂到推广素材库
- **LinkedIn 自动发**：用 LinkedIn API 发英文版摘要

这些需要每个平台的 API key 和登录 cookie，是中等工程量。我可以帮你写脚本但你需要自己配置授权。

---

## 🟢 低优先级 · 一个月内做

### 10. 内容回流 → 公众号

把每周的日记合集整理成一篇公众号长文，反向把流量从公众号导回网站。模式参考傅盛的 "周报" 格式。

### 11. 海外 PR

英文版网站建好后，可以投递这些渠道：
- **Information's Race to AGI** newsletter（如果能进可信赖关系）
- **TechCrunch Asia / KrAsia**（之前 36氪有合作，可以延续）
- **Substack 推荐网络**（找 LP 视角的 newsletter 互推）

### 12. 季度 LP 简报 PDF 自动生成

把每季度的所有 entry 自动 PDF 化，发给已经签了 NDA 的 LP。这就是从"日记"升级成"季度财报"的路径。

---

## 📊 衡量是否 Launch 成功的指标（第 30 天复盘）

| 指标 | 目标值 |
|---|---|
| 月独立访客 | > 5,000（中英文合计） |
| 邮件订阅数 | > 200 |
| 内容订阅留存率 | > 50% |
| 被引用 / 转载次数 | > 50 次 |
| 微博 / X 转发 | > 100 次 |
| 带来 1+ 内容合作（媒体/研究）| ≥ 1 |

**关键判断**：如果 30 天后内容互动量低于预期，回看内容质量和分发基建，而不是把网站当募资工具。本网站不构成对任何基金产品的推介或募集要约。

---

## ⚙️ 维护清单（每周做一次）

- [ ] 每周一早上 8:30 看 Plausible 数据（10 分钟）
- [ ] 每周三复盘"错过清单"并写进当周日记（参考 ENTRY 38 制度）
- [ ] 每周五检查 lp@futurex.capital 邮箱，回复读者来信和媒体询问
- [ ] 每周日检查 sitemap 是否被 Google 重新爬取（在 Search Console 看）

---

## 📞 出问题找谁

- 网站本身问题 → 提交 issue 到 https://github.com/cynthia-git11/clawq-diary/issues
- 内容方向问题 → Cynthia 自己决策
- 自动化任务异常 → 查 GitHub Actions logs（每天 7AM 任务）

---

**Last updated by:** Day 58 自动化系统 + 张倩
**Next review:** Day 88（一个月后）
