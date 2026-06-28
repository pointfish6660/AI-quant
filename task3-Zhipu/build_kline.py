#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate comprehensive analysis page for 智谱 (Zhipu AI) 02513.HK

Reads zhipu_data.json (from fetch_zhipu.py, 腾讯自选股 data source),
computes technical indicators (MA, MACD, Bollinger Bands, RSI, golden/death cross),
injects into chart_template.html, outputs zhipu_chart.html.

Usage: python build_kline.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "zhipu_data.json")
TEMPLATE_PATH = os.path.join(HERE, "chart_template.html")
OUTPUT_PATH = os.path.join(HERE, "zhipu_chart.html")

# ── Load data ──
with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

rows = []
for r in raw:
    d = r["trade_date"]  # already YYYY-MM-DD format
    rows.append(dict(
        date=d,
        open=float(r["open"]),
        close=float(r["close"]),
        high=float(r["high"]),
        low=float(r["low"]),
        vol=float(r["vol"]),          # unit: shares (股)
        amount=float(r.get("amount", 0)),
        pct_chg=float(r.get("pct_chg", 0)),
    ))

rows.sort(key=lambda x: x["date"])
N = len(rows)

dates = [r["date"] for r in rows]
opens = [r["open"] for r in rows]
closes = [r["close"] for r in rows]
highs = [r["high"] for r in rows]
lows = [r["low"] for r in rows]
pcts = [r["pct_chg"] for r in rows]
# Convert shares -> 万股 (10,000 shares)
vols = [round(r["vol"] / 10000, 2) for r in rows]
amounts = [round(r["amount"] / 10000, 2) for r in rows]


# ── Technical indicator calculations ──
def sma(data, period):
    r = [None] * len(data)
    for i in range(period - 1, len(data)):
        r[i] = sum(data[i - period + 1:i + 1]) / period
    return r


def ema(data, period):
    a = 2 / (period + 1)
    r = [None] * len(data)
    first = next(i for i, v in enumerate(data) if v is not None)
    r[first] = data[first]
    for i in range(first + 1, len(data)):
        r[i] = a * data[i] + (1 - a) * r[i - 1]
    return r


def rstd(data, period):
    r = [None] * len(data)
    for i in range(period - 1, len(data)):
        w = data[i - period + 1:i + 1]
        m = sum(w) / period
        r[i] = (sum((x - m) ** 2 for x in w) / period) ** 0.5
    return r


def diff(a, b):
    return [a[i] - b[i] if a[i] is not None and b[i] is not None else None for i in range(len(a))]


def mult(a, k):
    return [a[i] * k if a[i] is not None else None for i in range(len(a))]


def rsi_calc(data, period=14):
    r = [None] * len(data)
    gains = []
    losses = []
    for i in range(1, len(data)):
        c = data[i] - data[i - 1]
        gains.append(max(c, 0))
        losses.append(max(-c, 0))
    for i in range(period - 1, len(gains)):
        ag = sum(gains[i - period + 1:i + 1]) / period
        al = sum(losses[i - period + 1:i + 1]) / period
        r[i + 1] = 100 if al == 0 else round(100 - 100 / (1 + ag / al), 2)
    return r


