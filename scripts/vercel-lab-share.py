#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复算 Vercel AI Gateway 官方导出（CC-BY-4.0）里任意一组实验室的份额。
用法：python3 scripts/vercel-lab-share.py [导出文件或.gz] [起始日] [结束日] [lab1,lab2,...]
默认：在线拉取 dataset=labs；窗口取最近 30 个完整日；lab 组为 NSA/CISA/FBI 通告 AA26-251A 点名的 6 家。
ENTRY 128 的裁定口径（广义中国实验室）请传：
  alibaba,bytedance,deepseek,inclusionai,minimax,moonshotai,stepfun,tencent,xiaomi,zai,kwaipilot,klingai
"""
import json, sys, gzip, statistics, collections, urllib.request
URL = "https://vercel.com/api/ai/leaderboard-export?dataset=labs&modality=all&format=json"
src = sys.argv[1] if len(sys.argv) > 1 else None
if src:
    raw = gzip.open(src, "rt", encoding="utf-8").read() if src.endswith(".gz") else open(src, encoding="utf-8").read()
else:
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "clawq-meter/1.0"}), timeout=60).read().decode()
rows = json.loads(raw)["rows"]
dates = sorted({r["date"] for r in rows})
start = sys.argv[2] if len(sys.argv) > 2 else dates[-31]
end = sys.argv[3] if len(sys.argv) > 3 else dates[-2]   # 最后一天可能是不完整日，默认剔除
labs = set((sys.argv[4] if len(sys.argv) > 4 else "deepseek,moonshotai,alibaba,minimax,stepfun,zai").split(","))
print(f"窗口 {start} → {end} · 实验室 {sorted(labs)}")
print(f"导出内全部 lab 名：{sorted({r['name'] for r in rows})}")
for metric in ["tokens", "spend", "requests"]:
    byday = collections.defaultdict(float)
    for r in rows:
        if r["metric"] == metric and start <= r["date"] <= end and r["name"] in labs:
            byday[r["date"]] += r["share_percent"]
    vals = [byday[d] for d in sorted(byday)]
    print(f"{metric:9s} 日均 {statistics.mean(vals):5.1f}% · 最低日 {min(vals):5.1f}% · 最高日 {max(vals):5.1f}% · 末日 {vals[-1]:5.1f}% · 天数 {len(vals)}")
