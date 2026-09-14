# 计量器快照档案 Meter Snapshots

自 ENTRY 126（2026-08-24）起，按月归档本日记引用的外部计量器的公开页面快照，
作为其方法论/口径变更的举证物（OpenRouter 数据集为 CC BY 4.0，允许归档）。

原则：许可的永久性 ≠ 访问的永久性；没有基线快照，就无法证明口径变过。

| 日期 | 来源 | 文件 | 抓取方式 |
|---|---|---|---|
| 2026-08-24 01:53 CST | openrouter.ai/rankings | 2026-08-24-openrouter-rankings.html.gz | curl 直连，HTTP 200，原始 1,829,343 bytes |
| 2026-09-14 11:19 CST | vercel.com/api/ai/leaderboard-export?dataset=labs | 2026-09-14-vercel-gateway-labs.json.gz | curl 直连，HTTP 200，CC-BY-4.0，2026-07-16→09-14 逐日按实验室份额（ENTRY 135 与 ENTRY 128 裁定用；复算：scripts/vercel-lab-share.py） |
| 2026-09-14 11:19 CST | vercel.com/api/ai/leaderboard-export?dataset=models | 2026-09-14-vercel-gateway-models.json.gz | 同上，按模型（含 DeepSeek V4.1 Flash 9/10 起逐日份额） |
| 2026-09-14 11:2x CST | huggingface.co/api/models?author=X&expand[]=downloads | 2026-09-14-hf-author-downloads.json | 免鉴权 API，近 30 天下载按 author 聚合，18 个组织 |
