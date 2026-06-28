#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive analysis page for 中际旭创 300308.SZ
Includes: trading advice, K-line + MACD + BB + indicators, educational content, deep analysis.
"""
import csv, json, os, math

CSV_PATH = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_data.csv")

# ── Read data ──
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

dates   = [r["date"]   for r in rows]
opens   = [r["open"]   for r in rows]
closes  = [r["close"]  for r in rows]
highs   = [r["high"]   for r in rows]
lows    = [r["low"]    for r in rows]
vols    = [round(r["vol"]/10000,2)   for r in rows]
amounts = [round(r["amount"]/10000,2) for r in rows]
pcts    = [r["pct_chg"] for r in rows]

# ── Helpers ──
def js(a, prec=2):
    if a and isinstance(a[0], str):
        return "[" + ",".join(f'"{v}"' for v in a) + "]"
    return "[" + ",".join(f"{v:.{prec}f}" if prec else str(v) for v in a) + "]"

def js_nullable(a, prec=2):
    def fmt(v):
        if v is None: return "null"
        if isinstance(v, (int, float)): return f"{v:.{prec}f}" if prec else str(v)
        return f'"{v}"'
    return "[" + ",".join(fmt(v) for v in a) + "]"

def sma(data, period):
    r = [None] * len(data)
    for i in range(period-1, len(data)):
        r[i] = sum(data[i-period+1:i+1]) / period
    return r

def ema(data, period):
    alpha = 2/(period+1)
    r = [None] * len(data)
    first = next(i for i, v in enumerate(data) if v is not None)
    r[first] = data[first]
    for i in range(first+1, len(data)):
        r[i] = alpha * data[i] + (1-alpha) * r[i-1]
    return r

def rolling_std(data, period):
    r = [None] * len(data)
    for i in range(period-1, len(data)):
        win = data[i-period+1:i+1]
        m = sum(win)/period
        r[i] = (sum((x-m)**2 for x in win)/period) ** 0.5
    return r

def diff(a, b):
    return [a[i]-b[i] if a[i] is not None and b[i] is not None else None for i in range(len(a))]

def mult(a, k):
    return [a[i]*k if a[i] is not None else None for i in range(len(a))]

def rsi(data, period=14):
    r = [None] * len(data)
    gains, losses = [], []
    for i in range(1, len(data)):
        chg = data[i] - data[i-1]
        gains.append(max(chg, 0))
        losses.append(max(-chg, 0))
    for i in range(period-1, len(gains)):
        avg_gain = sum(gains[i-period+1:i+1]) / period
        avg_loss = sum(losses[i-period+1:i+1]) / period
        if avg_loss == 0:
            r[i+1] = 100
        else:
            rsi_val = 100 - 100 / (1 + avg_gain / avg_loss)
            r[i+1] = round(rsi_val, 2)
    return r

# ── Indicators ──
ma5, ma10, ma20 = sma(closes,5), sma(closes,10), sma(closes,20)
bb_mid = ma20
bb_std = rolling_std(closes, 20)
bb_upper = [bb_mid[i]+2*bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
bb_lower = [bb_mid[i]-2*bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
ema12, ema26 = ema(closes,12), ema(closes,26)
dif_ = diff(ema12, ema26)
dea_ = ema(dif_, 9)
macd_hist = mult(diff(dif_, dea_), 2)
rsi14 = rsi(closes, 14)

# ── Cross detection ──
def find_cross(a, b):
    c = []
    for i in range(1, len(a)):
        if a[i] is None or b[i] is None or a[i-1] is None or b[i-1] is None: continue
        if a[i-1] <= b[i-1] and a[i] > b[i]: c.append((i, "gold"))
        elif a[i-1] >= b[i-1] and a[i] < b[i]: c.append((i, "death"))
    return c

gc_5_10 = find_cross(ma5, ma10)

def gc_data(crosses, typ):
    items = []
    for idx, t in crosses:
        if t == typ:
            items.append(f"[{idx},{round(lows[idx] if typ=='gold' else highs[idx],2)}]")
    return "[" + ",".join(items) + "]" if items else "[]"

gc5_10_js = gc_data([x for x in gc_5_10 if x[1]=="gold"], "gold")
dc5_10_js = gc_data([x for x in gc_5_10 if x[1]=="death"], "death")

def last_cross_str(crosses, typ):
    for idx, t in reversed(crosses):
        if t == typ and idx < N: return dates[idx]
    return "—"

last_gc = last_cross_str(gc_5_10, "gold")
last_dc = last_cross_str(gc_5_10, "death")

# ── Analysis metrics ──
sp = closes[0]; ep = closes[-1]; chg = ep - sp; chg_pct = (ep/sp-1)*100
all_hi = max(highs); all_lo = min(lows)
r20_hi = max(highs[-20:]); r20_lo = min(lows[-20:])
vol_avg20 = sum(vols[-20:])/20
rsi_last = rsi14[-1] if rsi14[-1] is not None else 0

# MA status
last = N-1
if ma5[last] and ma10[last] and ma20[last]:
    if ma5[last] > ma10[last] > ma20[last]: ma_st = "多头排列▲"
    elif ma5[last] < ma10[last] < ma20[last]: ma_st = "空头排列▼"
    else: ma_st = "均线缠绕"
else: ma_st = "—"
ma5v = f"{ma5[last]:.2f}" if ma5[last] else "—"
ma10v= f"{ma10[last]:.2f}" if ma10[last] else "—"
ma20v= f"{ma20[last]:.2f}" if ma20[last] else "—"

# BB position
if bb_upper[last]:
    c, bu, bm, bl = closes[last], bb_upper[last], bb_mid[last], bb_lower[last]
    if c > bu: bb_pos = "突破上轨"; bb_sig = "超买"
    elif c > bm: bb_pos = "上轨~中轨"; bb_sig = "偏强"
    elif c > bl: bb_pos = "中轨~下轨"; bb_sig = "偏弱"
    else: bb_pos = "跌破下轨"; bb_sig = "超卖"
else: bb_pos = bb_sig = "—"

# MACD status
if dif_[last] and dea_[last]:
    if dif_[last] > dea_[last]: macd_st = "多头 (DIF>DEA)"
    else: macd_st = "空头 (DIF<DEA)"
    macd_dir = "红柱扩大" if macd_hist[last] > macd_hist[last-1] else ("绿柱扩大" if macd_hist[last] < macd_hist[last-1] else "持平")
else: macd_st = macd_dir = "—"

# Recent price action
recent_days_desc = []
for r in rows[-5:]:
    c = r["pct_chg"]
    arrow = "▲" if c>=0 else "▼"
    recent_days_desc.append(f'{r["date"]} {arrow}{abs(c):.1f}%')
recent_summary = " | ".join(recent_days_desc)

# Volume analysis
vol_ratio = vols[-1]/vol_avg20 if vol_avg20 > 0 else 0
vol_vs_avg = "放量" if vol_ratio > 1.5 else ("缩量" if vol_ratio < 0.5 else "正常")
vol_today = vols[-1]

# ── JS data ──
js_vars = "\n".join([
    f"var dates={js(dates)};",
    f"var opens={js(opens)}; var closes={js(closes)}; var highs={js(highs)}; var lows={js(lows)};",
    f"var vols={js(vols)}; var amounts={js(amounts,0)}; var pcts={js(pcts)};",
    f"var bbUpper={js_nullable(bb_upper)}; var bbMid={js_nullable(bb_mid)}; var bbLower={js_nullable(bb_lower)};",
    f"var dif={js_nullable(dif_)}; var dea={js_nullable(dea_)}; var macdHist={js_nullable(macd_hist,4)};",
    f"var ma5={js_nullable(ma5)}; var ma10={js_nullable(ma10)}; var ma20={js_nullable(ma20)};",
    f"var rsi14={js_nullable(rsi14)};",
    f"var allHi={all_hi}; var allLo={all_lo}; var r20Hi={r20_hi}; var r20Lo={r20_lo};",
])

# ── CHART HTML snippet ──
CHART_HTML = """<script>
var UP="#e74c3c",DOWN="#2ecc71",ZS=50,ZE=100;
var kl=[];
for(var i=0;i<dates.length;i++)kl.push([opens[i],closes[i],lows[i],highs[i]]);

