#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一条命令切换全站规范域名（canonical / og:url / sitemap / atom / llms / JSON-LD）。

  python3 scripts/switch-domain.py diary.futurex.capital        # 切到自有域名
  python3 scripts/switch-domain.py --revert                     # 切回 github.io
  python3 scripts/switch-domain.py <domain> --dry               # 只看会改多少处

设计要点：
- staged 写入，任一文件出错则零写入
- github.io 那份仍可访问，只是不再作为规范地址（避免两个域名争抢索引）
- 切换后必须跑 scripts/geo-check.py
"""
import io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH   = "cynthia-git11.github.io/clawq-diary"
FILES = ["index.html", "en.html", "ja.html", "theses.html", "analytics.html",
         "integrations/futurex-diary-widget.html",
         "press.html", "press-en.html", "404.html",
         "llms.txt", "llms-full.txt", "atom.xml", "sitemap.xml", "robots.txt",
         "humans.txt", "manifest.json", "sw.js"]

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry  = "--dry" in sys.argv
    rev  = "--revert" in sys.argv
    if rev:
        cur = read_current()
        if not cur: sys.exit("当前已是 github.io，无需回退")
        src, dst = cur, GH
    else:
        if not args: sys.exit(__doc__)
        dom = args[0].strip().strip("/")
        if "/" in dom or not re.match(r'^[a-z0-9.-]+$', dom):
            sys.exit(f"域名格式不对：{dom}")
        cur = read_current()
        src, dst = (cur or GH), dom
    if src == dst: sys.exit(f"无变化：已经是 {dst}")

    staged, total = {}, 0
    for f in FILES:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p): continue
        s = io.open(p, encoding="utf-8").read()
        n = s.count(src)
        if n:
            staged[p] = s.replace(src, dst); total += n
            print(f"  {f:18} {n:>4} 处")
    if not total: sys.exit(f"没找到 {src}，无可替换")
    print(f"合计 {total} 处：{src} → {dst}")
    if dry: print("DRY RUN — 未落盘"); return
    for p, s in staged.items():
        io.open(p, "w", encoding="utf-8").write(s)
    # 注意：走 Cloudflare Pages 路线时【不要】写 GitHub 的 CNAME 文件，
    # 否则 GitHub Pages 会抢占该域名并与 Cloudflare 冲突（见 SETUP-CUSTOM-DOMAIN.md）。
    io.open(os.path.join(ROOT, ".domain"), "w", encoding="utf-8").write(dst + "\n")
    print(f"已写入 {len(staged)} 个文件（未写 CNAME，Cloudflare 路线）；现在跑 python3 scripts/geo-check.py")

def read_current():
    p = os.path.join(ROOT, ".domain")
    return io.open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None

if __name__ == "__main__":
    main()
