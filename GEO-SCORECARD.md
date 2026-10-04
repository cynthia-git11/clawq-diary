# GEO 记分卡

这份文件只记能复测的读数。每次复测在下面追加一节，不改旧节。

## 2026-09-29 · 第一轮：给每个判断一个能被引用的 URL

### 基线（2026-09-28 06:16 CST 探针，改动之前）

| 通道 | 读数 | 可信度 |
|---|---|---|
| Google `site:cynthia-git11.github.io/clawq-diary` | 收录 1 页：ja.html，且是约 2026-06-13 的旧快照 | 浏览器直查，可信 |
| Google 精确品牌词「倩小虾日记」 | 0 结果 | 可信 |
| WebSearch 后端限域查询 | 0 页 | 可信 |
| Common Crawl 最近三轮 | 0 抓取 | 可信 |
| Feedly 订阅 | 0 | 可信 |
| llms.txt 三个目录站 | 0 提及 | 可信 |
| Wayback | index 最后抓取 2026-07-16；entries/ 从未存档 | 可信 |
| Bing、DuckDuckGo | 不可判定：验证码与诱饵结果 | 只能登 Bing Webmaster Tools 看 |
| 12 个投资人热点问题的前 10 结果 | 本站命中 0 次；每题本站都有对应日记 | 可信 |
| 对照组 futurex.capital | 两个引擎均正常收录 | 可信 |
| 自建统计（Worker + D1） | 60 天 83 PV、42 UV；30 天 52 PV、18 UV | 真实数据 |

结论：内容有，收录没有。Google Search Console 从未验证，是零收录的直接原因。

### 本轮上线

| 项 | 数量 | 说明 |
|---|---|---|
| 单篇页面 `entries/<N>.html` | 141 | h1、`<time>`、真实 dateModified、主题 keywords 与 about、尾注按标签结构化、相关主题与问答互链 |
| 主题页 `topics/<slug>.html` | 19 | 每个公司或议题一页：利益披露块、相关问答、挂账判断、全部相关日记 |
| 问答页 `answers/<slug>.html` | 44 中文 + 44 英文 | 一题一页；判断、事实、落点、证伪口（逐字取自尾注）、利益披露、原文链接 |
| 站点地图 | 5 份 | `sitemap-index.xml` 汇总 core、entries、topics、answers |
| Atom | 104 条 | 每条的 alternate 链接指向单篇页面，锚点保留为 related |
| 判断台账 | 全部卡片 | 链接指向单篇页面 |
| 主页 | 导航与页脚 | 新增「全部单篇」「公司与议题」「问答」入口；修掉 7 月以来未更新的 JSON-LD 日期、篇数、Day 数；删重复 FAQ 一条 |
| IndexNow | 见下 | 每小时任务自动推送新改动的 entries、topics、answers |
| 日更流水线 | 已接入 | 写完新篇自动生成单页、主题页、问答页 |

问答页的硬闸：答案里每一个数字都必须能在所引日记里逐字找到，否则拒绝构建。44 题各经一位写手和一位核实员，闸门通过时问题数为 0。

### 只有作者本人能做的事（需要登录）

1. **Google Search Console**：用 URL 前缀属性 `https://cynthia-git11.github.io/clawq-diary/` 验证，把验证码填进 index.html 里现在被注释掉的 `google-site-verification`，然后提交 `sitemap-index.xml`，并对主页、`entries/141.html`、`answers/` 各点一次「请求编入索引」。
2. **Bing Webmaster Tools**：用「从 GSC 导入」，提交同一份站点地图。这是唯一能看清 Bing 是否收录的办法。
3. **futurex.capital/diary**：镜像页停在 6/25 第 66 篇，链接只指主页。改成链接到 `entries/<N>.html`，并在 Person 与 Organization 的 sameAs 里加上日记站。
4. **自定义域名** `diary.futurex.capital`：GitHub Pages 子路径加零外链是抓取弱的原因之一。

### 复测（2026-10-13）

- Google `site:` 收录页数，目标大于 1。
- GSC 覆盖率报告：已编入索引的页数。
- WebSearch 限域命中数。
- 同样 12 个问题的前 10 命中数。
- 自建统计里来自搜索与 AI 引擎的来路数。

### 本轮没做

- 英文单篇页面 `entries/en/<N>.html`。英文现在只有问答页。
- 主页 FAQ 73 问瘦身到 10 条以内。
- 尾注来源加外链。
- 主页旧篇折叠。只在 GSC 显示「已抓取未编入索引」持续两周后再做。

---

## 2026-10-04 · 第二轮：外部入口与英文单篇

起点读数：上次统计 7 天内 6 次浏览，全部没有来路。也就是说还没有任何搜索或 AI 引擎带来访问。瓶颈仍然是外部入口和收录，不在内容。

| 项目 | 状态 | 说明 |
|---|---|---|
| futurex.capital/diary 服务端渲染 | 已上线 | 改为服务端输出最新 60 篇，每篇直链 `entries/<N>.html`（线上抓到 71 个不重复单篇链接），带 ItemList 结构化数据，并删掉「每日更新」的旧说法 |
| GitHub 仓库 README | 已上线 | `scripts/gen-readme.py` 生成，内容包括最新 15 篇、19 个主题、44 道问答和机器可读入口，日更时自动刷新 |
| 仓库元数据 | 已设 | 主页链接指向日记站；中英描述；10 个话题标签 |
| 英文单篇页 `entries/en/<N>.html` | 76 篇上线 | 只用 en.html 上已发布的英文条目，按 Day 和数字重合度配对。配不上的 23 条跳过，不猜。中英互设 hreflang，中文页可见 EN 链接 |
| 站点地图 | 已更新 | sitemap-index 收录 `sitemap-entries-en.xml`，共 77 个地址 |
| IndexNow | 已提交 | 267 个地址，HTTP 200 |

上一轮清单第 3 项（futurex.capital 镜像页）已经完成，只剩 Person 和 Organization 的 sameAs 还没加日记站。第 1、2、4 项仍要作者登录才能做。

10/13 的复测加两项：英文单篇页是否被收录，GitHub 仓库页是否出现在「clawq」「倩小虾日记」的搜索结果里。