var kch=echarts.init(document.getElementById("kline-chart"));
kch.setOption({
  backgroundColor:"#161b22",
  tooltip:{trigger:"axis",axisPointer:{type:"cross"},backgroundColor:"rgba(13,17,23,0.96)",borderColor:"#21262d",textStyle:{color:"#c9d1d9",fontSize:13},
    formatter:function(ps){var i=ps[0].dataIndex,c=pcts[i],col=c>=0?UP:DOWN;
      var s='<div style="font-size:13px;line-height:2"><b>'+dates[i]+'</b><br>';
      s+='O <b>'+opens[i].toFixed(2)+'</b> H <b style="color:'+UP+'">'+highs[i].toFixed(2)+'</b><br>';
      s+='L <b style="color:'+DOWN+'">'+lows[i].toFixed(2)+'</b> C <b style="color:'+col+';font-size:15px">'+closes[i].toFixed(2)+'</b><br>';
      s+='涨跌 <b style="color:'+col+'">'+(c>=0?"+":"")+c.toFixed(2)+'%</b><br>';
      if(bbUpper[i]!=null)s+='BB上'+bbUpper[i].toFixed(2)+' 中'+bbMid[i].toFixed(2)+' 下'+bbLower[i].toFixed(2)+'<br>';
      if(dif[i]!=null)s+='DIF '+dif[i].toFixed(2)+' DEA '+dea[i].toFixed(2);
      return s+'</div>';}}},
  legend:{data:["K线","MA5","MA10","MA20","BB上轨","BB下轨"],top:4,left:50,textStyle:{color:"#6e7681",fontSize:11},itemWidth:18,itemHeight:10},
  grid:{left:"7%",right:"3%",top:42,bottom:8},
  xAxis:{type:"category",data:dates,axisLine:{lineStyle:{color:"#21262d"}},axisLabel:{color:"#484f58",fontSize:10,formatter:function(v){return v.substring(5);},rotate:45},axisTick:{show:false},splitLine:{show:false}},
  yAxis:{type:"value",name:"价格 (¥)",nameTextStyle:{color:"#484f58",fontSize:11},scale:true,splitLine:{lineStyle:{color:"#21262d",type:"dashed"}},axisLabel:{color:"#484f58",fontSize:11,formatter:"¥{value}"},axisLine:{show:false}},
  dataZoom:[{type:"inside",start:ZS,end:ZE,xAxisIndex:0},{type:"slider",start:ZS,end:ZE,height:0,bottom:0}],
  series:[
    {name:"K线",type:"candlestick",data:kl,itemStyle:{color:UP,color0:DOWN,borderColor:UP,borderColor0:DOWN,borderWidth:1}},
    {name:"MA5",type:"line",data:ma5,symbol:"none",lineStyle:{width:1.2,color:"#e67e22"}},
    {name:"MA10",type:"line",data:ma10,symbol:"none",lineStyle:{width:1.2,color:"#a29bfe"}},
    {name:"MA20",type:"line",data:ma20,symbol:"none",lineStyle:{width:1.5,color:"#1abc9c"}},
    {name:"BB上轨",type:"line",data:bbUpper,symbol:"none",lineStyle:{width:1,color:"#f39c12",type:"dashed"}},
    {name:"BB下轨",type:"line",data:bbLower,symbol:"none",lineStyle:{width:1,color:"#f39c12",type:"dashed"}},
    {name:"BB中轨",type:"line",data:bbMid,symbol:"none",lineStyle:{width:0.8,color:"#f39c12"}},
    {name:"金叉",type:"scatter",data:GC5_10,symbol:"triangle",symbolSize:14,itemStyle:{color:"#e74c3c"},z:10,label:{show:true,position:"bottom",color:"#e74c3c",fontSize:9,formatter:"金"}},
    {name:"死叉",type:"scatter",data:DC5_10,symbol:"triangle",symbolRotate:180,symbolSize:14,itemStyle:{color:"#2ecc71"},z:10,label:{show:true,position:"top",color:"#2ecc71",fontSize:9,formatter:"死"}},
    {name:"阻",type:"line",markLine:{silent:true,symbol:"none",lineStyle:{color:"#e74c3c",type:"dashed",width:1},label:{color:"#e74c3c",fontSize:10},data:[{yAxis:R20HI,name:"阻"+R20HI},{yAxis:ALLHI,name:"历史高"+ALLHI}]}},
    {name:"支",type:"line",markLine:{silent:true,symbol:"none",lineStyle:{color:"#2ecc71",type:"dashed",width:1},label:{color:"#2ecc71",fontSize:10},data:[{yAxis:R20LO,name:"支"+R20LO},{yAxis:ALLLO,name:"历史低"+ALLLO}]}}]});

