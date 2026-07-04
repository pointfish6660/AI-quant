#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate K-line charts for 比亚迪 A+H (前复权)."""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data")
TP = os.path.join(HERE, "chart_template.html")

# ── Indicators ──
def sma(d,p):
    r=[None]*len(d)
    for i in range(p-1,len(d)): r[i]=sum(d[i-p+1:i+1])/p
    return r
def ema(d,p):
    a=2/(p+1); r=[None]*len(d)
    f=next(i for i,v in enumerate(d) if v is not None); r[f]=d[f]
    for i in range(f+1,len(d)): r[i]=a*d[i]+(1-a)*r[i-1]
    return r
def rstd(d,p):
    r=[None]*len(d)
    for i in range(p-1,len(d)):
        w=d[i-p+1:i+1]; m=sum(w)/p
        r[i]=(sum((x-m)**2 for x in w)/p)**0.5
    return r
def diff_fn(a,b): return [a[i]-b[i] if a[i] is not None and b[i] is not None else None for i in range(len(a))]
def mul(a,k): return [a[i]*k if a[i] is not None else None for i in range(len(a))]
def rsi(d,p=14):
    r=[None]*len(d); g=[]; l_=[]
    for i in range(1,len(d)):
        c=d[i]-d[i-1]; g.append(max(c,0)); l_.append(max(-c,0))
    for i in range(p-1,len(g)):
        ag=sum(g[i-p+1:i+1])/p; al=sum(l_[i-p+1:i+1])/p
        r[i+1]=100 if al==0 else round(100-100/(1+ag/al),2)
    return r
def find_cross(a,b):
    c=[]
    for i in range(1,len(a)):
        if any(x is None for x in [a[i],b[i],a[i-1],b[i-1]]): continue
        if a[i-1]<=b[i-1] and a[i]>b[i]: c.append((i,"gold"))
        elif a[i-1]>=b[i-1] and a[i]<b[i]: c.append((i,"death"))
    return c

