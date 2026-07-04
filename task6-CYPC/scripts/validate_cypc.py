#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量校验脚本 - 长江电力 (600900.SH)

基于 specs/cypc.yaml 定义的 6 项校验规则，对 K线数据和分红数据做全面检查。

Usage: python scripts/validate_cypc.py
"""
import sys
import io
# Fix Windows GBK encoding in Git Bash
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
CSV_PATH = os.path.join(DATA_DIR, "cypc_daily.csv")
DIV_PATH = os.path.join(DATA_DIR, "cypc_dividend.csv")

PCT_LIMIT = 10.0  # 主板涨跌幅阈值


def load_kline(path):
    """Load K-line CSV into list of dicts."""
    if not os.path.exists(path):
        return None, f"文件不存在: {path}"
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows, None


def load_dividend(path):
    """Load dividend CSV. Returns set of ex_date strings (YYYYMMDD)."""
    if not os.path.exists(path):
        return set(), f"分红文件不存在: {path} (跳过除权日校验)"
    ex_dates = set()
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            ex_dates.add(r.get("ex_date", "").strip())
    return ex_dates, None


# ── 校验 1: 字段完整性 ──
def check_field_completeness(rows):
    required = ["trade_date", "open", "close", "high", "low", "vol"]
    issues = []
    for i, r in enumerate(rows):
        for f in required:
            val = r.get(f, "").strip()
            if val == "" or val is None:
                issues.append(f"第{i+2}行 (date={r.get('trade_date','?')}): 字段 '{f}' 为空")
    return issues


# ── 校验 2: 日期唯一性 ──
def check_date_uniqueness(rows):
    seen = {}
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"].strip()
        if dt in seen:
            issues.append(f"日期重复: {dt} (第{seen[dt]+2}行 和 第{i+2}行)")
        else:
            seen[dt] = i
    return issues


# ── 校验 3: 价格合理性 ──
def check_price_sanity(rows):
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"]
        try:
            o, c, h, l_ = float(r["open"]), float(r["close"]), float(r["high"]), float(r["low"])
            if not (l_ <= c <= h and l_ <= o <= h):
                issues.append(f"{dt}: 价格不合理 O={o} C={c} H={h} L={l_}")
            if h <= 0 or l_ <= 0 or c <= 0 or o <= 0:
                issues.append(f"{dt}: 价格非正数 O={o} C={c} H={h} L={l_}")
        except (ValueError, TypeError):
            issues.append(f"{dt}: 价格字段无法解析为数字")
    return issues


# ── 校验 4: 涨跌幅阈值 ──
def check_pct_chg(rows, limit=PCT_LIMIT):
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"]
        try:
            pct = float(r["pct_chg"])
            if abs(pct) > limit:
                issues.append(f"{dt}: 涨跌幅 {pct:+.2f}% 超出主板 ±{limit}% 阈值")
        except (ValueError, TypeError):
            issues.append(f"{dt}: 涨跌幅无法解析")
    return issues


# ── 校验 5: 除权日跳空校验 ──
def check_dividend_gap(rows, ex_dates):
    if not ex_dates:
        return ["分红数据为空，跳过除权日跳空校验"]
    issues = []
    for i, r in enumerate(rows):
        dt = r["trade_date"].strip()
        if dt in ex_dates:
            try:
                pct = float(r["pct_chg"])
                if pct < -2.0:  # 除权日一般跌 1-5%
                    issues.append(f"{dt}: 除权日跌幅 {pct:.2f}%, 疑似除权效应（需人工确认）")
            except (ValueError, TypeError):
                pass
    return issues


# ── 校验 6: 交易日连续性 ──
def check_date_continuity(rows):
    from datetime import datetime, timedelta
    issues = []
    for i in range(1, len(rows)):
        try:
            prev = datetime.strptime(rows[i - 1]["trade_date"], "%Y%m%d")
            curr = datetime.strptime(rows[i]["trade_date"], "%Y%m%d")
            gap = (curr - prev).days
            if gap > 7:  # 超过 7 天（含春节/国庆长假）
                issues.append(f"{rows[i-1]['trade_date']} → {rows[i]['trade_date']}: 间隔 {gap} 天")
        except ValueError:
            pass
    return issues


# ── 主流程 ──
def main():
    print(f"{'='*60}")
    print(f"  长江电力 (600900.SH) 数据质量校验")
    print(f"{'='*60}\n")

    # 加载数据
    kline, err = load_kline(CSV_PATH)
    if err:
        print(f"[FAIL] {err}")
        sys.exit(1)
    print(f"[加载] K线数据: {len(kline)} 条")

    ex_dates, err = load_dividend(DIV_PATH)
    if err:
        print(f"[WARN] {err}")
    else:
        print(f"[加载] 分红除权日: {len(ex_dates)} 个")

    print(f"\n--- 执行校验 ---\n")

    # 定义校验: (名称, 函数, 严重度)
    checks = [
        ("1. 字段完整性",      check_field_completeness, "fail"),
        ("2. 日期唯一性",      check_date_uniqueness,    "fail"),
        ("3. 价格合理性",      check_price_sanity,       "fail"),
        ("4. 涨跌幅阈值 (±10%)", check_pct_chg,           "warn"),
        ("5. 除权日跳空校验",   lambda r: check_dividend_gap(r, ex_dates), "warn"),
        ("6. 交易日连续性",     check_date_continuity,    "warn"),
    ]

    total_issues = 0
    fails = 0
    warns = 0

    for name, func, severity in checks:
        issues = func(kline)
        total_issues += len(issues)
        if severity == "fail":
            fails += len(issues)
        else:
            warns += len(issues)

        status = "✅ 通过" if not issues else f"⚠️  {len(issues)} 个{severity.upper()}"
        print(f"  [{status}]  {name}")
        for issue in issues[:5]:  # 只显示前 5 个
            print(f"           └ {issue}")
        if len(issues) > 5:
            print(f"           └ ... 共 {len(issues)} 个问题")
        print()

    # 总结
    print(f"{'='*60}")
    if fails > 0:
        print(f"  ❌ 校验失败: {fails} 个 FAIL 级别问题，需要修复后重新取数")
    else:
        print(f"  ✅ 所有 FAIL 级别校验通过")
    if warns > 0:
        print(f"  ⚠️  告警: {warns} 个 WARN 级别问题，建议人工复核")
    else:
        print(f"  ✅ 无告警")
    print(f"{'='*60}")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
