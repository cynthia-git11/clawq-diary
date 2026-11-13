# -*- coding: utf-8 -*-
"""ENTRY 152 recompute: every OpenRouter number used in the entry, from the raw JSON pulls.
Usage: python3 scripts/kimi-openrouter-share.py   (reads archive/meter-snapshots/2026-11-13-openrouter-kimi-*.json.gz)
"""
import json, sys, os, gzip
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'archive', 'meter-snapshots')
F = {'verB-or-k31pro-endpoint-stats-20261113.json': 'k31pro-endpoints-read1', 'verB-or-k31pro-endpoint-stats-20261112T2239Z.json': 'k31pro-endpoints-read2',
     'verB-or-k31pro-endpoint-stats-20261112T2240Z.json': 'k31pro-endpoints-read3', 'verB-or-k3-endpoint-stats-20261113.json': 'k3-endpoints',
     'verB-or-k31pro-model_chart-20261113.json': 'k31pro-daily-requests'}
def jopen(f): return gzip.open(os.path.join(D, f'2026-11-13-openrouter-kimi-{F[f]}.json.gz'), 'rt', encoding='utf-8')
READS = ['verB-or-k31pro-endpoint-stats-20261113.json',          # read 1 (cached, identical to T2236Z)
         'verB-or-k31pro-endpoint-stats-20261112T2239Z.json',    # read 2
         'verB-or-k31pro-endpoint-stats-20261112T2240Z.json']    # read 3

def load(f):
    return json.load(jopen(f))['data']

def price(e):
    p = e['pricing']; return round(float(p['prompt']) * 1e6, 3), round(float(p['completion']) * 1e6, 3)

own_all, own_std, own_hs, host_avg = [], [], [], []
for f in READS:
    d = load(f)
    tot = sum(e['stats']['request_count'] or 0 for e in d)
    mo = [e for e in d if e['provider_display_name'] == 'Moonshot AI']
    std = sum(e['stats']['request_count'] for e in mo if not e['provider_model_id'].endswith('highspeed'))
    hs = sum(e['stats']['request_count'] for e in mo if e['provider_model_id'].endswith('highspeed'))
    own_all.append((std + hs) / tot); own_std.append(std / tot); own_hs.append(hs / tot)
    same = [e for e in d if price(e) == (2.0, 10.0) and e['provider_display_name'] != 'Moonshot AI']
    host_avg.append(sum(e['stats']['request_count'] for e in same) / tot / len(same))
    slow = sorted(d, key=lambda e: e['stats']['p50_throughput'])[:2]
    third = [e for e in d if e['provider_display_name'] != 'Moonshot AI']
    print(f, 'total', tot, 'endpoints', len(d), 'third-party', len(third),
          'earliest third-party', min(e['created_at'] for e in third)[:16])
    print('  own %.1f%% (std %.1f%%, highspeed %.1f%%); same-price $2/$10 hosts n=%d avg %.1f%%'
          % (own_all[-1] * 100, own_std[-1] * 100, own_hs[-1] * 100, len(same), host_avg[-1] * 100))
    print('  two slowest p50:', [(e['provider_display_name'], e['stats']['p50_throughput'], price(e)) for e in slow])
m = lambda xs: sum(xs) / len(xs) * 100
print('MEAN own %.1f%%  std %.1f%%  highspeed %.1f%%' % (m(own_all), m(own_std), m(own_hs)))

k3 = json.load(jopen('verB-or-k3-endpoint-stats-20261113.json'))['data']
t3 = sum(e['stats']['request_count'] or 0 for e in k3)
for name in ('Moonshot AI', 'Amazon Bedrock'):
    xs = [e for e in k3 if e['provider_display_name'] == name]
    print('K3', name, 'endpoints', len(xs), '%.1f%%' % (sum(e['stats']['request_count'] for e in xs) / t3 * 100),
          [price(e) for e in xs])

ch = json.load(jopen('verB-or-k31pro-model_chart-20261113.json'))
day = {r['date'][:10]: r['count'] for r in ch}
pre = [v for k, v in day.items() if '2026-10-24' <= k <= '2026-11-03']
post = [v for k, v in day.items() if '2026-11-05' <= k <= '2026-11-11']
a, b = sum(pre) / len(pre), sum(post) / len(post)
print('daily requests pre %.0f (n=%d) post %.0f (n=%d)' % (a, len(pre), b, len(post)))
lo, hi = min(own_all) * b, max(own_all) * b
print('own/day %.2fM-%.2fM, drop %.0f%%-%.0f%%' % (lo / 1e6, hi / 1e6, (1 - hi / a) * 100, (1 - lo / a) * 100))
print('2x mean share drop %.0f%%' % ((1 - 2 * m(own_all) / 100 * b / a) * 100))
be = a / 2 / b
print('break-even share for "more than half" %.1f%% = %.1fx snapshot mean' % (be * 100, be * 100 / m(own_all)))