var vch=echarts.init(document.getElementById("vol-chart"));
vch.setOption({
  backgroundColor:"#161b22",
  tooltip:{trigger:"axis",backgroundColor:"rgba(13,17,23,0.96)",borderColor:"#21262d",textStyle:{color:"#c9d1d9",fontSize:12},formatter:function(ps){var i=ps[0].dataIndex;return dates[i]+"<br>成交量 <b>"+vols[i].toFixed(2)+"</b> 万手";}},
  grid:{left:"7%",right:"3%",top:6,bottom:22},
  xAxis:{type:"category",data:dates,axisLabel:{show:false},axisLine:{lineStyle:{color:"#21262d"}},axisTick:{show:false},splitLine:{show:false}},
  yAxis:{type:"value",name:"万手",nameTextStyle:{color:"#484f58",fontSize:11},splitLine:{lineStyle:{color:"#21262d",type:"dashed"}},axisLabel:{color:"#484f58",fontSize:10},axisLine:{show:false}},
  dataZoom:[{type:"inside",start:ZS,end:ZE,xAxisIndex:0},{type:"slider",start:ZS,end:ZE,height:18,bottom:2}],
  series:[{type:"bar",data:vols.map(function(v,i){return{value:v,itemStyle:{color:pcts[i]>=0?"rgba(231,76,60,0.65)":"rgba(46,204,113,0.65)"}};}),barWidth:"60%"}]});

