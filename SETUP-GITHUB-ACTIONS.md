# GitHub Actions Cron · 一次性配置指南

把"每日 7AM 日记自动更新"从本地定时任务搬到 GitHub Actions 后，**这条流程不再依赖你的电脑或 App 是否开机**——GitHub 自己的服务器每天 7AM 北京时间自动跑一次。

需要你做的 **只有一步**：把 Anthropic API key 存到这个仓库的 GitHub Secret 里。

---

## Step 1 · 拿到 Anthropic API key（如果还没有）

1. 去 https://console.anthropic.com/settings/keys
2. 点 **Create Key**（建议命名 `clawq-diary-cron`，方便以后单独撤销）
3. 复制 `sk-ant-…` 这串字符串。**只显示一次，关掉就拿不回来了**——存好。

## Step 2 · 把 key 存进 GitHub Secret

1. 去 https://github.com/cynthia-git11/clawq-diary/settings/secrets/actions
2. 点 **New repository secret**
3. **Name**: `ANTHROPIC_API_KEY`（必须一字不差）
4. **Secret**: 粘贴刚才那串 `sk-ant-…`
5. 点 **Add secret**

完成。GitHub Secrets 是单向加密的——即使是仓库 admin 也看不到原值，只有 Actions runner 在跑的时候能解出来用。

## Step 3 · 验证 workflow 跑得通

不用等到明天 7AM。直接手动触发一次试跑：

1. 去 https://github.com/cynthia-git11/clawq-diary/actions/workflows/daily-diary.yml
2. 点右上角 **Run workflow** → **Run workflow**
3. 大约 3-10 分钟后看结果。绿色 ✓ = 成功；红色 × = 看 log

如果跑成功，仓库会自动出现一个新 commit，标题类似：
> `Daily auto-update · Day 79 · ENTRY 61 · [今天写的主题]`

GitHub Pages 60 秒后自动重新构建上线。

---

## 之后会怎么跑

| 时间 | 谁触发 | 做什么 |
|------|--------|--------|
| 每天 23:00 UTC (= 北京 7:00 次日) | GitHub Actions cron | 自动跑一遍 daily-prompt.md，产出新一篇日记 + 全栈同步 + 自动 commit + push |
| 任何时候 | 你手动点 "Run workflow" | 同上（用来补昨天/前天遗漏，或加急更新） |

## 它具体在干什么

`.github/workflows/daily-diary.yml` 大致逻辑：
1. checkout 仓库
2. 配 git 作者为 `ClawQ Auto-Update Bot`
3. 算出今天的 Beijing 日期 + Day 数
4. 调用 `anthropics/claude-code-action`，把 `.github/scripts/daily-prompt.md` 喂给 Claude
5. Claude 读取 prompt → WebSearch 找最新动态 → 写新条目 → 改 index/en/atom/sitemap/archive → 自检合规 → `git push`
6. 兜底：如果 Claude 没成功 push（罕见），workflow 最后一步会强制 commit + push 兜底

## 成本估算

每次跑大约消耗：
- Input tokens: 80-200K（读 index.html 是大头）
- Output tokens: 5-20K

按 Claude Sonnet 当前定价 ($3/$15 per 1M)：
- 单次 ≈ $0.30-0.80
- 每月 ≈ **$10-25 美元**

如果想压成本，可以：
- 把 workflow 里的 `--max-turns 40` 调到 25（够用）
- 用 Haiku 跑（在 claude_args 里加 `--model claude-haiku-4-5`），单次成本可以压到 $0.05-0.15

## 怎么停 / 怎么调

| 想做 | 怎么做 |
|------|--------|
| 临时暂停几天 | 去 Actions 页面禁用 daily-diary workflow，回来时启用 |
| 永久停掉 | 把 `.github/workflows/daily-diary.yml` 删了 commit 一下 |
| 改时间 | 编辑 yml 里 `cron: '0 23 * * *'`（UTC 时区） |
| 改 prompt | 直接改 `.github/scripts/daily-prompt.md`，下次跑时生效 |
| 撤销 API key | 去 console.anthropic.com 把那个 key 删了，workflow 之后会失败但不会泄漏 |

## 排错速查

| 症状 | 原因 | 解决 |
|------|------|------|
| Actions log 报 `secret ANTHROPIC_API_KEY not found` | Secret 没配 | 回到 Step 2 |
| 跑完没 commit | Claude 觉得"今天没素材"或者没找到 timeline 锚点 | 看 Actions log 里 Claude 的输出 |
| Push 被拒 | 分支保护规则 | 仓库 Settings → Branches → 允许 GitHub Actions push |
| 内容偏题 | 模型走神 | 编辑 daily-prompt.md 加更具体约束 |
