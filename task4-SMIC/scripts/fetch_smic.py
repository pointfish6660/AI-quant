#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch 中芯国际 (688981.SH + 00981.HK) daily K-line data.

A股: 腾讯行情 API (sh688981, qfq)
港股: westock CLI (hk00981)
Spec: specs/smic.yaml

Usage: python scripts/fetch_smic.py
Output: data/smic_a_daily.csv, smic_a_daily.json, smic_hk_daily.csv, smic_hk_daily.json
"""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import json
import csv
import os
import subprocess

# ── Config (from specs/smic.yaml) ──
TENCENT_CODE = "sh688981"
A_CODE = "688981.SH"
HK_CODE = "00981.HK"
WESTOCK_CODE = "hk00981"
NAME = "中芯国际"
LIMIT_A = 320
LIMIT_HK = 300

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ── A股: 腾讯行情 ──
def fetch_a_share():
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?param={TENCENT_CODE},day,,,{LIMIT_A},qfq")
    print(f"[A-Share FETCH] {url}")

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=15)
    api_data = json.loads(resp.read().decode("utf-8"))

    raw = api_data["data"][TENCENT_CODE].get("qfqday") or api_data["data"][TENCENT_CODE].get("day", [])
    print(f"[A-Share OK] {len(raw)} raw records")

    records = []
    for k in raw:
        o, c, h, l_ = float(k[1]), float(k[2]), float(k[3]), float(k[4])
        v = float(k[5])
        rec = {
            "trade_date": k[0].replace("-", ""),
            "open": o, "close": c, "high": h, "low": l_,
            "vol": v,  # 手
            "amount": round(v * (h + l_ + c) / 3, 0),
            "turnover": None,
        }
        records.append(rec)

    records.sort(key=lambda x: x["trade_date"])

    # pct_chg
    for i, rec in enumerate(records):
        if i == 0:
            o, c = rec["open"], rec["close"]
            rec["pct_chg"] = round((c - o) / o * 100, 4) if o else 0.0
        else:
            prev = records[i - 1]["close"]
            rec["pct_chg"] = round((rec["close"] - prev) / prev * 100, 4)

    # Save
    save_records(records, "smic_a")
    return records


# ── 港股: westock CLI ──
def fetch_hk_share():
    print(f"\n[HK-Share FETCH] westock CLI: {WESTOCK_CODE}")

    cmd = f"npx -y westock-data-clawhub@1.0.4 kline {WESTOCK_CODE} --period day --limit {LIMIT_HK}"
    print(f"  [CMD] {cmd}")
    result = subprocess.run(
        cmd, capture_output=True, text=True, shell=True,
        timeout=180, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
        return []

    # Parse Markdown table
    lines = [l.strip() for l in result.stdout.split("\n") if l.strip().startswith("|")]
    if len(lines) < 3:
        print(f"[ERROR] Unexpected westock output")
        return []

    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    data_lines = [l for l in lines[1:] if not all(c in "-:|" for c in l.replace(" ", ""))]

    records = []
    for line in data_lines:
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) != len(headers) or "npm notice" in line:
            continue
        row = dict(zip(headers, cells))
        rec = {
            "trade_date": row.get("date", ""),
            "open": to_float(row.get("open")),
            "close": to_float(row.get("last")),  # westock: last = close
            "high": to_float(row.get("high")),
            "low": to_float(row.get("low")),
            "vol": to_float(row.get("volume")),  # 股
            "amount": to_float(row.get("amount")),
            "turnover": to_float(row.get("exchange")),
        }
        records.append(rec)

    records.sort(key=lambda x: x["trade_date"])

    # pct_chg
    for i, rec in enumerate(records):
        if i == 0:
            o, c = rec["open"], rec["close"]
            rec["pct_chg"] = round((c - o) / o * 100, 4) if o and c else 0.0
        else:
            prev = records[i - 1]["close"]
            if prev:
                rec["pct_chg"] = round((rec["close"] - prev) / prev * 100, 4)
            else:
                rec["pct_chg"] = 0.0

    print(f"[HK-Share OK] {len(records)} records")

    # Save
    save_records(records, "smic_hk")
    return records


def to_float(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def save_records(records, prefix):
    fieldnames = ["trade_date", "open", "close", "high", "low", "vol",
                  "amount", "pct_chg", "turnover"]

    csv_path = os.path.join(DATA_DIR, f"{prefix}_daily.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})
    print(f"  [SAVE] {csv_path}")

    json_path = os.path.join(DATA_DIR, f"{prefix}_daily.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  [SAVE] {json_path}")


def print_summary(records, label, code):
    if not records:
        return
    f, l_ = records[0], records[-1]
    sp, ep = f["close"], l_["close"]
    chg = ep - sp if sp and ep else 0
    pct = (ep / sp - 1) * 100 if sp else 0
    print(f"\n{'='*50}")
    print(f"  {label} ({code})  {f['trade_date']} ~ {l_['trade_date']}  ({len(records)} days)")
    print(f"  Close: {sp} -> {ep}  ({'+' if chg>=0 else ''}{chg:.2f})")
    print(f"  Pct: {'+' if pct>=0 else ''}{pct:.2f}%")
    print(f"{'='*50}")


def main():
    print(f"=== 取数: {NAME} (A+H 双重上市) ===\n")

    a_records = fetch_a_share()
    print_summary(a_records, "A股", A_CODE)

    hk_records = fetch_hk_share()
    print_summary(hk_records, "港股", HK_CODE)

    print(f"\n=== Done ===")
    print(f"  A股: {len(a_records)} records")

    return 0


if __name__ == "__main__":
    main()
