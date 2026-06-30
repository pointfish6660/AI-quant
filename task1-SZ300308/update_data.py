#!/usr/bin/env python3
"""Update CSV with latest from Tencent API (unadjusted prices), then regenerate HTML."""
import csv, json, urllib.request, os, sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_data.csv")

# ── Fetch from Tencent (unadjusted day format) ──
url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz300308,day,,,320,qfq"
req = urllib.request.Request(url)
req.add_header("User-Agent", "Mozilla/5.0")
req.add_header("Referer", "https://gu.qq.com/sz300308")
resp = urllib.request.urlopen(req, timeout=15)
api_data = json.loads(resp.read().decode("utf-8"))
raw = api_data["data"]["sz300308"]["qfqday"]

# Tencent day format: [date, open, close, high, low, volume]
# Parse with correct mapping: idx1=open, idx2=close, idx3=high, idx4=low

# ── Read existing CSV dates ──
existing_dates = set()
all_rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        existing_dates.add(r["trade_date"])
        all_rows.append(r)

# Find latest close for pct_chg calculation
if all_rows:
    prev_close = float(all_rows[-1]["close"])
else:
    prev_close = None

print(f"Existing records: {len(existing_dates)}, latest close: {prev_close}")

# ── Append new records ──
new_count = 0
last_close = prev_close
with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    for k in raw:
        dt_raw = k[0]
        dt = dt_raw.replace("-", "")
        if dt in existing_dates:
            continue
        
        o = float(k[1])   # open
        c = float(k[2])   # close (Tencent: idx2)
        h = float(k[3])   # high  (Tencent: idx3)
        l = float(k[4])   # low   (Tencent: idx4)
        v = float(k[5])
        amount = round(v * (h + l + c) / 3, 0)
        
        # Calculate pct_chg
        if last_close and last_close > 0:
            pct_chg = ((c - last_close) / last_close) * 100
        else:
            pct_chg = 0
        last_close = c
        
        writer.writerow([dt, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", str(int(v)), f"{amount:.0f}", f"{pct_chg:.4f}"])
        new_count += 1
        arrow = "▲" if pct_chg >= 0 else "▼"
        print(f"  + {dt_raw}  {arrow}{abs(pct_chg):.1f}%  O={o:.2f} C={c:.2f} H={h:.2f} L={l:.2f} V={int(v)}")

print(f"\nAppended {new_count} new records. Total: {len(existing_dates) + new_count}")

if new_count > 0:
    print("Regenerating HTML...")
    ret = os.system(f'python3 "{os.path.join(os.path.dirname(__file__), "build_kline.py")}"')
    if ret != 0:
        print("Warning: build_kline.py returned non-zero, but HTML may be generated")
