#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch 长江电力 (600900.SH) daily K-line data via 腾讯行情 API.

Data source: web.ifzq.gtimg.cn (免token, 前复权 qfq)
Spec: specs/cypc.yaml

Usage: python scripts/fetch_cypc.py

Output:
  - data/cypc_daily.csv  (utf-8-sig, ascending by date)
  - data/cypc_daily.json (utf-8, indent=2)
"""
import urllib.request
import json
import csv
import os
import sys

# ── Config (from specs/cypc.yaml) ──
TENCENT_CODE = "sh600900"
TS_CODE = "600900.SH"
NAME = "长江电力"
LIMIT = 320

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_tencent_kline(code, limit):
    """Fetch qfq day kline from Tencent API. Returns list of raw arrays."""
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{limit},qfq"
    print(f"[FETCH] {url}")

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("Referer", f"https://gu.qq.com/{code}")
    resp = urllib.request.urlopen(req, timeout=15)
    api_data = json.loads(resp.read().decode("utf-8"))

    try:
        raw = api_data["data"][code]["qfqday"]
    except KeyError:
        # Try without 'day' suffix
        raw = api_data["data"][code].get("qfqday", [])

    print(f"[OK]  Fetched {len(raw)} raw records")
    return raw


def parse_records(raw):
    """Convert Tencent raw arrays to standard dict records.

    Tencent day format: [date, open, close, high, low, volume]
    Index mapping: k[0]=date, k[1]=open, k[2]=close, k[3]=high, k[4]=low, k[5]=vol
    (Verified in task1-SZ300308/update_data.py line 16-17)
    """
    records = []
    for k in raw:
        dt_raw = k[0]
        rec = {
            "trade_date": dt_raw.replace("-", ""),  # YYYY-MM-DD -> YYYYMMDD
            "open":       float(k[1]),
            "close":      float(k[2]),  # Tencent: idx2 = close
            "high":       float(k[3]),
            "low":        float(k[4]),
            "vol":        float(k[5]),  # unit: 手
            "amount":     round(float(k[5]) * (float(k[3]) + float(k[4]) + float(k[2])) / 3, 0),
            "turnover":   None,  # Tencent 不提供换手率
        }
        records.append(rec)

    # Sort ascending by date
    records.sort(key=lambda x: x["trade_date"])
    return records


def compute_pct_chg(records):
    """Compute chain-based pct_chg (涨跌幅%)."""
    for i, rec in enumerate(records):
        if i == 0:
            # First record: use (close - open) / open
            o, c = rec["open"], rec["close"]
            rec["pct_chg"] = round((c - o) / o * 100, 4) if o else 0.0
        else:
            prev_close = records[i - 1]["close"]
            cur_close = rec["close"]
            rec["pct_chg"] = round((cur_close - prev_close) / prev_close * 100, 4)

    return records


def save_csv(records, path):
    """Save records as CSV with utf-8-sig BOM (Excel friendly)."""
    fieldnames = ["trade_date", "open", "close", "high", "low", "vol",
                  "amount", "pct_chg", "turnover"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})
    print(f"[OK]  Saved CSV: {path} ({len(records)} records)")


def save_json(records, path):
    """Save records as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[OK]  Saved JSON: {path}")


def print_summary(records):
    """Print data summary."""
    if not records:
        print("[WARN] No records to summarize")
        return

    first = records[0]
    last = records[-1]
    sp = first["close"]
    ep = last["close"]
    chg = ep - sp
    pct = (ep / sp - 1) * 100 if sp else 0

    all_high = max(r["high"] for r in records)
    all_low = min(r["low"] for r in records)
    max_pct = max(r["pct_chg"] for r in records)
    min_pct = min(r["pct_chg"] for r in records)

    print(f"\n{'='*60}")
    print(f"  {NAME} ({TS_CODE}) 日K线数据摘要")
    print(f"{'='*60}")
    print(f"  时间范围:  {first['trade_date']} ~ {last['trade_date']}  ({len(records)} 交易日)")
    print(f"  收盘价:    {sp:.2f} -> {ep:.2f}  {'' if chg<0 else '+'}{chg:.2f}  ({'' if pct<0 else '+'}{pct:.2f}%)")
    print(f"  区间最高:  {all_high:.2f}")
    print(f"  区间最低:  {all_low:.2f}")
    print(f"  最大单日涨幅: +{max_pct:.2f}%")
    print(f"  最大单日跌幅: {min_pct:.2f}%")
    print(f"{'='*60}")


def main():
    print(f"=== 取数: {NAME} ({TS_CODE}) | 数据源: 腾讯行情 ===\n")

    # 1. Fetch raw data
    raw = fetch_tencent_kline(TENCENT_CODE, LIMIT)
    if not raw:
        print("[ERROR] No data returned from Tencent API")
        sys.exit(1)

    # 2. Parse records
    records = parse_records(raw)
    print(f"[OK]  Parsed {len(records)} records")

    # 3. Compute pct_chg
    records = compute_pct_chg(records)

    # 4. Save outputs
    csv_path = os.path.join(DATA_DIR, "cypc_daily.csv")
    json_path = os.path.join(DATA_DIR, "cypc_daily.json")
    save_csv(records, csv_path)
    save_json(records, json_path)

    # 5. Summary
    print_summary(records)

    return records


if __name__ == "__main__":
    main()
