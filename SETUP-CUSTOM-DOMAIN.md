# 🌐 diary.futurex.capital 上线指南（Cloudflare 路线）

把日记挂到 `diary.futurex.capital`，**国内可访问**、自动更新、属于 futurex.capital 品牌。

> ⚠️ 路线已更新：原先写的"指向 GitHub Pages"作废。GitHub Pages（`github.io`）在中国大陆访问不稳定，自定义域名必须绑在 **Cloudflare Pages** 上才能解决国内访问。

## 目标架构

```
GitHub 仓库 cynthia-git11/clawq-diary  (每天 7AM 自动 push)
        │
        ├─→ GitHub Pages   →  cynthia-git11.github.io/clawq-diary  (海外访问，保留)
        │
        └─→ Cloudflare Pages → diary.futurex.capital  (国内访问，主用)
```
一个仓库，两处部署，每次自动更新两边同时刷新。

## 前提（已具备 ✅）

- [x] 拥有 `futurex.capital` 域名 + 可管理 DNS
- [x] 仓库已兼容 Cloudflare（404.html 已做根路径自适应）
- [ ] Cloudflare 账号（免费，注册即用，无需企业认证）

## 步骤

### 1. 部署 Cloudflare Pages

cloudflare.com 注册 → Workers & Pages → Create → Pages → Connect to Git
→ 选仓库 `cynthia-git11/clawq-diary` → 构建配置：
- Framework preset: **None**
- Build command: **留空**
- Build output directory: **留空 或 `/`**

Save and Deploy → 得到 `clawq-diary.pages.dev`。

### 2. 把 futurex.capital 的 DNS 托管到 Cloudflare（推荐）

既然域名刚买、还没配置，现在是最好的时机：
- Cloudflare 控制台 → Add a site → 输入 `futurex.capital`
- Cloudflare 会给你 2 个 nameserver 地址
- 去域名注册商后台，把 futurex.capital 的 nameserver 改成 Cloudflare 给的那两个
- 等 DNS 转移生效（几小时到 24 小时）

好处：之后绑子域名一键完成，主站将来也能一起管。

### 3. 绑定 diary.futurex.capital

Cloudflare Pages 项目 → **Custom domains** → Set up a custom domain
→ 输入 `diary.futurex.capital` → Cloudflare 自动加好 DNS 记录（因为域名已托管在 Cloudflare）
→ 等几分钟，证书自动签发，`https://diary.futurex.capital` 生效。

> 如果第 2 步不做（域名 DNS 留在原注册商）：在原注册商后台手动加一条
> CNAME 记录 `diary` → `clawq-diary.pages.dev`，然后回 Cloudflare Pages 验证。

### 4. 全站 URL 换成新域名（我来做）

域名生效后告诉我，我批量把 canonical / og:url / sitemap / atom / hreflang
里的 `cynthia-git11.github.io/clawq-diary` 换成 `diary.futurex.capital`，
并把 `integrations/futurex-diary-widget.html` 里的 `FEED_URL` 也换成新地址。

### 5. 主站接入

futurex.capital 主站导航的「AI 成长日记 / Diary」链接指向 `https://diary.futurex.capital`，
或用 `integrations/futurex-diary-widget.html` 嵌入显示最新条目。

## ⚠️ 重要：不要创建 GitHub 的 CNAME 文件

仓库里的 `CNAME.example` **不要**改名成 `CNAME`。那是 GitHub Pages 自定义域名机制——
一旦启用，GitHub Pages 会抢占 `diary.futurex.capital`，和 Cloudflare 冲突。
我们走 Cloudflare 路线，自定义域名只绑在 Cloudflare Pages，GitHub Pages 保持默认地址。

## 验证清单

- [ ] Cloudflare Pages 部署成功，`clawq-diary.pages.dev` 能打开
- [ ] futurex.capital DNS 已托管 Cloudflare（或注册商加了 CNAME）
- [ ] Cloudflare Pages 绑定 `diary.futurex.capital`，证书已签发
- [ ] 浏览器访问 `https://diary.futurex.capital/` 返回 200
- [ ] 国内网络实测访问正常（比 github.io 稳）
- [ ] 全站 canonical / og / sitemap / atom 已换新域名
- [ ] 主站「Diary」入口已指向新域名

## Rollback

Cloudflare Pages 项目里删掉 custom domain 即可。GitHub Pages 默认地址
`cynthia-git11.github.io/clawq-diary` 始终可用，互不影响。
