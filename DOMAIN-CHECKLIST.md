# ✅ diary.futurex.capital 上线操作清单

> 域名已定：**diary.futurex.capital**（2026-08-31 作者确认）
> 路线：Cloudflare Pages（**不是** GitHub Pages 绑域名——github.io 在大陆本就不通，绑上去等于没解决）

## 你要做的（约 15 分钟 + DNS 等待）

### ① 注册 Cloudflare 账号
cloudflare.com → Sign up。免费版够用，不需要企业认证。

### ② 创建 Pages 项目
Workers & Pages → Create → Pages → **Connect to Git** → 授权 GitHub → 选仓库 `cynthia-git11/clawq-diary`

构建配置（三项都要按这个填，填错会构建失败）：
- Framework preset：**None**
- Build command：**留空**
- Build output directory：**留空**（或填 `/`）

Save and Deploy → 拿到 `clawq-diary.pages.dev`，**先打开确认能访问**。

### ③ 把 futurex.capital 的 DNS 托管到 Cloudflare（推荐）
Cloudflare 控制台 → Add a site → 输入 `futurex.capital` → Cloudflare 给你 2 个 nameserver
→ 去域名注册商后台把 nameserver 改成这两个 → 等生效（几小时到 24 小时）

> **不想动主域名 DNS 的话**：跳过这步，直接在现有注册商加一条
> CNAME：`diary` → `clawq-diary.pages.dev`，然后回 ④ 验证。

### ④ 绑定子域名
Pages 项目 → Custom domains → Set up a custom domain → 输入 `diary.futurex.capital`
→ 证书自动签发，几分钟后 `https://diary.futurex.capital` 生效。

### ⑤ 告诉我「域名通了」
剩下的我做，见下。

---

## 我要做的（你说一声就执行）

1. 跑 `python3 scripts/switch-domain.py diary.futurex.capital`
   —— 一次性把 **457 处**规范链接（canonical / og:url / JSON-LD / sitemap / atom / llms / robots / widget FEED_URL）切到新域名
2. 跑 GEO 双门复核，确认 JSON-LD 与 XML 未破
3. 提交推送，验证线上生效
4. 把统计 Worker 也绑自定义域（如 `a.futurex.capital`）
   —— **这一步同样关键**：tracker 现在打点到 `*.workers.dev`，该域在大陆被 DNS 污染 + SNI 阻断，
   所以大陆读者即使打开日记也**不会被统计到**。绑自有域名后才能真正看到大陆流量。

回滚：`python3 scripts/switch-domain.py --revert`，一条命令切回 github.io。

---

## 绝对不要做的一件事

**不要**把 `CNAME.example` 改名成 `CNAME`。那是 GitHub Pages 的自定义域名机制，
一旦启用 GitHub 会抢占 `diary.futurex.capital`，与 Cloudflare 冲突。
（`scripts/switch-domain.py` 已按此约束修改，不会写 CNAME 文件。）

## 验证清单

- [ ] `clawq-diary.pages.dev` 能打开
- [ ] `https://diary.futurex.capital/` 返回 200
- [ ] **大陆网络实测能打开**（这是做这件事的全部理由）
- [ ] 全站 canonical / og / sitemap / atom 已换新域名（我执行）
- [ ] 统计 Worker 已绑自有域、大陆打点能上报（我执行）
- [ ] futurex.capital 主站导航加「日记」入口指向新域名