var mch=echarts.init(document.getElementById("macd-chart"));
mch.setOption({
  backgroundColor:"#161b22",
  tooltip:{trigger:"axis",backgroundColor:"rgba(13,17,23,0.96)",borderColor:"#21262d",textStyle:{color:"#c9d1d9",fontSize:12},formatter:function(ps){var i=ps[0].dataIndex;if(dif[i]==null)return"";return dates[i]+"<br>DIF <b style='color:#e67e22'>"+dif[i].toFixed(2)+"</b> DEA <b style='color:#3498db'>"+dea[i].toFixed(2)+"</b><br>MACD <b style='color:"+(macdHist[i]>=0?"#e74c3c":"#2ecc71")+"'>"+macdHist[i].toFixed(2)+"</b>";}},
  legend:{data:["MACD柱","DIF","DEA"],top:4,left:50,textStyle:{color:"#6e7681",fontSize:11},itemWidth:18,itemHeight:10},
  grid:{left:"7%",right:"3%",top:36,bottom:24},
  xAxis:{type:"category",data:dates,axisLine:{lineStyle:{color:"#21262d"}},axisLabel:{color:"#484f58",fontSize:9,formatter:function(v){return v.substring(5);},rotate:45},axisTick:{show:false},splitLine:{show:false}},
  yAxis:{type:"value",name:"MACD",nameTextStyle:{color:"#484f58",fontSize:11},splitLine:{lineStyle:{color:"#21262d",type:"dashed"}},axisLabel:{color:"#484f58",fontSize:10},axisLine:{show:false}},
  dataZoom:[{type:"inside",start:ZS,end:ZE,xAxisIndex:0},{type:"slider",start:ZS,end:ZE,height:18,bottom:2}],
  series:[
    {name:"MACD柱",type:"bar",data:macdHist.map(function(v,i){if(v==null)return 0;return{value:v,itemStyle:{color:v>=0?"rgba(231,76,60,0.6)":"rgba(46,204,113,0.6)"}};}),barWidth:"60%"},
    {name:"DIF",type:"line",data:dif,symbol:"none",lineStyle:{width:1.2,color:"#e67e22"}},
    {name:"DEA",type:"line",data:dea,symbol:"none",lineStyle:{width:1.2,color:"#3498db"}}]});

kch.group="sync";vch.group="sync";mch.group="sync";echarts.connect("sync");
window.addEventListener("resize",function(){kch.resize();vch.resize();mch.resize();});
</script>"""

# Replace chart placeholders
Chart1 = CHART_HTML
Chart1 = Chart1.replace("GC5_10", gc5_10_js).replace("DC5_10", dc5_10_js)
Chart1 = Chart1.replace("R20HI", f"{r20_hi:.0f}").replace("R20LO", f"{r20_lo:.0f}")
Chart1 = Chart1.replace("ALLHI", f"{all_hi:.0f}").replace("ALLLO", f"{all_lo:.0f}")

# ── Build full HTML ──
# Strategy: write template with %%PLACEHOLDER%% markers, then replace
html_parts = []

# CSS
html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中际旭创 (300308.SZ) 深度分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#0d1117;color:#c9d1d9;}
.header{background:linear-gradient(135deg,#161b22,#0d1117);border-bottom:1px solid #21262d;padding:18px 32px 12px;text-align:center;}
.header h1{font-size:28px;font-weight:700;margin-bottom:4px;background:linear-gradient(90deg,#e74c3c,#f39c12);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.header .subtitle{font-size:12px;color:#6e7681;}
/* Trading advice */
.advice-section{max-width:1200px;margin:16px auto;padding:0 16px;}
.advice-card{background:linear-gradient(135deg,#1a0a0a,#0d1117);border:2px solid #e74c3c;border-radius:10px;padding:20px 24px;margin-bottom:14px;}
.advice-card h2{font-size:20px;color:#e74c3c;margin-bottom:12px;display:flex;align-items:center;gap:8px;}
.advice-card h2 .badge{background:#e74c3c;color:#fff;font-size:14px;padding:2px 10px;border-radius:4px;}
.advice-card .disclaimer{font-size:12px;color:#e74c3c;margin-bottom:14px;padding:8px 12px;background:rgba(231,76,60,0.1);border-radius:6px;}
.advice-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:12px;}
.advice-item{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px 16px;}
.advice-item .ai-title{font-size:12px;color:#6e7681;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;}
.advice-item .ai-value{font-size:18px;font-weight:700;}
.advice-item .ai-detail{font-size:12px;color:#6e7681;margin-top:4px;line-height:1.5;}
.levels-table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;}
.levels-table th{text-align:left;padding:6px 10px;color:#6e7681;font-size:11px;border-bottom:1px solid #21262d;}
.levels-table td{padding:6px 10px;border-bottom:1px solid #1a1f29;}
.levels-table tr:hover td{background:rgba(255,255,255,0.02);}
/* signal bar */
.signal-bar{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;padding:10px 24px;background:#161b22;border-bottom:1px solid #21262d;}
.signal-card{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 16px;text-align:center;min-width:120px;}
.signal-card .label{font-size:11px;color:#6e7681;margin-bottom:3px;}
.signal-card .value{font-size:14px;font-weight:600;}
.up{color:#e74c3c;}.down{color:#2ecc71;}
/* stats */
.stats{display:flex;justify-content:center;gap:24px;padding:10px 24px;background:#161b22;border-bottom:1px solid #21262d;flex-wrap:wrap;}
.stat-item{text-align:center;}
.stat-val{font-size:20px;font-weight:700;margin-bottom:1px;}
.stat-lbl{font-size:11px;color:#6e7681;}
/* charts */
.container{max-width:1440px;margin:0 auto;padding:8px 12px;}
.chart-box{background:#161b22;border-radius:8px;border:1px solid #21262d;padding:10px;margin-bottom:8px;}
#kline-chart{width:100%;height:500px;}
#vol-chart{width:100%;height:160px;}
#macd-chart{width:100%;height:200px;}
/* Analysis content sections */
.analysis-section{max-width:1200px;margin:20px auto;padding:0 16px;}
.analysis-card{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:20px 24px;margin-bottom:14px;line-height:1.8;font-size:14px;}
.analysis-card h3{font-size:18px;color:#f39c12;margin-bottom:12px;border-bottom:1px solid #21262d;padding-bottom:8px;}
.analysis-card h4{color:#e67e22;margin:14px 0 6px;font-size:15px;}
.analysis-card p{margin-bottom:10px;}
.analysis-card ul,.analysis-card ol{margin:8px 0 8px 20px;}
.analysis-card li{margin-bottom:4px;}
.analysis-card .highlight{color:#e74c3c;font-weight:600;}
.analysis-card .warn{color:#2ecc71;font-weight:600;}
.analysis-card code{background:#0d1117;padding:1px 6px;border-radius:3px;font-size:13px;color:#a29bfe;}
.analysis-card table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px;}
.analysis-card table th{text-align:left;padding:6px 10px;background:#0d1117;color:#6e7681;font-size:11px;}
.analysis-card table td{padding:6px 10px;border-bottom:1px solid #1a1f29;}
.analysis-card .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;margin:2px;}
.tag-bull{background:rgba(231,76,60,0.2);color:#e74c3c;}
.tag-bear{background:rgba(46,204,113,0.2);color:#2ecc71;}
.tag-neutral{background:rgba(106,118,129,0.2);color:#6e7681;}
.footer{text-align:center;padding:14px;color:#484f58;font-size:11px;border-top:1px solid #21262d;margin-top:6px;}
@media(max-width:768px){
  .header h1{font-size:18px;}
  .advice-grid{grid-template-columns:1fr;}
  .signal-card{padding:6px 8px;min-width:80px;}.signal-card .value{font-size:12px;}
  #kline-chart{height:350px;}#vol-chart{height:120px;}#macd-chart{height:150px;}
}
</style>
</head>
<body>""")