ma5 = sma(closes, 5)
ma10 = sma(closes, 10)
ma20 = sma(closes, 20)
bb_mid = ma20
bb_std = rstd(closes, 20)
bb_upper = [bb_mid[i] + 2 * bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
bb_lower = [bb_mid[i] - 2 * bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
ema12 = ema(closes, 12)
ema26 = ema(closes, 26)
dif_ = diff(ema12, ema26)
dea_ = ema(dif_, 9)
macd_hist = mult(diff(dif_, dea_), 2)
rsi14 = rsi_calc(closes, 14)


# ── Golden / Death cross detection (MA5 vs MA10) ──
def find_cross(a, b):
    c = []
    for i in range(1, len(a)):
        if a[i] is None or b[i] is None or a[i - 1] is None or b[i - 1] is None:
            continue
        if a[i - 1] <= b[i - 1] and a[i] > b[i]:
            c.append((i, "gold"))
        elif a[i - 1] >= b[i - 1] and a[i] < b[i]:
            c.append((i, "death"))
    return c


gc_5_10 = find_cross(ma5, ma10)


def last_cross_str(crosses, typ):
    for idx, t in reversed(crosses):
        if t == typ and idx < N:
            return dates[idx]
    return "—"


last_gc = last_cross_str(gc_5_10, "gold")
last_dc = last_cross_str(gc_5_10, "death")

# Cross markers for JS chart
gc_markers = []
dc_markers = []
for idx, typ in gc_5_10[-8:]:
    if typ == "gold":
        gc_markers.append([idx, round(lows[idx], 2)])
    else:
        dc_markers.append([idx, round(highs[idx], 2)])


# ── Summary statistics ──
sp = closes[0]   # IPO first day close
ep = closes[-1]  # latest close
chg = ep - sp
chg_pct = (ep / sp - 1) * 100
all_hi = max(highs)
all_lo = min(lows)
r20_hi = max(highs[-20:])
r20_lo = min(lows[-20:])
vol_avg20 = sum(vols[-20:]) / 20
rsi_last = rsi14[-1] if rsi14[-1] is not None else 50
vol_today = vols[-1]
vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0
vol_vs_avg = "放量" if vol_ratio > 1.5 else ("缩量" if vol_ratio < 0.5 else "正常")

# Recent drop: from recent 5-day high to current close
recent_5_high = max(highs[-5:])
recent_drop_pct = (ep - recent_5_high) / recent_5_high * 100

last = N - 1

# ── Indicator states ──
if ma5[last] and ma10[last] and ma20[last]:
    if ma5[last] > ma10[last] > ma20[last]:
        ma_st = "多头排列▲"
        ma_st_class = "up"
        ma_st_color = "#e74c3c"
    elif ma5[last] < ma10[last] < ma20[last]:
        ma_st = "空头排列▼"
        ma_st_class = "down"
        ma_st_color = "#2ecc71"
    else:
        ma_st = "均线缠绕"
        ma_st_class = ""
        ma_st_color = "#f39c12"
else:
    ma_st = "—"
    ma_st_class = ""
    ma_st_color = "#6e7681"

ma5v = f"{ma5[last]:.2f}" if ma5[last] else "—"
ma10v = f"{ma10[last]:.2f}" if ma10[last] else "—"
ma20v = f"{ma20[last]:.2f}" if ma20[last] else "—"
ma10_int = f"{ma10[last]:.0f}" if ma10[last] else "—"
ma20_int = f"{ma20[last]:.0f}" if ma20[last] else "—"

if bb_upper[last]:
    c = closes[last]
    bu = bb_upper[last]
    bm = bb_mid[last]
    bl = bb_lower[last]
    if c > bu:
        bb_pos = "突破上轨"
        bb_sig = "超买"
    elif c > bm:
        bb_pos = "上轨~中轨"
        bb_sig = "偏强"
    elif c > bl:
        bb_pos = "中轨~下轨"
        bb_sig = "偏弱"
    else:
        bb_pos = "跌破下轨"
        bb_sig = "超卖"
else:
    bb_pos = bb_sig = "—"

if dif_[last] and dea_[last]:
    if dif_[last] > dea_[last]:
        macd_st = "多头 (DIF>DEA)"
        macd_st_class = "up"
        macd_st_color = "#e74c3c"
    else:
        macd_st = "空头 (DIF<DEA)"
        macd_st_class = "down"
        macd_st_color = "#2ecc71"
    if macd_hist[last] > macd_hist[last - 1]:
        macd_dir = "红柱扩大" if macd_hist[last] > 0 else "绿柱缩小"
    elif macd_hist[last] < macd_hist[last - 1]:
        macd_dir = "绿柱扩大" if macd_hist[last] < 0 else "红柱缩小"
    else:
        macd_dir = "持平"
else:
    macd_st = "—"
    macd_st_class = ""
    macd_st_color = "#6e7681"
    macd_dir = "—"

# RSI description
if rsi_last > 70:
    rsi_desc = "超买"
elif rsi_last < 30:
    rsi_desc = "超卖"
else:
    rsi_desc = "中性"

rsi_color = "#2ecc71" if rsi_last < 30 else "#e74c3c" if rsi_last > 70 else "#f39c12"

# Volume color
vol_color = "#2ecc71" if (vol_vs_avg == "放量" and pcts[-1] < 0) else "#f39c12"

# Recent 5-day summary
recent_days_desc = []
for r in rows[-5:]:
    c = r["pct_chg"]
    arrow = "▲" if c >= 0 else "▼"
    recent_days_desc.append(f'{r["date"]} {arrow}{abs(c):.1f}%')
recent_summary = " | ".join(recent_days_desc)


# ── Build all JS data as a single JSON object ──
data_obj = {
    "dates": dates, "opens": opens, "closes": closes,
    "highs": highs, "lows": lows, "vols": vols,
    "amounts": [round(a) for a in amounts], "pcts": pcts,
    "bbUpper": bb_upper, "bbMid": bb_mid, "bbLower": bb_lower,
    "dif": dif_, "dea": dea_, "macdHist": macd_hist,
    "ma5": ma5, "ma10": ma10, "ma20": ma20, "rsi14": rsi14,
    "allHi": all_hi, "allLo": all_lo, "r20Hi": r20_hi, "r20Lo": r20_lo,
    "gcMarkers": gc_markers, "dcMarkers": dc_markers,
}
data_json = json.dumps(data_obj, ensure_ascii=False, default=lambda x: None if x is None else x)


# ── Read template and replace placeholders ──
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    template = f.read()

replacements = {
    "__DATA_JSON__": data_json,
    "__DATE_FROM__": dates[0],
    "__DATE_TO__": dates[-1],
    "__N_DAYS__": str(N),
    "__END_PRICE__": f"{ep:.2f}",
    "__START_PRICE__": f"{sp:.2f}",
    "__CHG__": f"{'+' if chg >= 0 else ''}{chg:.2f}",
    "__CHG_PCT__": f"{'+' if chg_pct >= 0 else ''}{chg_pct:.2f}%",
    "__GAIN_PCT__": f"{'+' if chg_pct >= 0 else ''}{chg_pct:.0f}%",
    "__CHG_CLASS__": "up" if chg >= 0 else "down",
    "__PCT_CLASS__": "up" if chg_pct >= 0 else "down",
    "__ALL_HI__": f"{all_hi:.2f}",
    "__ALL_LO__": f"{all_lo:.2f}",
    "__MA_ST__": ma_st,
    "__MA_ST_CLASS__": ma_st_class,
    "__MA_ST_COLOR__": ma_st_color,
    "__MA5V__": ma5v,
    "__MA10V__": ma10v,
    "__MA20V__": ma20v,
    "__MA10_INT__": ma10_int,
    "__MA20_INT__": ma20_int,
    "__MACD_ST__": macd_st,
    "__MACD_ST_CLASS__": macd_st_class,
    "__MACD_ST_COLOR__": macd_st_color,
    "__MACD_DIR__": macd_dir,
    "__BB_POS__": bb_pos,
    "__BB_SIG__": bb_sig,
    "__LAST_GC__": last_gc,
    "__LAST_DC__": last_dc,
    "__RSI__": f"{rsi_last:.0f}",
    "__RSI_COLOR__": rsi_color,
    "__RSI_DESC__": rsi_desc,
    "__VOL_VS_AVG__": vol_vs_avg,
    "__VOL_TODAY__": f"{vol_today:.1f}",
    "__VOL_AVG__": f"{vol_avg20:.1f}",
    "__VOL_COLOR__": vol_color,
    "__RECENT_SUMMARY__": recent_summary,
    "__RECENT_DROP_PCT__": f"{recent_drop_pct:.1f}",
    "__DIF__": f"{dif_[last]:.2f}" if dif_[last] else "—",
    "__DEA__": f"{dea_[last]:.2f}" if dea_[last] else "—",
    "__MACD_HIST__": f"{macd_hist[last]:.2f}" if macd_hist[last] else "—",
    "__BB_UPPER__": f"{bb_upper[last]:.2f}" if bb_upper[last] else "—",
    "__BB_MID__": f"{bb_mid[last]:.2f}" if bb_mid[last] else "—",
    "__BB_LOWER__": f"{bb_lower[last]:.2f}" if bb_lower[last] else "—",
    "__BB_MID_INT__": f"{bb_mid[last]:.0f}" if bb_mid[last] else "—",
    "__BB_LOWER_INT__": f"{bb_lower[last]:.0f}" if bb_lower[last] else "—",
}

for key, val in replacements.items():
    template = template.replace(key, val)

# ── Verify no placeholders left ──
import re
leftover = re.findall(r"__[A-Z_]+__", template)
if leftover:
    print(f"[WARN] Unreplaced placeholders: {set(leftover)}")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(template)

print(f"[OK] {OUTPUT_PATH}")
print(f"  Days: {N}, {dates[0]} ~ {dates[-1]}")
print(f"  Close: {sp:.2f} -> {ep:.2f} ({'+'if chg>=0 else ''}{chg:.2f}, {'+'if chg_pct>=0 else ''}{chg_pct:.2f}%)")
print(f"  MA: {ma_st} ({ma5v}/{ma10v}/{ma20v})")
print(f"  MACD: DIF={dif_[last]:.2f} DEA={dea_[last]:.2f} Hist={macd_hist[last]:.2f} ({macd_dir})")
print(f"  RSI: {rsi_last:.0f} ({rsi_desc})")
print(f"  BB: {bb_pos} ({bb_sig})")
print(f"  Recent drop: {recent_drop_pct:.1f}%")
print(f"  GC markers: {len(gc_markers)}, DC markers: {len(dc_markers)}")
