#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch 兆易创新 (603986.SH) daily K-line data via 腾讯行情 API.

Data source: web.ifzq.gtimg.cn (免token, 前复权 qfq)
Spec: specs/gdpy.yaml

Usage: python scripts/fetch_gdpy.py

Output:
  - data/gdpy_daily.csv  (utf-8-sig, ascending by date)
  - data/gdpy_daily.json (utf-8, indent=2)
"""
import sys
import io
import os

# ── UTF-8 修复 (Windows Git Bash 兼容) ──
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import json
import csv

# ── Config (from specs/gdpy.yaml) ──
TENCENT_CODE = "sh603986"      # 兆易创新 科创板
TS_CODE = "603986.SH"
NAME = "兆易创新"
LIMIT = 250                    # 约1年交易日
PCT_LIMIT = 20                 # 科创板 ±20%

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_tencent_kline(code, limit):
    """Fetch qfq day kline from Tencent API. Returns list of raw arrays.

    兼容 qfqday 和 day 两种返回 key（教训1）。
    """
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{limit},qfq"
    print(f"[FETCH] {url}")

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("Referer", f"https://gu.qq.com/{code}")
    resp = urllib.request.urlopen(req, timeout=15)
    api_data = json.loads(resp.read().decode("utf-8"))

    # 兼容 qfqday / day 两种 key（sh688981 返回 day，sh600900 返回 qfqday）
    raw = api_data["data"][code].get("qfqday") or api_data["data"][code].get("day", [])

    print(f"[OK]  Fetched {len(raw)} raw records")
    return raw


def parse_records(raw):
    """Convert Tencent raw arrays to standard dict records.

    Tencent day format: [date, open, close, high, low, volume]
    Index mapping: k[0]=date, k[1]=open, k[2]=close, k[3]=high, k[4]=low, k[5]=vol
    关键：idx2=close（不是idx3！）
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
    """Print data summary + quality check."""
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

    # ── 质量校验 ──
    print(f"\n  ── 质量校验 ──")
    # 1. 字段完整性
    missing = [r for r in records if not all(r.get(f) is not None for f in ["trade_date", "open", "close", "high", "low", "vol"])]
    print(f"  [{'PASS' if not missing else 'FAIL'}] 字段完整性: {len(missing)} 条缺失")

    # 2. 日期唯一
    dates = [r["trade_date"] for r in records]
    dup = len(dates) - len(set(dates))
    print(f"  [{'PASS' if dup == 0 else 'FAIL'}] 日期唯一: {dup} 条重复")

    # 3. 价格合理性
    bad_price = [r for r in records if not (r["low"] <= r["close"] <= r["high"] and r["low"] <= r["open"] <= r["high"])]
    print(f"  [{'PASS' if not bad_price else 'FAIL'}] 价格合理性: {len(bad_price)} 条异常")

    # 4. 涨跌幅阈值 (科创板 ±20%)
    over_limit = [r for r in records if abs(r["pct_chg"]) > PCT_LIMIT]
    print(f"  [{'WARN' if over_limit else 'PASS'}] 涨跌幅阈值(±{PCT_LIMIT}%): {len(over_limit)} 条超限")
    if over_limit:
        for r in over_limit[:5]:
            print(f"        {r['trade_date']}: {r['pct_chg']:+.2f}%")

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
    csv_path = os.path.join(DATA_DIR, "gdpy_daily.csv")
    json_path = os.path.join(DATA_DIR, "gdpy_daily.json")
    save_csv(records, csv_path)
    save_json(records, json_path)

    # 5. Summary + quality check
    print_summary(records)

    return records


if __name__ == "__main__":
    main()
