#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量校验 — 比亚迪 (002594.SZ + 01211.HK), 前复权数据"""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import csv, os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
A_CSV = os.path.join(D, "byd_a_daily.csv")
HK_CSV = os.path.join(D, "byd_hk_daily.csv")

def load(p):
    if not os.path.exists(p): return None
    rows = []
    with open(p, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): rows.append(r)
    return rows

def ck_field(rows, lb):
    req = ["trade_date","open","close","high","low","vol"]
    return [f"[{lb}] R{i+2}: {f} empty" for i,r in enumerate(rows) for f in req if r.get(f,"").strip() in ("","None")]

def ck_uniq(rows, lb):
    s = {}; iss = []
    for i,r in enumerate(rows):
        d = r["trade_date"].strip()
        if d in s: iss.append(f"[{lb}] Dup: {d}")
        else: s[d]=i
    return iss

def ck_price(rows, lb):
    iss = []
    for r in rows:
        try:
            o,c,h,l_ = float(r["open"]),float(r["close"]),float(r["high"]),float(r["low"])
            if not (l_<=c<=h and l_<=o<=h): iss.append(f"[{lb}] {r['trade_date']}: O={o} C={c} H={h} L={l_}")
        except: pass
    return iss

def ck_pct(rows, lim, lb):
    return [f"[{lb}] {r['trade_date']}: pct {float(r['pct_chg']):+.2f}%" for r in rows
            if abs(float(r.get("pct_chg",0))) > lim]

def ck_cont(rows, fmt, lb):
    iss = []
    for i in range(1,len(rows)):
        try:
            p = datetime.strptime(rows[i-1]["trade_date"], fmt)
            c = datetime.strptime(rows[i]["trade_date"], fmt)
            if (c-p).days > 7: iss.append(f"[{lb}] {rows[i-1]['trade_date']}→{rows[i]['trade_date']}: {(c-p).days}d")
        except: pass
    return iss

def run(label, csv_p, pct_lim, date_fmt):
    rows = load(csv_p)
    print(f"\n{label} | Loaded: {len(rows) if rows else 0} | Limit: ±{pct_lim}%")
    if not rows: return
    for name, fn in [("字段完整", lambda: ck_field(rows,label)), ("日期唯一", lambda: ck_uniq(rows,label)),
                      ("价格合理", lambda: ck_price(rows,label)), ("涨跌幅", lambda: ck_pct(rows,pct_lim,label)),
                      ("连续性", lambda: ck_cont(rows,date_fmt,label))]:
        iss = fn(); st = "PASS" if not iss else f"{len(iss)} WARN"
        print(f"  [{st}] {name}")
        for x in iss[:2]: print(f"         {x}")

def main():
    print("="*50)
    print("  比亚迪 A+H 质量校验")
    print("="*50)
    run("A股", A_CSV, 10, "%Y%m%d")
    run("港股", HK_CSV, 30, "%Y-%m-%d")
    print(f"\n{'='*50}\n  校验完成\n{'='*50}")

if __name__ == "__main__":
    main()