# Header
html_parts.append(f"""
<div class="header">
  <h1>中际旭创 &nbsp;300308.SZ</h1>
  <div class="subtitle">深度技术分析 &nbsp;|&nbsp; {dates[0]} ~ {dates[-1]} &nbsp;|&nbsp; 共 {N} 个交易日</div>
</div>""")

# ── TRADING ADVICE SECTION ──
html_parts.append(f"""
<div class="advice-section">
  <div class="advice-card">
    <h2><span class="badge">⚠️ 操作建议</span> 6月29日（周一）— 当前空仓</h2>
    <div class="disclaimer">⚠️ 以下分析基于技术面数据，仅供参考，不构成投资建议。股市有风险，投资需谨慎。</div>
    
    <div class="advice-grid">
      <div class="advice-item">
        <div class="ai-title">核心策略</div>
        <div class="ai-value" style="color:#f39c12">观望为主，等待止跌信号</div>
        <div class="ai-detail">上周连续两日大阴线（-5.23% / -5.25%），短线空头力量释放中，不宜急于抄底。</div>
      </div>
      <div class="advice-item">
        <div class="ai-title">激进建仓区</div>
        <div class="ai-value" style="color:#e74c3c">¥1200 ~ ¥1235</div>
        <div class="ai-detail">前低支撑 + 20日均线附近。若周一放量止跌于此区间，可轻仓试探，仓位不超过30%。</div>
      </div>
      <div class="advice-item">
        <div class="ai-title">保守建仓条件</div>
        <div class="ai-value" style="color:#3498db">等待站回 ¥1320 以上</div>
        <div class="ai-detail">需同时满足：① 收盘突破MA10(约¥1320) ② MACD绿柱缩短 ③ 成交量放大。可建仓40-50%。</div>
      </div>
      <div class="advice-item">
        <div class="ai-title">止损位</div>
        <div class="ai-value" style="color:#e74c3c">跌破 ¥1235 坚决止损</div>
        <div class="ai-detail">若跌破前低1235且无法收回，下方空间打开至¥1077(BB下轨)，亏损约-2%至-14%。</div>
      </div>
    </div>

    <table class="levels-table" style="margin-top:16px;">
      <tr><th>点位</th><th>价格</th><th>性质</th><th>操作</th></tr>
      <tr><td style="color:#e74c3c">强阻力</td><td>¥1416.88</td><td>历史高点 (6月22日)</td><td>突破前不建议追高</td></tr>
      <tr><td style="color:#f39c12">阻力</td><td>¥1320 ~ ¥1382</td><td>MA10 / 前期平台</td><td>收复此区转多头</td></tr>
      <tr><td style="color:#1abc9c">当前价</td><td>¥{ep:.2f}</td><td>6月26日收盘</td><td>—</td></tr>
      <tr><td style="color:#3498db">支撑1</td><td>¥1235 ~ ¥1250</td><td>前低 / MA20附近</td><td>激进建仓区</td></tr>
      <tr><td style="color:#3498db">支撑2</td><td>¥1078</td><td>布林带下轨(20日,2σ)</td><td>强支撑，若跌至此可加仓</td></tr>
      <tr><td style="color:#2ecc71">强支撑</td><td>¥1000</td><td>整数关口 + 心理支撑</td><td>极端回调目标</td></tr>
    </table>
  </div>
</div>""")