def build(csv_path, out_path, code, curr, date_fmt):
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = r["trade_date"]
            dd = d if date_fmt == "%Y-%m-%d" else f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            rows.append(dict(date=dd, open=float(r["open"]), close=float(r["close"]),
                             high=float(r["high"]), low=float(r["low"]),
                             vol=float(r["vol"]), pct_chg=float(r["pct_chg"])))
    rows.sort(key=lambda x: x["date"]); N = len(rows)
    dates=[r["date"] for r in rows]; closes=[r["close"] for r in rows]
    highs=[r["high"] for r in rows]; lows=[r["low"] for r in rows]
    pcts=[r["pct_chg"] for r in rows]; opens=[r["open"] for r in rows]
    vols=[round(r["vol"]/10000,2) for r in rows]

    ma5,ma10,ma20=sma(closes,5),sma(closes,10),sma(closes,20)
    bm=ma20; bs=rstd(closes,20)
    bu=[bm[i]+2*bs[i] if bm[i] else None for i in range(N)]
    bl=[bm[i]-2*bs[i] if bm[i] else None for i in range(N)]
    e12,e26=ema(closes,12),ema(closes,26)
    di=diff_fn(e12,e26); de=ema(di,9); mh=mul(diff_fn(di,de),2)
    r14=rsi(closes)
    # KDJ
    K=[None]*N; D_=[None]*N; J=[None]*N
    for i in range(N):
        if i<8: continue
        hh=max(highs[i-8:i+1]); ll_=min(lows[i-8:i+1])
        rsv=50.0 if hh==ll_ else (closes[i]-ll_)/(hh-ll_)*100
        if i==8 or K[i-1] is None: K[i]=rsv; D_[i]=rsv
        else: K[i]=2/3*K[i-1]+1/3*rsv; D_[i]=2/3*D_[i-1]+1/3*K[i]
        J[i]=3*K[i]-2*D_[i]
    gc=find_cross(ma5,ma10)

    sp,ep=closes[0],closes[-1]; chg=ep-sp; cpct=(ep/sp-1)*100
    ah=max(highs); al_=min(lows); r20h=max(highs[-20:]); r20l=min(lows[-20:])
    l=N-1; va=sum(vols[-20:])/20; vt=vols[-1]; vr=vt/va if va else 0
    vvs="放量" if vr>1.5 else ("缩量" if vr<0.5 else "正常")

    ma5v=f"{ma5[l]:.2f}" if ma5[l] else "N/A"
    ma10v=f"{ma10[l]:.2f}" if ma10[l] else "N/A"
    ma20v=f"{ma20[l]:.2f}" if ma20[l] else "N/A"
    if ma5[l] and ma10[l] and ma20[l]:
        if ma5[l]>ma10[l]>ma20[l]: ms="多头排列"
        elif ma5[l]<ma10[l]<ma20[l]: ms="空头排列"
        else: ms="均线缠绕"
    else: ms="N/A"
    if bu[l]:
        c=closes[l]
        if c>bu[l]: bp,bsig="突破上轨","超买"
        elif c>bm[l]: bp,bsig="上轨~中轨","偏强"
        elif c>bl[l]: bp,bsig="中轨~下轨","偏弱"
        else: bp,bsig="跌破下轨","超卖"
    else: bp=bsig="N/A"
    if di[l] and de[l]:
        mst="多头" if di[l]>de[l] else "空头"
        md="红柱扩大" if mh[l]>mh[l-1] else ("绿柱扩大" if mh[l]<mh[l-1] else "持平")
    else: mst=md="N/A"
    rl_=r14[l] if r14[l] else 0
    rc="#2ecc71" if rl_<30 else "#e74c3c" if rl_>70 else "#f39c12"

    def lc(t):
        for i,tt in reversed(gc):
            if tt==t and i<N: return dates[i]
        return "N/A"
    lg,ld=lc("gold"),lc("death")
    rs=" | ".join(f'{r["date"]} {"+"if r["pct_chg"]>=0 else ""}{r["pct_chg"]:.2f}%' for r in rows[-5:])
    gm=[]; dm=[]
    for i,t in gc[-8:]:
        if t=="gold": gm.append([i,round(lows[i],2)])
        else: dm.append([i,round(highs[i],2)])

    dob={"dates":dates,"opens":[round(x,2) for x in opens],"closes":closes,"highs":highs,
         "lows":lows,"vols":vols,"pcts":pcts,"bbUpper":bu,"bbMid":bm,"bbLower":bl,
         "dif":di,"dea":de,"macdHist":mh,"ma5":ma5,"ma10":ma10,"ma20":ma20,"rsi14":r14,
         "allHi":ah,"allLo":al_,"r20Hi":r20h,"r20Lo":r20l,"gcMarkers":gm,"dcMarkers":dm,"kdjK":K,"kdjD":D_,"kdjJ":J}
    dj=json.dumps(dob,ensure_ascii=False,default=lambda x:None if x is None else x)

    with open(TP,"r",encoding="utf-8") as f: tpl=f.read()
    reps={"__DATA_JSON__":dj,"__DATE_FROM__":dates[0],"__DATE_TO__":dates[-1],
          "__N_DAYS__":str(N),"__END_PRICE__":f"{ep:.2f}","__START_PRICE__":f"{sp:.2f}",
          "__CHG__":f"{'+'if chg>=0 else ''}{chg:.2f}",
          "__CHG_PCT__":f"{'+'if cpct>=0 else ''}{cpct:.2f}%",
          "__CHG_CLASS__":"up" if chg>=0 else "down",
          "__PCT_CLASS__":"up" if cpct>=0 else "down",
          "__ALL_HI__":f"{ah:.2f}","__ALL_LO__":f"{al_:.2f}",
          "__MA_ST__":ms,"__MA5V__":ma5v,"__MA10V__":ma10v,"__MA20V__":ma20v,
          "__MACD_ST__":mst,"__MACD_DIR__":md,"__BB_POS__":bp,"__BB_SIG__":bsig,
          "__LAST_GC__":lg,"__LAST_DC__":ld,"__RSI__":f"{rl_:.0f}","__RSI_COLOR__":rc,
          "__VOL_VS_AVG__":vvs,"__VOL_TODAY__":f"{vt:.1f}","__VOL_AVG__":f"{va:.1f}",
          "__RECENT_SUMMARY__":rs,
          "__DIF__":f"{di[l]:.2f}" if di[l] else "N/A",
          "__DEA__":f"{de[l]:.2f}" if de[l] else "N/A",
          "__MACD_HIST__":f"{mh[l]:.2f}" if mh[l] else "N/A",
          "__BB_UPPER__":f"{bu[l]:.2f}" if bu[l] else "N/A",
          "__BB_MID__":f"{bm[l]:.2f}" if bm[l] else "N/A",
          "__BB_LOWER__":f"{bl[l]:.2f}" if bl[l] else "N/A",
          "__BB_MID_INT__":f"{bm[l]:.0f}" if bm[l] else "N/A",
          "__BB_LOWER_INT__":f"{bl[l]:.0f}" if bl[l] else "N/A",
          "__STOCK_NAME__":"比亚迪",
          "__STOCK_CODE__":code,
          "__KDJ_K__":f"{K[l]:.2f}" if K[l] is not None else "N/A",
          "__KDJ_D__":f"{D_[l]:.2f}" if D_[l] is not None else "N/A",
          "__KDJ_J__":f"{J[l]:.2f}" if J[l] is not None else "N/A"}
    for k,v in reps.items(): tpl=tpl.replace(k,str(v))
    os.makedirs(os.path.dirname(out_path),exist_ok=True)
    with open(out_path,"w",encoding="utf-8") as f: f.write(tpl)
    print(f"[OK] {out_path}  {sp:.2f}→{ep:.2f} ({chg:+.2f}, {cpct:+.2f}%)")

if __name__=="__main__":
    build(os.path.join(D,"byd_a_daily.csv"), os.path.join(ROOT,"outputs","byd_a_kline.html"), "002594.SZ", "¥", "%Y%m%d")
    build(os.path.join(D,"byd_hk_daily.csv"), os.path.join(ROOT,"outputs","byd_hk_kline.html"), "01211.HK", "HK$", "%Y-%m-%d")
