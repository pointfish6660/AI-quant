#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate comprehensive analysis page for 中际旭创 300308.SZ"""
import csv, json, os

CSV_PATH = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_data.csv")

rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        d = r["trade_date"]
        rows.append(dict(date=f"{d[:4]}-{d[4:6]}-{d[6:8]}",
                         open=float(r["open"]), close=float(r["close"]),
                         high=float(r["high"]), low=float(r["low"]),
                         vol=float(r["vol"]), amount=float(r["amount"]),
                         pct_chg=float(r["pct_chg"])))
rows.sort(key=lambda x: x["date"])
N = len(rows)

dates=[r["date"] for r in rows]; opens=[r["open"] for r in rows]
closes=[r["close"] for r in rows]; highs=[r["high"] for r in rows]
lows=[r["low"] for r in rows]; pcts=[r["pct_chg"] for r in rows]
vols=[round(r["vol"]/10000,2) for r in rows]
amounts=[round(r["amount"]/10000,2) for r in rows]

def sma(data, period):
    r=[None]*len(data)
    for i in range(period-1,len(data)):
        r[i]=sum(data[i-period+1:i+1])/period
    return r

def ema(data, period):
    a=2/(period+1); r=[None]*len(data)
    first=next(i for i,v in enumerate(data) if v is not None)
    r[first]=data[first]
    for i in range(first+1,len(data)):
        r[i]=a*data[i]+(1-a)*r[i-1]
    return r

def rstd(data, period):
    r=[None]*len(data)
    for i in range(period-1,len(data)):
        w=data[i-period+1:i+1]; m=sum(w)/period
        r[i]=(sum((x-m)**2 for x in w)/period)**0.5
    return r

def diff(a,b):
    return [a[i]-b[i] if a[i] is not None and b[i] is not None else None for i in range(len(a))]

def mult(a,k):
    return [a[i]*k if a[i] is not None else None for i in range(len(a))]

def rsi_calc(data, period=14):
    r=[None]*len(data); gains=[]; losses=[]
    for i in range(1,len(data)):
        c=data[i]-data[i-1]; gains.append(max(c,0)); losses.append(max(-c,0))
    for i in range(period-1,len(gains)):
        ag=sum(gains[i-period+1:i+1])/period
        al=sum(losses[i-period+1:i+1])/period
        r[i+1]=100 if al==0 else round(100-100/(1+ag/al),2)
    return r