# Signal bar
html_parts.append(f"""
<div class="signal-bar">
  <div class="signal-card"><div class="label">均线状态</div><div class="value up">{ma_st}</div></div>
  <div class="signal-card"><div class="label">MA5/MA10/MA20</div><div class="value">{ma5v}/{ma10v}/{ma20v}</div></div>
  <div class="signal-card"><div class="label">MACD</div><div class="value down">{macd_st}<br><span style="font-size:11px">{macd_dir}</span></div></div>
  <div class="signal-card"><div class="label">布林带</div><div class="value" style="color:#f39c12">{bb_pos}<br><span style="font-size:11px">{bb_sig}</span></div></div>
  <div class="signal-card"><div class="label">最近金叉</div><div class="value up">{last_gc}</div></div>
  <div class="signal-card"><div class="label">最近死叉</div><div class="value down">{last_dc}</div></div>
  <div class="signal-card"><div class="label">RSI(14)</div><div class="value" style="color:{'#2ecc71' if rsi_last < 30 else '#e74c3c' if rsi_last > 70 else '#f39c12'}">{rsi_last:.0f}</div></div>
  <div class="signal-card"><div class="label">成交量</div><div class="value">{vol_vs_avg}<br><span style="font-size:11px">{vol_today:.1f}万手 vs 均{vol_avg20:.1f}</span></div></div>
</div>""")

# Stats
html_parts.append(f"""
<div class="stats">
  <div class="stat-item"><div class="stat-val up">¥{ep:.2f}</div><div class="stat-lbl">最新收盘</div></div>
  <div class="stat-item"><div class="stat-val">¥{sp:.2f}</div><div class="stat-lbl">期初收盘</div></div>
  <div class="stat-item"><div class="stat-val {"up"if chg>=0 else"down"}">{"+"if chg>=0 else""}{chg:.2f}</div><div class="stat-lbl">期间涨跌</div></div>
  <div class="stat-item"><div class="stat-val {"up"if chg_pct>=0 else"down"}">{"+"if chg_pct>=0 else""}{chg_pct:.2f}%</div><div class="stat-lbl">涨跌幅</div></div>
  <div class="stat-item"><div class="stat-val up">¥{all_hi:.2f}</div><div class="stat-lbl">区间最高</div></div>
  <div class="stat-item"><div class="stat-val down">¥{all_lo:.2f}</div><div class="stat-lbl">区间最低</div></div>
</div>""")

# Charts
html_parts.append(f"""
<div class="container">
  <div class="chart-box"><div id="kline-chart"></div></div>
  <div class="chart-box"><div id="vol-chart"></div></div>
  <div class="chart-box"><div id="macd-chart"></div></div>
</div>""")

