#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch 智谱 (hk02513) daily K-line data via 腾讯自选股 (westock-data) CLI.

Data source: 腾讯自选股行情数据接口 (npx westock-data-clawhub)
Usage: python fetch_zhipu.py

Output:
  - zhipu_data.json  (raw records, ascending by date)
  - zhipu_data.csv   (with computed pct_chg field)
"""
import subprocess
import json
import csv
import os
import sys

TS_CODE = "hk02513"
NAME = "智谱"
LIMIT = 300  # 智谱 2026-01-08 上市，约 100 个交易日，300 足够

HERE = os.path.dirname(os.path.abspath(__file__))


def run_npx(*args):
    """Run npx command and return stdout string."""
    cmd = ["npx", "-y", "westock-data-clawhub@1.0.4", *args]
    print(f"[CMD] {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True,          # Windows needs shell to find npx
        timeout=180,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"[ERROR] returncode={result.returncode}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout


def parse_markdown_table(text):
    """Parse markdown table output from westock CLI into list of dicts."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 3:
        raise ValueError("Unexpected table format")

    # First line = header
    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    # Skip separator line (| --- | --- |)
    data_lines = [l for l in lines[1:] if not all(c in "-:|" for c in l.replace(" ", ""))]

    rows = []
    for line in data_lines:
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) != len(headers):
            continue
        row = {}
        for h, c in zip(headers, cells):
            # Strip npm notice lines that sneak in
            if "npm notice" in c:
                break
            row[h] = c
        else:
            rows.append(row)
    return rows


def to_float(val):
    """Parse a numeric string, handling commas and units."""
    if val is None:
        return None
    s = str(val).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def main():
    print(f"=== Fetching {NAME} ({TS_CODE}) K-line data ===")

    # 1. Get K-line data
    raw = run_npx("kline", TS_CODE, "--period", "day", "--limit", str(LIMIT))
    rows = parse_markdown_table(raw)
    print(f"[OK] Parsed {len(rows)} raw K-line rows")

    # Field mapping: westock uses 'last' for close, 'exchange' for turnover
    records = []
    for r in rows:
        rec = {
            "trade_date": r.get("date", ""),
            "open": to_float(r.get("open")),
            "close": to_float(r.get("last")),   # 'last' = closing price
            "high": to_float(r.get("high")),
            "low": to_float(r.get("low")),
            "vol": to_float(r.get("volume")),    # unit: shares (股)
            "amount": to_float(r.get("amount")),
            "turnover": to_float(r.get("exchange")),  # turnover rate %
        }
        records.append(rec)

    # Sort ascending by date (westock returns descending)
    records.sort(key=lambda x: x["trade_date"])

    # Compute pct_chg (涨跌幅 %)
    for i, rec in enumerate(records):
        if i == 0:
            # IPO first day: use (close - open) / open as proxy
            o, c = rec["open"], rec["close"]
            rec["pct_chg"] = round((c - o) / o * 100, 2) if o else 0.0
        else:
            prev_close = records[i - 1]["close"]
            cur_close = rec["close"]
            rec["pct_chg"] = round((cur_close - prev_close) / prev_close * 100, 2)

    # Save JSON
    json_path = os.path.join(HERE, "zhipu_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved JSON: {json_path} ({len(records)} records)")

    # Save CSV
    csv_path = os.path.join(HERE, "zhipu_data.csv")
    fieldnames = ["trade_date", "open", "close", "high", "low", "vol", "amount", "pct_chg", "turnover"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})
    print(f"[OK] Saved CSV: {csv_path}")

    # Summary
    if records:
        first = records[0]
        last = records[-1]
        sp = first["close"]
        ep = last["close"]
        chg = ep - sp
        pct = (ep / sp - 1) * 100
        print(f"\n=== Summary ===")
        print(f"  Period: {first['trade_date']} ~ {last['trade_date']}  ({len(records)} days)")
        print(f"  Close: {sp:.2f} -> {ep:.2f}  ({'+'if chg>=0 else ''}{chg:.2f}, {'+'if pct>=0 else ''}{pct:.2f}%)")
        print(f"  High: {max(r['high'] for r in records):.2f}")
        print(f"  Low:  {min(r['low'] for r in records):.2f}")

    # 2. Get company profile
    print(f"\n=== Fetching {NAME} profile ===")
    try:
        prof_raw = run_npx("profile", TS_CODE)
        prof_rows = parse_markdown_table(prof_raw)
        if prof_rows:
            prof_path = os.path.join(HERE, "zhipu_profile.json")
            with open(prof_path, "w", encoding="utf-8") as f:
                json.dump(prof_rows[0], f, ensure_ascii=False, indent=2)
            print(f"[OK] Saved profile: {prof_path}")
    except Exception as e:
        print(f"[WARN] Profile fetch failed: {e}")


if __name__ == "__main__":
    main()
