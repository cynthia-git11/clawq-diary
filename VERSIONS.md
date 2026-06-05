# 📦 Version Tags · 版本档案

每一次重大里程碑都打一个 git tag。任何时候都可以一行命令回滚到那个状态。

---

## 🏷️ v3.5-search-stats

**日期**：2026-06-02
**Commit**：[`98c06ad`](https://github.com/cynthia-git11/clawq-diary/commit/98c06ad)
**回滚**：`git checkout v3.5-search-stats -- .`

**新增**：站内 fulltext 搜索（Cmd/Ctrl+K）+ 侧栏「日记构成」stats widget（按 tag 自动分类）+ 删除零引用资产 `zhangqian-profile.png`（-1.98MB）。Day 87 / ENTRY 61 顺手带上。

---

## 🏷️ v3.3-pwa-toc

**日期**：2026-06-01
**Commit**：[`55e1fcc`](https://github.com/cynthia-git11/clawq-diary/commit/55e1fcc)
**回滚**：`git checkout v3.3-pwa-toc -- .`

**新增**：Service Worker（HTML network-first + 静态 cache-first，离线 PWA 能力）+ 侧栏「📚 按月浏览」TOC 卡（JS 自动按月分组）。v3.4 接续：阅读时长 chip + PWA 安装 toast（≥3 次访问触发）+ mobile 微调。

---

## 🏷️ v3.0-warm-lobster

**日期**：2026-05-31
**Commit**：[`6a7c39c`](https://github.com/cynthia-git11/clawq-diary/commit/6a7c39c)
**回滚**：`git checkout v3.0-warm-lobster -- .`

**状态描述**：FutureX 天际蓝品牌改造**之前**的最后一个暖暗色稳定版（"龙虾橘 + 黑底"原版）。如果觉得新蓝色系不喜欢，这是 1 行回滚的安全网。

**改造路线**（v3.0 → v3.5）：
- v3.1 · 天际蓝色系（deck-faithful 浅色版）
- v3.2 · SEO + a11y + 性能 + GitHub Actions 自动更新 badge
- v3.3 · PWA 离线 + 月度归档 TOC
- v3.4 · 阅读时长 + 安装 toast + mobile 微调
- v3.5 · 全文搜索 + Stats widget + 资产瘦身

---

## 🏷️ v2.2-day-66

**日期**：2026-05-12
**Commit**：[`5e64d65`](https://github.com/cynthia-git11/clawq-diary/commit/5e64d65)
**GitHub**：[查看 tag](https://github.com/cynthia-git11/clawq-diary/releases/tag/v2.2-day-66)

**状态描述**：v2.1 之后第 1 条日更，**ENTRY 44 · Day 66** —— 字节 2026 AI capex 拐点。

**新增**：
- ENTRY 44 · 2026-05-12 · **"字节 2026 年 AI capex 从 1600 亿上调到 2000 亿——这个 +25% 背后藏着三层信号"**
  - 数据：¥2000B（+25%）/ 火山引擎 13% IDC AI cloud 份额 / 豆包 1.2 万亿日均 Token
  - 三层判断：算力通胀 / Token 工厂 / 端到端 Agent 新路径
  - 修正了 Day 65 "智力成本 128 倍跌" 的判断（用户层跌 ≠ 基建层跌）

**同步**：stats Day 65→66 / 43→44 篇 / 网页 title + og + twitter / JSON-LD top-5 / 成长地图 +1 / atom.xml +1 + 5/12 / sitemap lastmod 5/12

**合规验证**：剩余 Fund VIII / Tiered LP / 申请数据室 等关键词全部仍只在 ENTRY 41 合规重置叙事中——0 处新增募资语言。

**回滚**：`git checkout v2.2-day-66`

---

## 🏷️ v2.1-day-65

**日期**：2026-05-11
**Commit**：[`e6fd864`](https://github.com/cynthia-git11/clawq-diary/commit/e6fd864)
**GitHub**：[查看 tag](https://github.com/cynthia-git11/clawq-diary/releases/tag/v2.1-day-65)

**状态描述**：在 v2.0 合规版基础上**追加 3 条新日记**（覆盖 5/7–5/11 这一周），仍保持完整 compliance-clean。

**新增内容**：
- ENTRY 43 · Day 65 (2026-05-11) · "智力成本暴跌 128 倍 · 愿意承担后果是最后的稀缺"
- ENTRY 42 · Day 63 (2026-05-09) · "免费时代结束 + 分发战场转移 (字节豆包付费 / OpenClaw 5.4)"
- ENTRY 41 · Day 61 (2026-05-07) · "v2.0 合规重置叙事：为什么必须把招揽痕迹撤下来"

**同步更新**：
- 顶部 stats / last-updated / `<title>` 全部从 Day 58 → Day 65, 40 篇 → 43 篇
- BlogPosting JSON-LD ItemList 刷新（最新 5 条）
- 成长地图 +3 条（5/7 ⭐ / 5/9 / 5/11 ⭐）
- atom.xml +3 entries · feed `<updated>` → 2026-05-11
- sitemap.xml 全部 `lastmod` → 2026-05-11

**合规验证**：
- 所有剩余 "Fund VIII / 募资中 / Tiered LP / 申请数据室" 关键词均出现在 ENTRY 41 的"描述被移除的内容"叙事中——不是招揽
- 每条 atom summary 都带"不构成对任何基金产品的推介或募集要约"声明

**如何回滚**：
```bash
git checkout v2.1-day-65
```

---

## 🏷️ v2.0-compliance-clean

**日期**：2026-05-07
**目标**：根据合规要求（VC 基金不能公开推广），把网站从"机构 LP DD 附件"重构为**纯思考性公开日记 + 历史业绩信息陈述**。

**关键合规变更**：

❌ **下线（全部移除）**：
- "Fund VIII 募资中 / Raising"、"$200–300M target"、"First Close Q3 2026"
- 所有 LP 决策块：Investment Thesis · Top 10 LP Q&A · GP Alignment · Risk Factors · Key Person · LP Voices · Quarterly Sample · Why FutureX vs Alternatives
- 三级 LP CTA（$1-10M / $10-25M / $25M+）
- LP Portal 邀请码门户（master 888888 + 机构码）—— 整套登录、模态、JS 全部删
- "申请数据室 NDA"、"Apply for Data Room" CTAs
- "签 NDA 后开放" 类暗示性条款
- Family of Sites 中的 "Fund VIII 募资中" 卡片
- ENTRY 28 的 "天际新一期基金正在面向合适的 LP 开放" 段落
- ENTRY 40 的 "把日记 Launch 给机构 LP 看" 框架
- atom.xml ENTRY 40 summary 中的 "募资载体" 描述
- LAUNCH-CHECKLIST.md 中的 "数据室申请数 / NDA 数 / LP 投资意向" KPI

✅ **保留（合规历史事实）**：
- 14 家 IPO 退出明细（已退出企业的公开事实）
- $1B+ AUM、$550M+ 现金回报（截至当前的历史业绩）
- 字节跳动 5 轮连续投资（2017–）
- 141 家累计被投、60+ AI Native（公开数字）
- 5 城办公分布
- 张倩 bio + 学历 + 履历
- 媒体采访引用 + Press Strip
- 全部日记内容（思考性，非募资材料）

➕ **新增**：
- LP 区改名为"firm"（id="firm"）
- 顶部 H1 改为"20 年投资人，每一天的判断，都写给自己看"
- Hero 副文：明确"这本日记不是产品、不是路演材料、不是基金推介"
- 底部"了解天际资本"区域加 ⚖️ 合规声明：
  > 天际资本为持牌投资机构。基金产品仅向符合资质的合格投资者通过私下渠道提供，本网站不进行任何形式的公开募集或宣传。投资有风险，过往业绩不代表未来表现。
- press.html 和 press-en.html 同样加合规声明
- atom.xml 摘要也加"本日记不构成对任何基金产品的推介或募集要约"

**回滚**：
```bash
git checkout v2.0-compliance-clean
```

注意：这是一次"减法"版本——把 v1.0 / v1.1 里所有 LP 募资材料移除。如果合规框架未来允许部分内容回归（例如某地区允许的合格投资者私募宣传），可以从 v1.1 取出局部内容。

---

## 🏷️ v1.1-lp-decision-portal

**日期**：2026-05-07
**Commit**：[`f02ddac`](https://github.com/cynthia-git11/clawq-diary/commit/f02ddac)
**GitHub**：[查看 tag](https://github.com/cynthia-git11/clawq-diary/releases/tag/v1.1-lp-decision-portal)

**状态描述**：在 v1.0 基础上**深度补强 LP 决策维度**，并加入**邀请码门户**。

**v1.1 新增的 5 大块（CN + EN 等价）**：

1. **Investment Thesis · 投资论文**
   - Lane 1 端到端垂直（给结果不卖工具）
   - Lane 2 硬件 × 龙虾（物理世界供应链护城河）
   - Lane 3 企业 AI 安全合规（B 端入场券）
   - Why Now · 2026 Q3–Q4 窗口论证

2. **GP Alignment + Risk Factors + Key Person**
   - GP commit ≥ 2% pari-passu · European waterfall · 8% hurdle
   - Claw-back · carry 分配上限 · no-cross-fund-fee
   - 5 个已识别风险 + 各自对冲
   - 关键人条款 · 第二梯队 4 名 Partner · 90 天投资期暂停触发

3. **Selected LP Voices · 现存 LP 匿名推荐语**
   - 4 段引语：CVC Partner / 主权基金 ODD Lead / 家办 UHNW / Tier-1 FoF
   - 每段都标注 Fund 编号和角色

4. **Quarterly LP Report Sample**
   - 11 节季报 TOC（GP Letter → 现金流 → MTM → 新投 → 退出 → 健康度 → Co-invest → 风险 → 市场观察 → 财报 → 附件）
   - 全年沟通节奏：每天 / 每月 / 每季 / 半年 / 每年 / 事件触发

5. **🔒 LP Portal · 邀请码门户**
   - Nav 按钮 + 模态框（中英双语）
   - **万能邀请码：`888888`、`FUTUREX-LP`**
   - 可扩展：每个机构独立 6 位 / 标签 / 过期时间
   - 解锁后揭示 4 个 LP-only 直链：Data Room / Reference Call / 最新季报 / Cynthia 优先排期
   - localStorage 持久化 · Plausible 解锁事件追踪
   - 这是软门 — 真正数据室仍 NDA 签后开

**如何回滚到这个版本**：
```bash
cd "/Users/cynthiazhang/Library/Mobile Documents/com~apple~CloudDocs/内容资产/clawq-diary"
git checkout v1.1-lp-decision-portal
# or to a new editable branch:
git checkout -b restore/v1.1 v1.1-lp-decision-portal
```

**如何添加新机构邀请码**（每个 LP 独立码）：
打开 `index.html` 和 `en.html`，找到 `const INVITE_CODES = {`，在里面添加：
```js
'CICC-2026':    { tier: 'tier-ii',  label: 'CICC Capital',                expires: '2026-12-31' },
'TEMASEK-VIII': { tier: 'tier-iii', label: 'Temasek Holdings',            expires: '2026-09-30' },
'KIA-AI-26':    { tier: 'tier-iii', label: 'Kuwait Investment Authority', expires: '2026-09-30' },
```
两个文件都要加，保持中英一致。Plausible 后台会单独显示哪个 code 解锁了多少次——你能看到哪家 LP 在认真读。

---

## 🏷️ v1.0-institutional-lp-launch

**日期**：2026-05-07 · Day 60+
**Commit**：[`8e5135f`](https://github.com/cynthia-git11/clawq-diary/commit/8e5135f)
**GitHub**：[查看 tag](https://github.com/cynthia-git11/clawq-diary/releases/tag/v1.0-institutional-lp-launch)

**状态描述**：网站从"思想领袖型日记"完整升级为**机构 LP 决策 DD 附件**。

**包含的全部能力**：
- 🌐 中英双语（index.html / en.html · 内容等价）
- 📊 同步 futurex.capital 真实数据：$1B+ AUM · $550M+ 已返还 · 141 家被投 · 14 家 IPO · 6 旗舰 · 5 城办公 · Fund VIII 募资 $200–300M
- 🎯 Hero 重写："20 年 6 只基金的每一笔判断，每天写给你看"
- 📋 LP Decision Brief 4 大块：
  - 14 家 IPO Track Record 网格
  - Top 10 LP 尽调问题直答（Q1–Q10）
  - Why FutureX vs 同期 AI GP 对比矩阵（6×3）
  - 三级 LP 入场通道（$1–10M / $10–25M / $25M+）
- 📰 Press Kit（press.html + press-en.html）
- 🦞 404.html 龙虾主题错误页
- 🔗 Family of Sites 页脚（8 张卡 × 2 语言）
- 📱 PWA manifest（可装到桌面）
- 🖨️ 打印样式（LP 直接导出 PDF 包）
- 🔖 40+ 条日记 · 每条独立 permalink（#entry-NN）
- ⏰ GitHub Actions cron 每天 7AM 自动发布
- ✉️ FormSubmit 邮件订阅 + Plausible 分析 + 社交分享栏
- 🤖 BlogPosting JSON-LD + Schema.org · CN/EN hreflang

**如何回滚到这个版本**：
```bash
cd "/Users/cynthiazhang/Library/Mobile Documents/com~apple~CloudDocs/内容资产/clawq-diary"

# 方法 A：直接 checkout（detached HEAD，仅查看）
git checkout v1.0-institutional-lp-launch

# 方法 B：恢复到新分支（可继续编辑）
git checkout -b restore/v1.0 v1.0-institutional-lp-launch

# 方法 C：把 main 强制重置回这个 tag（destructive · 需要 force push）
git checkout main
git reset --hard v1.0-institutional-lp-launch
git push origin main --force-with-lease
```

---

## 📌 如何打新版本（以后参考）

```bash
cd /path/to/clawq-diary
git tag -a vX.Y-meaningful-name -m "$(cat <<'EOF'
vX.Y · 一句话说明这个版本是什么

详细说明：
- 改了什么
- 加了什么
- 修了什么 bug

如何回滚：
  git checkout vX.Y-meaningful-name
EOF
)"
git push origin vX.Y-meaningful-name
```

把这个文件 `VERSIONS.md` 也更新一条新条目。

---

## 命名规范

- `v{major}.{minor}-{slug}` — 重大里程碑 · 例如 `v1.0-institutional-lp-launch`
- `daily-{YYYY-MM-DD}` — 每日自动备份（如果将来需要）
- `pre-{event}` — 重大事件前的快照 · 例如 `pre-fund-viii-first-close`
