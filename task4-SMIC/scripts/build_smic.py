#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate K-line charts for 中芯国际 A+H.

Output:
  - outputs/smic_a_kline.html  (A股 688981.SH)
  - outputs/smic_hk_kline.html (港股 00981.HK)
"""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
TEMPLATE_PATH = os.path.join(HERE, "chart_template.html")

# ── Technical indicators (reused from task6) ──
def sma(data, period):
    r = [None] * len(data)
    for i in range(period - 1, len(data)):
        r[i] = sum(data[i - period + 1:i + 1]) / period
    return r

def ema(data, period):
    a = 2 / (period + 1); r = [None] * len(data)
    first = next(i for i, v in enumerate(data) if v is not None)
    r[first] = data[first]
    for i in range(first + 1, len(data)):
        r[i] = a * data[i] + (1 - a) * r[i - 1]
    return r

def rstd(data, period):
    r = [None] * len(data)
    for i in range(period - 1, len(data)):
        w = data[i - period + 1:i + 1]; m = sum(w) / period
        r[i] = (sum((x - m) ** 2 for x in w) / period) ** 0.5
    return r

def diff(a, b):
    return [a[i] - b[i] if a[i] is not None and b[i] is not None else None for i in range(len(a))]

def mult(a, k):
    return [a[i] * k if a[i] is not None else None for i in range(len(a))]

def rsi_calc(data, period=14):
    r = [None] * len(data); gains = []; losses = []
    for i in range(1, len(data)):
        c = data[i] - data[i-1]; gains.append(max(c, 0)); losses.append(max(-c, 0))
    for i in range(period - 1, len(gains)):
        ag = sum(gains[i - period + 1:i + 1]) / period
        al = sum(losses[i - period + 1:i + 1]) / period
        r[i + 1] = 100 if al == 0 else round(100 - 100 / (1 + ag / al), 2)
    return r

def find_cross(a, b):
    c = []
    for i in range(1, len(a)):
        if a[i] is None or b[i] is None or a[i-1] is None or b[i-1] is None: continue
        if a[i-1] <= b[i-1] and a[i] > b[i]: c.append((i, "gold"))
        elif a[i-1] >= b[i-1] and a[i] < b[i]: c.append((i, "death"))
    return c


def build_chart(csv_path, output_path, name, code, currency="¥", date_fmt="%Y%m%d"):
    """Generate a single K-line chart HTML."""
    # Load data
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = r["trade_date"]
            if date_fmt == "%Y-%m-%d":
                date_display = d
            else:
                date_display = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            rows.append(dict(date=date_display,
                             open=float(r["open"]), close=float(r["close"]),
                             high=float(r["high"]), low=float(r["low"]),
                             vol=float(r["vol"]), amount=float(r["amount"]),
                             pct_chg=float(r["pct_chg"])))
    rows.sort(key=lambda x: x["date"])
    N = len(rows)

    dates = [r["date"] for r in rows]
    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    pcts = [r["pct_chg"] for r in rows]
    opens = [r["open"] for r in rows]
    vols = [round(r["vol"] / 10000, 2) for r in rows]

    # Indicators
    ma5, ma10, ma20 = sma(closes, 5), sma(closes, 10), sma(closes, 20)
    bb_mid = ma20; bb_std = rstd(closes, 20)
    bb_upper = [bb_mid[i] + 2 * bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
    bb_lower = [bb_mid[i] - 2 * bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
    ema12, ema26 = ema(closes, 12), ema(closes, 26)
    dif_ = diff(ema12, ema26); dea_ = ema(dif_, 9)
    macd_hist = mult(diff(dif_, dea_), 2)
    rsi14 = rsi_calc(closes, 14)
    # KDJ
    kdjK = [None] * N; kdjD = [None] * N; kdjJ = [None] * N
    for i in range(N):
        if i < 8: continue
        hh = max(highs[i-8:i+1]); ll_ = min(lows[i-8:i+1])
        rsv = 50.0 if hh == ll_ else (closes[i] - ll_) / (hh - ll_) * 100
        if i == 8 or kdjK[i-1] is None:
            kdjK[i] = rsv; kdjD[i] = rsv
        else:
            kdjK[i] = 2/3 * kdjK[i-1] + 1/3 * rsv
            kdjD[i] = 2/3 * kdjD[i-1] + 1/3 * kdjK[i]
        kdjJ[i] = 3 * kdjK[i] - 2 * kdjD[i]
    gc_5_10 = find_cross(ma5, ma10)

    # Stats
    sp, ep = closes[0], closes[-1]
    chg = ep - sp; chg_pct = (ep / sp - 1) * 100
    all_hi = max(highs); all_lo = min(lows)
    r20_hi = max(highs[-20:]); r20_lo = min(lows[-20:])
    vol_avg20 = sum(vols[-20:]) / 20
    rsi_last = rsi14[-1] if rsi14[-1] is not None else 0
    last = N - 1

    ma5v = f"{ma5[last]:.2f}" if ma5[last] else "N/A"
    ma10v = f"{ma10[last]:.2f}" if ma10[last] else "N/A"
    ma20v = f"{ma20[last]:.2f}" if ma20[last] else "N/A"

    if ma5[last] and ma10[last] and ma20[last]:
        if ma5[last] > ma10[last] > ma20[last]: ma_st = "多头排列"
        elif ma5[last] < ma10[last] < ma20[last]: ma_st = "空头排列"
        else: ma_st = "均线缠绕"
    else: ma_st = "N/A"

    if bb_upper[last]:
        c = closes[last]; bu, bm, bl = bb_upper[last], bb_mid[last], bb_lower[last]
        if c > bu: bb_pos, bb_sig = "突破上轨", "超买"
        elif c > bm: bb_pos, bb_sig = "上轨~中轨", "偏强"
        elif c > bl: bb_pos, bb_sig = "中轨~下轨", "偏弱"
        else: bb_pos, bb_sig = "跌破下轨", "超卖"
    else: bb_pos = bb_sig = "N/A"

    if dif_[last] and dea_[last]:
        macd_st = "多头" if dif_[last] > dea_[last] else "空头"
        macd_dir = "红柱扩大" if macd_hist[last] > macd_hist[last-1] else ("绿柱扩大" if macd_hist[last] < macd_hist[last-1] else "持平")
    else: macd_st = macd_dir = "N/A"

    vol_today = vols[-1]
    vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0
    vol_vs_avg = "放量" if vol_ratio > 1.5 else ("缩量" if vol_ratio < 0.5 else "正常")
    rsi_color = "#2ecc71" if rsi_last < 30 else "#e74c3c" if rsi_last > 70 else "#f39c12"

    def lc(typ):
        for idx, t in reversed(gc_5_10):
            if t == typ and idx < N: return dates[idx]
        return "N/A"

    last_gc = lc("gold"); last_dc = lc("death")
    recent_summary = " | ".join(
        f'{r["date"]} {"+"if r["pct_chg"]>=0 else ""}{r["pct_chg"]:.2f}%'
        for r in rows[-5:])

    gc_markers = []; dc_markers = []
    for idx, typ in gc_5_10[-8:]:
        if typ == "gold": gc_markers.append([idx, round(lows[idx], 2)])
        else: dc_markers.append([idx, round(highs[idx], 2)])

    data_obj = {
        "dates": dates, "opens": [round(x,2) for x in opens], "closes": closes,
        "highs": highs, "lows": lows, "vols": vols, "pcts": pcts,
        "bbUpper": bb_upper, "bbMid": bb_mid, "bbLower": bb_lower,
        "dif": dif_, "dea": dea_, "macdHist": macd_hist,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "rsi14": rsi14,
        "allHi": all_hi, "allLo": all_lo, "r20Hi": r20_hi, "r20Lo": r20_lo,
        "gcMarkers": gc_markers, "dcMarkers": dc_markers,
        "kdjK": kdjK, "kdjD": kdjD, "kdjJ": kdjJ,
    }
    data_json = json.dumps(data_obj, ensure_ascii=False, default=lambda x: None if x is None else x)

    # Read template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()

    # Standard placeholders
    reps = {
        "__DATA_JSON__": data_json, "__DATE_FROM__": dates[0],
        "__DATE_TO__": dates[-1], "__N_DAYS__": str(N),
        "__END_PRICE__": f"{ep:.2f}", "__START_PRICE__": f"{sp:.2f}",
        "__CHG__": f"{'+'if chg>=0 else ''}{chg:.2f}",
        "__CHG_PCT__": f"{'+'if chg_pct>=0 else ''}{chg_pct:.2f}%",
        "__CHG_CLASS__": "up" if chg >= 0 else "down",
        "__PCT_CLASS__": "up" if chg_pct >= 0 else "down",
        "__ALL_HI__": f"{all_hi:.2f}", "__ALL_LO__": f"{all_lo:.2f}",
        "__MA_ST__": ma_st, "__MA5V__": ma5v, "__MA10V__": ma10v, "__MA20V__": ma20v,
        "__MACD_ST__": macd_st, "__MACD_DIR__": macd_dir,
        "__BB_POS__": bb_pos, "__BB_SIG__": bb_sig,
        "__LAST_GC__": last_gc, "__LAST_DC__": last_dc,
        "__RSI__": f"{rsi_last:.0f}", "__RSI_COLOR__": rsi_color,
        "__VOL_VS_AVG__": vol_vs_avg,
        "__VOL_TODAY__": f"{vol_today:.1f}", "__VOL_AVG__": f"{vol_avg20:.1f}",
        "__RECENT_SUMMARY__": recent_summary,
        "__DIF__": f"{dif_[last]:.2f}" if dif_[last] else "N/A",
        "__DEA__": f"{dea_[last]:.2f}" if dea_[last] else "N/A",
        "__MACD_HIST__": f"{macd_hist[last]:.2f}" if macd_hist[last] else "N/A",
        "__BB_UPPER__": f"{bb_upper[last]:.2f}" if bb_upper[last] else "N/A",
        "__BB_MID__": f"{bb_mid[last]:.2f}" if bb_mid[last] else "N/A",
        "__BB_LOWER__": f"{bb_lower[last]:.2f}" if bb_lower[last] else "N/A",
        "__BB_MID_INT__": f"{bb_mid[last]:.0f}" if bb_mid[last] else "N/A",
        "__BB_LOWER_INT__": f"{bb_lower[last]:.0f}" if bb_lower[last] else "N/A",
        "__STOCK_NAME__": name,
        "__STOCK_CODE__": code,
        "__KDJ_K__": f"{kdjK[last]:.2f}" if kdjK[last] is not None else "N/A",
        "__KDJ_D__": f"{kdjD[last]:.2f}" if kdjD[last] is not None else "N/A",
        "__KDJ_J__": f"{kdjJ[last]:.2f}" if kdjJ[last] is not None else "N/A",
    }
    for k, v in reps.items():
        tpl = tpl.replace(k, str(v))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tpl)

    print(f"[OK] {output_path}")
    print(f"  {name} ({code}): {sp:.2f} → {ep:.2f} ({chg:+.2f}, {chg_pct:+.2f}%)")

    return output_path


def main():
    # A-share chart
    build_chart(
        os.path.join(DATA_DIR, "smic_a_daily.csv"),
        os.path.join(ROOT, "outputs", "smic_a_kline.html"),
        "中芯国际 A股", "688981.SH", "¥", "%Y%m%d"
    )

    # HK-share chart
    build_chart(
        os.path.join(DATA_DIR, "smic_hk_daily.csv"),
        os.path.join(ROOT, "outputs", "smic_hk_kline.html"),
        "中芯国际 港股", "00981.HK", "HK$", "%Y-%m-%d"
    )


if __name__ == "__main__":
    main()
