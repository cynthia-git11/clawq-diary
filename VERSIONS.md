# 📦 Version Tags · 版本档案

每一次重大里程碑都打一个 git tag。任何时候都可以一行命令回滚到那个状态。

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