ma5,ma10,ma20=sma(closes,5),sma(closes,10),sma(closes,20)
bb_mid=ma20; bb_std=rstd(closes,20)
bb_upper=[bb_mid[i]+2*bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
bb_lower=[bb_mid[i]-2*bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
ema12,ema26=ema(closes,12),ema(closes,26)
dif_=diff(ema12,ema26); dea_=ema(dif_,9); macd_hist=mult(diff(dif_,dea_),2)
rsi14=rsi_calc(closes,14)

def find_cross(a,b):
    c=[]
    for i in range(1,len(a)):
        if a[i] is None or b[i] is None or a[i-1] is None or b[i-1] is None: continue
        if a[i-1]<=b[i-1] and a[i]>b[i]: c.append((i,"gold"))
        elif a[i-1]>=b[i-1] and a[i]<b[i]: c.append((i,"death"))
    return c

gc_5_10=find_cross(ma5,ma10)

def last_cross_str(crosses, typ):
    for idx,t in reversed(crosses):
        if t==typ and idx<N: return dates[idx]
    return "—"

last_gc=last_cross_str(gc_5_10,"gold")
last_dc=last_cross_str(gc_5_10,"death")

sp=closes[0]; ep=closes[-1]; chg=ep-sp; chg_pct=(ep/sp-1)*100
all_hi=max(highs); all_lo=min(lows)
r20_hi=max(highs[-20:]); r20_lo=min(lows[-20:])
vol_avg20=sum(vols[-20:])/20; rsi_last=rsi14[-1] if rsi14[-1] is not None else 0
vol_today=vols[-1]; vol_ratio=vol_today/vol_avg20 if vol_avg20>0 else 0
vol_vs_avg="放量" if vol_ratio>1.5 else ("缩量" if vol_ratio<0.5 else "正常")

last=N-1
if ma5[last] and ma10[last] and ma20[last]:
    ma_st="多头排列▲" if ma5[last]>ma10[last]>ma20[last] else ("空头排列▼" if ma5[last]<ma10[last]<ma20[last] else "均线缠绕")
else: ma_st="—"
ma5v=f"{ma5[last]:.2f}" if ma5[last] else "—"
ma10v=f"{ma10[last]:.2f}" if ma10[last] else "—"
ma20v=f"{ma20[last]:.2f}" if ma20[last] else "—"

if bb_upper[last]:
    c=closes[last]; bu=bb_upper[last]; bm=bb_mid[last]; bl=bb_lower[last]
    if c>bu: bb_pos="突破上轨"; bb_sig="超买"
    elif c>bm: bb_pos="上轨~中轨"; bb_sig="偏强"
    elif c>bl: bb_pos="中轨~下轨"; bb_sig="偏弱"
    else: bb_pos="跌破下轨"; bb_sig="超卖"
else: bb_pos=bb_sig="—"

if dif_[last] and dea_[last]:
    macd_st="多头 (DIF>DEA)" if dif_[last]>dea_[last] else "空头 (DIF<DEA)"
    macd_dir="红柱扩大" if macd_hist[last]>macd_hist[last-1] else ("绿柱扩大" if macd_hist[last]<macd_hist[last-1] else "持平")
else: macd_st=macd_dir="—"

recent_days_desc=[]
for r in rows[-5:]:
    c=r["pct_chg"]; arrow="▲" if c>=0 else "▼"
    recent_days_desc.append(f'{r["date"]} {arrow}{abs(c):.1f}%')
recent_summary=" | ".join(recent_days_desc)

# Build golden/death cross marker arrays for JS
gc_markers=[]
dc_markers=[]
for idx,typ in gc_5_10[-8:]:
    if typ=="gold":
        gc_markers.append([idx, round(lows[idx],2)])
    else:
        dc_markers.append([idx, round(highs[idx],2)])

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

# ── Read template ──
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "chart_template.html")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    template = f.read()

# Replace placeholders
template = template.replace("__DATA_JSON__", data_json)
template = template.replace("__DATE_FROM__", dates[0])
template = template.replace("__DATE_TO__", dates[-1])
template = template.replace("__N_DAYS__", str(N))
template = template.replace("__END_PRICE__", f"{ep:.2f}")
template = template.replace("__START_PRICE__", f"{sp:.2f}")
template = template.replace("__CHG__", f"{'+'if chg>=0 else ''}{chg:.2f}")
template = template.replace("__CHG_PCT__", f"{'+'if chg_pct>=0 else ''}{chg_pct:.2f}%")
template = template.replace("__CHG_CLASS__", "up" if chg>=0 else "down")
template = template.replace("__PCT_CLASS__", "up" if chg_pct>=0 else "down")
template = template.replace("__ALL_HI__", f"{all_hi:.2f}")
template = template.replace("__ALL_LO__", f"{all_lo:.2f}")
template = template.replace("__MA_ST__", ma_st)
template = template.replace("__MA5V__", ma5v)
template = template.replace("__MA10V__", ma10v)
template = template.replace("__MA20V__", ma20v)
template = template.replace("__MACD_ST__", macd_st)
template = template.replace("__MACD_DIR__", macd_dir)
template = template.replace("__BB_POS__", bb_pos)
template = template.replace("__BB_SIG__", bb_sig)
template = template.replace("__LAST_GC__", last_gc)
template = template.replace("__LAST_DC__", last_dc)
template = template.replace("__RSI__", f"{rsi_last:.0f}")
template = template.replace("__RSI_COLOR__", "#2ecc71" if rsi_last<30 else "#e74c3c" if rsi_last>70 else "#f39c12")
template = template.replace("__VOL_VS_AVG__", vol_vs_avg)
template = template.replace("__VOL_TODAY__", f"{vol_today:.1f}")
template = template.replace("__VOL_AVG__", f"{vol_avg20:.1f}")
template = template.replace("__RECENT_SUMMARY__", recent_summary)
template = template.replace("__DIF__", f"{dif_[last]:.2f}" if dif_[last] else "—")
template = template.replace("__DEA__", f"{dea_[last]:.2f}" if dea_[last] else "—")
template = template.replace("__MACD_HIST__", f"{macd_hist[last]:.2f}" if macd_hist[last] else "—")
template = template.replace("__BB_UPPER__", f"{bb_upper[last]:.2f}" if bb_upper[last] else "—")
template = template.replace("__BB_MID__", f"{bb_mid[last]:.2f}" if bb_mid[last] else "—")
template = template.replace("__BB_LOWER__", f"{bb_lower[last]:.2f}" if bb_lower[last] else "—")
template = template.replace("__BB_MID_INT__", f"{bb_mid[last]:.0f}" if bb_mid[last] else "—")
template = template.replace("__BB_LOWER_INT__", f"{bb_lower[last]:.0f}" if bb_lower[last] else "—")

OUT = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_chart.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(template)

print(f"[OK] {OUT}")
print(f"  Days: {N}, {dates[0]} ~ {dates[-1]}")
print(f"  Close: {sp:.2f} -> {ep:.2f} ({chg:+.2f}, {chg_pct:+.2f}%)")
print(f"  MA: {ma_st} ({ma5v}/{ma10v}/{ma20v})")
print(f"  MACD: DIF={dif_[last]:.2f} DEA={dea_[last]:.2f} Hist={macd_hist[last]:.2f}")
print(f"  GC markers: {len(gc_markers)}, DC markers: {len(dc_markers)}")
