# 🌐 自定义域名配置指南

把网站从 `cynthia-git11.github.io/clawq-diary` 升级为 `diary.futurexcapital.ai` 的步骤。

## 配置预览（已就绪）

仓库根目录已经放好 `CNAME.example` 文件，里面是预先填好的 `diary.futurexcapital.ai`。所有 SEO/OG/canonical 在你激活后只需要把网站里所有 `cynthia-git11.github.io/clawq-diary` 替换为新域名（用 sed 批量替换或我帮你做）。

## 5 个步骤

### 1. 在 futurexcapital.ai 域名管理后台添加 DNS 记录

**类型**: CNAME
**名称（前缀）**: `diary`
**指向**: `cynthia-git11.github.io`
**TTL**: 3600（1 小时）

添加完保存。

### 2. 把 CNAME.example 重命名为 CNAME

```bash
cd /Users/cynthiazhang/Library/Mobile\ Documents/com~apple~CloudDocs/内容资产/clawq-diary
mv CNAME.example CNAME
git add CNAME && git commit -m "Add custom domain CNAME" && git push origin main
```

或者就在 GitHub 网页端直接重命名也可以。

### 3. 在 GitHub repo 设置激活

打开 https://github.com/cynthia-git11/clawq-diary/settings/pages

- **Custom domain**: 输入 `diary.futurexcapital.ai`
- **Save**
- 等待 1-2 分钟 DNS 验证
- 勾选 **Enforce HTTPS**（DNS 校验通过后才会出现）

### 4. 等 24 小时 DNS 全球生效

可以用以下命令检查 DNS 是否已生效：

```bash
dig diary.futurexcapital.ai
# 应该返回 cynthia-git11.github.io 的 IP
```

### 5. 把网站里所有旧域名替换为新域名

让我（或下一次 push）批量替换以下文件中的 `cynthia-git11.github.io/clawq-diary` 为 `diary.futurexcapital.ai`：

- `index.html`（canonical / og:url / atom link 等）
- `en.html`
- `press.html`
- `sitemap.xml`
- `atom.xml`
- `robots.txt`

用一行 sed：
```bash
LC_ALL=C find . -type f \( -name "*.html" -o -name "*.xml" -o -name "*.txt" -o -name "*.md" \) -exec sed -i '' 's|cynthia-git11\.github\.io/clawq-diary|diary.futurexcapital.ai|g' {} +
```

（macOS 的 sed 需要 `-i ''`，Linux 是 `-i`）

## 验证清单

- [ ] DNS 已在域名后台添加
- [ ] CNAME 文件已 commit + push
- [ ] GitHub Settings 已填入 custom domain
- [ ] HTTPS Enforce 已勾选
- [ ] dig 测试返回正确
- [ ] 浏览器访问 `https://diary.futurexcapital.ai/` 返回 200
- [ ] 所有 .html / .xml 里的旧域名已批量替换
- [ ] 重新提交 sitemap 到 Google Search Console
- [ ] 旧 GitHub Pages URL `cynthia-git11.github.io/clawq-diary` 自动 301 跳转到新域名（GitHub 默认行为）

## Rollback

如果出问题，把 CNAME 文件删掉，再去 GitHub Settings → Pages 把 Custom domain 留空保存即可恢复到 `cynthia-git11.github.io/clawq-diary`。
