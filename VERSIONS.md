# 📦 Version Tags · 版本档案

每一次重大里程碑都打一个 git tag。任何时候都可以一行命令回滚到那个状态。

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
