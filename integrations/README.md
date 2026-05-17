# 🔌 futurex.capital 主站集成「AI 投资日记」

让 `futurex.capital` 自动显示倩小虾日记的最新条目——**粘贴一次，永久自动同步**。每天 7AM 日记自动更新后，主站这个板块会自动跟着刷新，无需任何人工维护。

---

## 给维护 futurex.capital 的开发者

### 方式 A · 嵌入组件（推荐，自动同步）

把 `futurex-diary-widget.html` 里那一整段代码（`<div id="clawq-diary-feed">` 到 `</script>`）粘贴到主站想显示日记的位置：
- `/diary` 页面正文，或
- 首页「最新洞察 / Insights」板块

它会客户端拉取日记的 `atom.xml`，渲染最新 5 条（日期 + 标题 + 摘要 + 链接）。

**特点**
- 纯原生 JS，**无依赖、无构建步骤**，任何技术栈都能用（纯 HTML / WordPress / Webflow / Wix 自定义代码块 / React 页面里也能塞）
- CSS 用 `cqd-` 前缀命名空间，**不会和主站样式冲突**
- 想改配色：组件 `<style>` 里改 `--cqd-accent`（主色）/ `--cqd-text` / `--cqd-muted` / `--cqd-line` 四个变量即可
- 想改显示条数：`<div id="clawq-diary-feed" data-max="5">` 的 `data-max` 改成别的数字
- 拉取失败时（比如网络问题）会优雅降级成一条「点此阅读」链接，不会留空白

### ⚠️ 上线后必做：改数据源地址

组件顶部有两行配置：
```js
var FEED_URL = 'https://cynthia-git11.github.io/clawq-diary/atom.xml';
var SITE_URL = 'https://cynthia-git11.github.io/clawq-diary/';
```
- 当前指向 GitHub Pages。**GitHub Pages 在中国大陆访问不稳定**——如果主站有中国访客，等日记迁移到 Cloudflare Pages / `diary.futurex.capital` 之后，把这两行换成新地址，组件就会从国内能稳定访问的源拉取。

### 方式 B · React / Next.js 组件

如果 futurex.capital 是 React / Next.js，告诉张倩，可以再要一份正式的 React 组件版本（用 `useEffect` 拉 feed、SSR 友好）。方式 A 的原生版在 React 里也能用，但 React 版更干净。

### 方式 C · 子域名（最省事，零集成代码）

如果不想动主站代码，最简单：把日记挂成子域名 `diary.futurex.capital`，主站导航的「AI 成长日记 / Diary」链接直接指过去即可。详见仓库根目录 `SETUP-CUSTOM-DOMAIN.md`。

---

## 合规说明

日记内容为**公开的投资思考记录**，已通过 v2.0 合规清理——不含任何基金募集、LP 招揽内容。组件底部固定显示免责声明。把它放在机构主站作为思想领导力内容，合规上没有问题。

---

## 技术细节

- 数据源：`atom.xml`（标准 Atom 1.0 feed，每天自动更新）
- 跨域：GitHub Pages / Cloudflare Pages 均返回 `Access-Control-Allow-Origin: *`，浏览器端 `fetch` 可直接读取
- 性能：单次 `fetch`，feed 体积约几十 KB，对主站加载无影响
- 隐私：纯前端拉取，不引入任何第三方追踪
