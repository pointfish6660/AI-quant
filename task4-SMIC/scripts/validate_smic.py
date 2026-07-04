#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量校验 — 中芯国际 (688981.SH + 00981.HK)

基于 specs/smic.yaml:
  A股科创板 pct_limit=20%
  港股 pct_limit=30%(合理性)
  额外：A/H 折溢价合理性校验
"""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import csv, os
from datetime import datetime

# Add skill scripts to path
SKILL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                         ".workbuddy", "skills", "ba-quant-fetch", "scripts")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")

A_CSV = os.path.join(DATA_DIR, "smic_a_daily.csv")
HK_CSV = os.path.join(DATA_DIR, "smic_hk_daily.csv")


def load_csv(path):
    if not os.path.exists(path):
        return None, f"File not found: {path}"
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows, None


# ── Basic validation (通用) ──
def check_required(rows, label):
    required = ["trade_date", "open", "close", "high", "low", "vol"]
    issues = []
    for i, r in enumerate(rows):
        for f in required:
            val = r.get(f, "").strip()
            if val == "" or val is None or val == "None":
                issues.append(f"[{label}] Row {i+2}: '{f}' empty")
    return issues

def check_unique(rows, label):
    seen = {}
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"].strip()
        if dt in seen:
            issues.append(f"[{label}] Duplicate: {dt}")
        else:
            seen[dt] = i
    return issues

def check_price(rows, label):
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"]
        try:
            o, c, h, l_ = float(r["open"]), float(r["close"]), float(r["high"]), float(r["low"])
            if not (l_ <= c <= h and l_ <= o <= h):
                issues.append(f"[{label}] {dt}: price O={o} C={c} H={h} L={l_}")
        except:
            issues.append(f"[{label}] {dt}: parse error")
    return issues

def check_pct(rows, limit, label):
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"]
        try:
            pct = float(r["pct_chg"])
            if abs(pct) > limit:
                issues.append(f"[{label}] {dt}: pct {pct:+.2f}% > ±{limit}%")
        except:
            pass
    return issues

def check_continuity(rows, date_fmt, label):
    issues = []
    for i in range(1, len(rows)):
        try:
            prev = datetime.strptime(rows[i-1]["trade_date"], date_fmt)
            curr = datetime.strptime(rows[i]["trade_date"], date_fmt)
            gap = (curr - prev).days
            if gap > 7:
                issues.append(f"[{label}] {rows[i-1]['trade_date']} → {rows[i]['trade_date']}: {gap}d gap")
        except:
            pass
    return issues


# ── A/H 折溢价校验（task4 特有） ──
def check_ah_premium():
    """Check A/H premium ratio is within reasonable bounds.

    AH premium = (A_price / H_price / FX_rate - 1) * 100
    Without FX rate, check raw ratio: A_price / H_price should be 0.5~5x.
    """
    a_rows, _ = load_csv(A_CSV)
    hk_rows, _ = load_csv(HK_CSV)
    if not a_rows or not hk_rows:
        return ["[AH] Cannot load both A and HK data, skipping"]

    # Build dicts by date
    # A股: YYYYMMDD, 港股: YYYY-MM-DD
    a_by_date = {}
    for r in a_rows:
        a_by_date[r["trade_date"].strip()] = float(r["close"])

    hk_by_date = {}
    for r in hk_rows:
        hk_by_date[r["trade_date"].strip()] = float(r["close"])

    issues = []
    checked = 0
    for a_date, a_close in a_by_date.items():
        # Convert YYYYMMDD → YYYY-MM-DD for HK matching
        a_date_fmt = f"{a_date[:4]}-{a_date[4:6]}-{a_date[6:8]}"
        hk_close = hk_by_date.get(a_date_fmt)
        if hk_close is None:
            continue
        ratio = a_close / hk_close
        # Without FX rate, AH premium range ~0.5x to 5x is normal
        if ratio < 0.3 or ratio > 6.0:
            issues.append(f"[AH] {a_date}: A=¥{a_close:.2f} H=HK${hk_close:.2f} ratio={ratio:.1f}x")
        checked += 1

    if checked == 0:
        return ["[AH] No matching dates between A and HK, skipping"]
    return issues


def main():
    print("=" * 60)
    print("  中芯国际 A+H 数据质量校验")
    print("=" * 60)

    # A股
    a_rows, a_err = load_csv(A_CSV)
    print(f"\n[A股] Loaded: {len(a_rows) if a_rows else 0} rows | Limit: ±20%")

    if a_rows:
        for name, fn in [
            ("字段完整性", lambda: check_required(a_rows, "A")),
            ("日期唯一", lambda: check_unique(a_rows, "A")),
            ("价格合理", lambda: check_price(a_rows, "A")),
            ("涨跌幅 ±20%", lambda: check_pct(a_rows, 20, "A")),
            ("连续性", lambda: check_continuity(a_rows, "%Y%m%d", "A")),
        ]:
            issues = fn()
            status = "PASS" if not issues else f"{len(issues)} WARN"
            print(f"  [{status}] {name}")
            for iss in issues[:3]:
                print(f"         {iss}")

    # 港股
    hk_rows, hk_err = load_csv(HK_CSV)
    print(f"\n[H股] Loaded: {len(hk_rows) if hk_rows else 0} rows | Limit: ±30%(合理性)")

    if hk_rows:
        for name, fn in [
            ("字段完整性", lambda: check_required(hk_rows, "HK")),
            ("日期唯一", lambda: check_unique(hk_rows, "HK")),
            ("价格合理", lambda: check_price(hk_rows, "HK")),
            ("涨跌幅 ±30%", lambda: check_pct(hk_rows, 30, "HK")),
            ("连续性", lambda: check_continuity(hk_rows, "%Y-%m-%d", "HK")),
        ]:
            issues = fn()
            status = "PASS" if not issues else f"{len(issues)} WARN"
            print(f"  [{status}] {name}")
            for iss in issues[:3]:
                print(f"         {iss}")

    # A/H premium
    print(f"\n[A/H 折溢价]")
    ah_issues = check_ah_premium()
    if ah_issues:
        for iss in ah_issues[:5]:
            print(f"  {iss}")

    print(f"\n{'=' * 60}")
    print("  校验完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