# ── ANALYSIS CONTENT ──
# Recent action summary
html_parts.append(f"""
<div class="analysis-section">
  <div class="analysis-card">
    <h3>📊 近期盘面回顾</h3>
    <p>中际旭创近5个交易日走势：<code>{recent_summary}</code></p>
    <p>上周（6月22-26日）出现了<span class="highlight">两次单日跌幅超过5%</span>的大阴线，这是自2025年10月以来首次出现如此密集的大幅回调。</p>
    <ul>
      <li><b>6月22日</b>：创历史新高 <span class="highlight">¥1416.88</span> 后回落收于¥1382.33</li>
      <li><b>6月23日</b>：高开低走，<span class="warn">暴跌 -5.23%</span>，放出巨量</li>
      <li><b>6月26日</b>：再度 <span class="warn">暴跌 -5.25%</span>，收盘¥1253.89，跌破5日和10日均线</li>
    </ul>
    <p>从高点1416.88到收盘1253.89，<span class="warn">4个交易日回调约 -11.5%</span>，属于技术性调整范畴。</p>
  </div>

  <div class="analysis-card">
    <h3>🔍 技术面深度分析</h3>
    
    <h4>1. 均线系统</h4>
    <p>当前均线数值：MA5={ma5v} | MA10={ma10v} | MA20={ma20v}</p>
    <p>均线仍保持 <span class="highlight">多头排列（MA5 > MA10 > MA20）</span>，但MA5已从1420回落至约{ma5v}，与MA10({ma10v})的差距急剧缩小。<span class="warn">若周一继续下跌，MA5可能下穿MA10形成死叉</span>，这是需要高度警惕的信号。</p>
    
    <h4>2. MACD指标</h4>
    <p>DIF={dif_[last]:.2f} | DEA={dea_[last]:.2f} | MACD柱={macd_hist[last]:.2f}</p>
    <p>MACD当前处于 <span class="warn">空头状态（DIF < DEA）</span>，绿柱在扩大，表明下跌动能仍在释放中。历史上，中际旭创的MACD死叉后通常会有1-2周的调整期。</p>
    
    <h4>3. 布林带分析</h4>
    <p>布林上轨={bb_upper[last]:.2f} | 中轨={bb_mid[last]:.2f} | 下轨={bb_lower[last]:.2f}</p>
    <p>股价位于 <span style="color:#f39c12">布林上轨~中轨之间</span>，仍处于强势区域。但此前股价曾突破上轨（超买），现正在回落。若继续下跌，中轨(¥{bb_mid[last]:.0f})将是关键支撑。<span class="highlight">下轨在¥{bb_lower[last]:.0f}</span>，距离当前价约-14%。</p>

    <h4>4. 成交量分析</h4>
    <p>两日大跌均伴随 {vol_vs_avg}（6/26成交{vol_today:.1f}万手，20日均{vol_avg20:.1f}万手），说明有大量筹码在高位换手出货。<span class="warn">放量下跌通常是趋势转弱的确认信号</span>。</p>

    <h4>5. 综合判断</h4>
    <p><span class="tag tag-bear">短线偏空</span> <span class="tag tag-bull">中线上涨趋势未破</span></p>
    <p>短线：两日大阴线 + MACD死叉 + 放量 = <span class="warn">短期调整压力大</span>，周五收盘后未见止跌信号。<br>
    中线：均线多头排列未破 + 股价仍在布林中轨之上 + 年涨幅759%趋势完好 = <span class="highlight">中长期上升趋势未破坏</span>。</p>
  </div>

  <div class="analysis-card">
    <h3>🏢 基本面分析</h3>
    
    <h4>公司概况</h4>
    <p><b>中际旭创股份有限公司</b>（Zhongji Innolight, SZ:300308），成立于2005年，2017年登陆创业板。总部位于山东烟台，员工11,625人。</p>
    <p><b>核心业务</b>：高速光通信收发模块（光模块）的研发、设计、封装、测试和销售。产品覆盖100G/200G/400G/800G光模块，正在研发1.6T产品。</p>
    <p><b>行业地位</b>：全球光模块市场份额<span class="highlight">前三</span>，国内龙头。公司董事长兼总经理刘圣，具备深厚的光电行业背景。</p>

    <h4>核心投资逻辑</h4>
    <ol>
      <li><b>AI算力爆发驱动光模块需求</b>：ChatGPT引发的AI大模型竞赛，推动数据中心从400G向800G/1.6T光模块升级，中际旭创是核心受益者。</li>
      <li><b>深度绑定全球头部客户</b>：与<span class="highlight">NVIDIA、Google、Meta、Amazon</span>等建立稳定供应关系，800G光模块全球出货量领先。</li>
      <li><b>毛利率持续改善</b>：随着高端产品(800G)占比提升，综合毛利率稳步向上，盈利能力增强。</li>
      <li><b>竞争壁垒</b>：光模块行业技术迭代快（每2-3年一代），中际旭创的先发优势和规模效应构成竞争壁垒。</li>
    </ol>
    
    <h4>风险因素</h4>
    <ol>
      <li><span class="warn">估值已处历史高位</span>：年涨幅759%，股价透支了部分未来增长预期</li>
      <li><b>大客户集中风险</b>：前五大客户收入占比高，单一客户订单波动影响大</li>
      <li><b>技术迭代风险</b>：若在1.6T/3.2T等下一代产品研发落伍，竞争优势将削弱</li>
      <li><b>中美科技博弈</b>：光模块涉及高端半导体，有出口管制和供应链风险</li>
      <li><b>行业景气度波动</b>：光模块行业具有周期性，历史上曾出现过供过于求</li>
    </ol>
  </div>

  <div class="analysis-card">
    <h3>📖 基础知识讲解</h3>
    
    <h4>什么是K线？</h4>
    <p><b>K线（蜡烛图）</b> 是一种记录价格走势的图表，由日本的米商本间宗久在18世纪发明。每根K线包含<span class="highlight">四个价格</span>：开盘价、收盘价、最高价、最低价。</p>
    <p><b>阳线（红/白）</b>：收盘 > 开盘，表示价格上涨。实体部分用红色填充。<br>
    <b>阴线（绿/黑）</b>：收盘 < 开盘，表示价格下跌。实体部分用绿色填充。<br>
    （注：A股习惯红涨绿跌，与美股相反）</p>
    <p>K线能直观反映市场情绪：长阳线代表多头强势，长阴线代表空头碾压；十字星代表犹豫不定。连续多根K线组合成各种形态（如头肩顶、W底等），是技术分析的基石。</p>

    <h4>什么是基本面分析？</h4>
    <p><b>基本面分析</b>是通过研究公司的财务状况、行业地位、管理团队、竞争格局等，判断公司的<span class="highlight">内在价值</span>是否被市场低估或高估。</p>
    <p><b>主要指标</b>：</p>
    <ul>
      <li><b>PE（市盈率）</b>：股价/每股收益，衡量"回本年限"</li>
      <li><b>ROE（净资产收益率）</b>：公司用股东的钱创造利润的效率</li>
      <li><b>营收增长率</b>：业务在扩张还是收缩</li>
      <li><b>毛利率</b>：产品竞争力，越高越有议价权</li>
    </ul>
    <p>基本面分析回答的问题："这家公司<span class="highlight">值多少钱</span>？现在的价格合理吗？" 适合长期投资者和机构决策。</p>

    <h4>什么是技术面分析？</h4>
    <p><b>技术面分析</b>基于三个假设：① 市场行为包容消化一切 ② 价格以趋势方式演变 ③ 历史会重演。通过研究价格图表和指标，预测未来走势。</p>
    <p><b>常用技术指标</b>：</p>
    <table>
      <tr><th>指标</th><th>作用</th><th>当前信号</th></tr>
      <tr><td>MA（移动平均线）</td><td>趋势方向，金叉/死叉</td><td style="color:#e74c3c">多头排列</td></tr>
      <tr><td>MACD</td><td>趋势强度，多空转换</td><td style="color:#2ecc71">空头信号</td></tr>
      <tr><td>布林带</td><td>超买/超卖，波动范围</td><td style="color:#f39c12">偏强区域</td></tr>
      <tr><td>RSI(14)</td><td>超买(>70)/超卖(<30)</td><td style="color:#f39c12">{rsi_last:.0f} 中性偏弱</td></tr>
      <tr><td>成交量</td><td>趋势确认，放量/缩量</td><td style="color:#2ecc71">放量下跌(警示)</td></tr>
    </table>
    <p style="margin-top:10px;"><b>基本面 vs 技术面</b>：基本面告诉你<span class="highlight">"买什么"</span>、技术面告诉你<span class="highlight">"什么时候买"</span>。两者结合是最有效的投资方法。</p>
  </div>

  <div class="analysis-card">
    <h3>⚠️ 风险提示</h3>
    <p style="color:#6e7681;font-size:13px;">
      本页面所有分析基于公开市场数据和技术指标计算，仅供学习研究参考，<span class="highlight">不构成任何投资建议</span>。<br><br>
      股票投资具有高风险性，中际旭创（300308.SZ）过去一年的涨幅不代表未来收益，<span class="warn">投资者可能面临本金损失</span>。<br><br>
      光模块行业受AI算力需求、国际贸易政策、技术迭代等多重因素影响，公司估值已显著高于历史均值，<span class="warn">回调风险不可忽视</span>。<br><br>
      请根据自身风险承受能力独立做出投资决策。
    </p>
  </div>
</div>""")

# Footer
html_parts.append(f"""
<div class="footer">
  数据来源: Tushare Pro &nbsp;|&nbsp; 中际旭创 300308.SZ &nbsp;|&nbsp; 生成: {dates[-1]}<br>
  技术指标: K线 + 布林带 + MACD + RSI &nbsp;|&nbsp; 红涨绿跌 &nbsp;|&nbsp; 仅供参考，不构成投资建议
</div>

<script>
{js_vars}
</script>
{Chart1}
</body>
</html>""")

# ── Write ──
OUT = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_chart.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))

print(f"[OK] {OUT}")
print(f"  Days: {N}, {dates[0]} ~ {dates[-1]}")
print(f"  Close: {sp:.2f} -> {ep:.2f} ({chg:+.2f}, {chg_pct:+.2f}%)")
print(f"  MA: {ma_st} ({ma5v}/{ma10v}/{ma20v})")
print(f"  MACD: DIF={dif_[last]:.2f} DEA={dea_[last]:.2f} Hist={macd_hist[last]:.2f}")
print(f"  BB: {bb_pos} (U{bb_upper[last]:.2f} M{bb_mid[last]:.2f} L{bb_lower[last]:.2f})" if bb_upper[last] else "  BB: -")
print(f"  RSI(14): {rsi_last:.1f}")
print(f"  Vol: {vol_today:.1f}万手 vs avg{vol_avg20:.1f} ({vol_vs_avg})")
