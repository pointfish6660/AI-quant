#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate comprehensive K-line chart with MACD, Bollinger Bands, and key signals.
"""
import csv, json, os

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

# ── Helper: JS array string ──
def js(a, prec=2):
    if a and isinstance(a[0], str):
        return "[" + ",".join(f'"{v}"' for v in a) + "]"
    return "[" + ",".join(f"{v:.{prec}f}" if prec else str(v) for v in a) + "]"

def js_nullable(a, prec=2):
    """Like js() but supports None values → null."""
    def fmt(v):
        if v is None: return "null"
        if isinstance(v, (int, float)):
            return f"{v:.{prec}f}" if prec else str(v)
        return f'"{v}"'
    return "[" + ",".join(fmt(v) for v in a) + "]"

# ── Indicators ──
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
    return [a[i]-b[i] if a[i] is not None and b[i] is not None else None
            for i in range(len(a))]

def mult(a, k):
    return [a[i]*k if a[i] is not None else None for i in range(len(a))]

# ── Compute all indicators ──
ma5, ma10, ma20 = sma(closes,5), sma(closes,10), sma(closes,20)

# Bollinger Bands (20, 2)
bb_mid   = ma20
bb_std   = rolling_std(closes, 20)
bb_upper = [bb_mid[i]+2*bb_std[i] if bb_mid[i] is not None else None for i in range(N)]
bb_lower = [bb_mid[i]-2*bb_std[i] if bb_mid[i] is not None else None for i in range(N)]

# MACD (12, 26, 9)
ema12 = ema(closes, 12)
ema26 = ema(closes, 26)
dif   = diff(ema12, ema26)
dea   = ema(dif, 9)
macd_hist = mult(diff(dif, dea), 2)

# ── Cross detection ──
def find_crosses(a, b):
    """Return [idx, type] where type='gold' (a crosses above b) or 'death' (a crosses below b)."""
    crosses = []
    for i in range(1, len(a)):
        if a[i] is None or b[i] is None or a[i-1] is None or b[i-1] is None:
            continue
        if a[i-1] <= b[i-1] and a[i] > b[i]:   # gold cross
            crosses.append([i, "gold"])
        elif a[i-1] >= b[i-1] and a[i] < b[i]:  # death cross
            crosses.append([i, "death"])
    return crosses

gc_5_10   = find_crosses(ma5, ma10)
gc_10_20  = find_crosses(ma10, ma20)
gc_dif_dea = find_crosses(dif, dea)

# Only keep recent 4 crosses per pair
gc_5_10 = gc_5_10[-4:]
gc_10_20 = gc_10_20[-4:]
gc_dif_dea = gc_dif_dea[-4:]

# ── Key levels ──
all_high = max(highs)
all_low  = min(lows)
recent_high = max(highs[-40:]) if N>=40 else all_high
recent_low  = min(lows[-40:])  if N>=40 else all_low

# ── Current status ──
last = N - 1
if ma5[last] and ma10[last] and ma20[last]:
    if ma5[last] > ma10[last] > ma20[last]:
        ma_status = "多头排列 <span style='color:#e74c3c'>▲</span>"
    elif ma5[last] < ma10[last] < ma20[last]:
        ma_status = "空头排列 <span style='color:#2ecc71'>▼</span>"
    else:
        ma_status = "均线缠绕"
else:
    ma_status = "计算中"

if dif[last] is not None and dea[last] is not None:
    if dif[last] > dea[last]:
        macd_signal = "DIF>DEA <span style='color:#e74c3c'>多头</span>"
    else:
        macd_signal = "DIF<DEA <span style='color:#2ecc71'>空头</span>"
    macd_hist_dir = "红柱" if macd_hist[last] > 0 else "绿柱"
else:
    macd_signal, macd_hist_dir = "计算中", ""

if bb_upper[last] is not None:
    c = closes[last]; bu = bb_upper[last]; bm = bb_mid[last]; bl = bb_lower[last]
    if c > bu: bb_pos = "突破上轨"
    elif c > bm: bb_pos = "上轨~中轨"
    elif c > bl: bb_pos = "中轨~下轨"
    else: bb_pos = "跌破下轨"
else:
    bb_pos = "计算中"

# ── Build signal markers for JS ──
# Mark golden/death crosses on K-line chart as scatter series
def make_marker_data(crosses):
    """Return JS code for markPoint data."""
    result = []
    for idx, typ in crosses:
        color = "#e74c3c" if typ == "gold" else "#2ecc71"
        symbol = "arrow" if typ == "gold" else "pin"
        label = "金叉" if typ == "gold" else "死叉"
        result.append(dict(coord=[idx, lows[idx] if typ=="gold" else highs[idx]],
                           value=label, symbol=symbol,
                           symbolSize=10, itemStyle=dict(color=color)))
    return json.dumps(result, ensure_ascii=False) if result else "[]"

# ── Build JS data arrays ──
js_vars = "\n".join([
    f"var dates = {js(dates)};",
    f"var opens = {js(opens)}; var closes = {js(closes)};",
    f"var highs = {js(highs)}; var lows = {js(lows)};",
    f"var vols = {js(vols)}; var amounts = {js(amounts,0)}; var pcts = {js(pcts)};",
    f"var bbUpper = {js_nullable(bb_upper)}; var bbMid = {js_nullable(bb_mid)}; var bbLower = {js_nullable(bb_lower)};",
    f"var dif_ = {js_nullable(dif)}; var dea_ = {js_nullable(dea)}; var macdHist = {js_nullable(macd_hist,4)};",
    f"var ma5 = {js_nullable(ma5)}; var ma10 = {js_nullable(ma10)}; var ma20 = {js_nullable(ma20)};",
    f"var allHigh = {all_high}; var allLow = {all_low};",
    f"var recentHigh = {recent_high}; var recentLow = {recent_low};",
    f"var lastClose = {closes[-1]:.2f};",
])

# ── HTML template ──
# Using %% as placeholder for single { in JS/CSS, replaced after
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中际旭创 (300308.SZ) 技术分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#0d1117;color:#c9d1d9;}
.header{background:linear-gradient(135deg,#161b22,#0d1117);border-bottom:1px solid #21262d;padding:18px 32px 12px;text-align:center;}
.header h1{font-size:26px;font-weight:700;margin-bottom:4px;background:linear-gradient(90deg,#e74c3c,#f39c12);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.header .subtitle{font-size:12px;color:#6e7681;}
/* indicator summary bar */
.signal-bar{display:flex;justify-content:center;gap:18px;flex-wrap:wrap;padding:10px 24px;background:#161b22;border-bottom:1px solid #21262d;}
.signal-card{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 16px;text-align:center;min-width:120px;}
.signal-card .label{font-size:11px;color:#6e7681;margin-bottom:3px;}
.signal-card .value{font-size:14px;font-weight:600;line-height:1.4;}
.up{color:#e74c3c;}.down{color:#2ecc71;}
/* stats */
.stats{display:flex;justify-content:center;gap:32px;padding:10px 24px;background:#161b22;border-bottom:1px solid #21262d;flex-wrap:wrap;}
.stat-item{text-align:center;}
.stat-val{font-size:20px;font-weight:700;margin-bottom:1px;}
.stat-lbl{font-size:11px;color:#6e7681;}
/* charts */
.container{max-width:1440px;margin:0 auto;padding:8px 12px;}
.chart-box{background:#161b22;border-radius:8px;border:1px solid #21262d;padding:10px;margin-bottom:8px;}
#kline-chart{width:100%;height:500px;}
#vol-chart{width:100%;height:160px;}
#macd-chart{width:100%;height:200px;}
.footer{text-align:center;padding:14px;color:#484f58;font-size:11px;border-top:1px solid #21262d;margin-top:6px;}
@media(max-width:768px){
  .header h1{font-size:18px;}
  .signal-bar{gap:8px;}.signal-card{padding:6px 10px;min-width:80px;}
  .signal-card .value{font-size:12px;}
  .stat-val{font-size:16px;}.stats{gap:16px;}
  #kline-chart{height:350px;}#vol-chart{height:120px;}#macd-chart{height:150px;}
}
</style>
</head>
<body>

<div class="header">
  <h1>中际旭创 &nbsp;300308.SZ</h1>
  <div class="subtitle">DATE_FROM ~ DATE_TO &nbsp;|&nbsp; 共 N_DAYS 个交易日</div>
</div>

<!-- Indicator Summary -->
<div class="signal-bar">
  <div class="signal-card">
    <div class="label">均线状态</div>
    <div class="value">MA_STATUS</div>
  </div>
  <div class="signal-card">
    <div class="label">MACD</div>
    <div class="value">MACD_SIGNAL<br><span style="font-size:11px">MACD_DIR</span></div>
  </div>
  <div class="signal-card">
    <div class="label">布林带</div>
    <div class="value">BB_POS</div>
  </div>
  <div class="signal-card">
    <div class="label">最近金叉</div>
    <div class="value" style="color:#e74c3c">LAST_GC</div>
  </div>
  <div class="signal-card">
    <div class="label">最近死叉</div>
    <div class="value" style="color:#2ecc71">LAST_DC</div>
  </div>
</div>

<!-- Price Stats -->
<div class="stats">
  <div class="stat-item"><div class="stat-val up">CLOSE_VAL</div><div class="stat-lbl">最新收盘</div></div>
  <div class="stat-item"><div class="stat-val">START_VAL</div><div class="stat-lbl">期初收盘</div></div>
  <div class="stat-item"><div class="stat-val CLR_CHG">CHG_VAL</div><div class="stat-lbl">期间涨跌</div></div>
  <div class="stat-item"><div class="stat-val CLR_PCT">PCT_VAL</div><div class="stat-lbl">涨跌幅</div></div>
  <div class="stat-item"><div class="stat-val up">HIGH_VAL</div><div class="stat-lbl">区间最高</div></div>
  <div class="stat-item"><div class="stat-val down">LOW_VAL</div><div class="stat-lbl">区间最低</div></div>
</div>

<div class="container">
  <div class="chart-box"><div id="kline-chart"></div></div>
  <div class="chart-box"><div id="vol-chart"></div></div>
  <div class="chart-box"><div id="macd-chart"></div></div>
</div>

<div class="footer">
  数据来源: Tushare Pro &nbsp;|&nbsp; 中际旭创 300308.SZ &nbsp;|&nbsp; 生成: DATE_TO<br>
  K线 + 布林带 + MACD &nbsp;|&nbsp; 红涨绿跌 &nbsp;|&nbsp; 标记金叉 · 死叉<br>
  本页面仅供学习参考，不构成投资建议
</div>

<script>
JS_DATA

var UP="#e74c3c", DOWN="#2ecc71", ZS=50, ZE=100;

// K-line data
var kl=[];
for(var i=0;i<dates.length;i++) kl.push([opens[i],closes[i],lows[i],highs[i]]);

// ── K-line Chart ──
var kch=echarts.init(document.getElementById("kline-chart"));
kch.setOption({
  backgroundColor:"#161b22",
  tooltip:{
    trigger:"axis",
    axisPointer:{type:"cross"},
    backgroundColor:"rgba(13,17,23,0.96)",
    borderColor:"#21262d",
    textStyle:{color:"#c9d1d9",fontSize:13},
    formatter:function(ps){
      var i=ps[0].dataIndex, c=pcts[i], col=c>=0?UP:DOWN;
      var s='<div style="font-size:13px;line-height:2"><b>'+dates[i]+'</b><br>';
      s+='开盘 <b>'+opens[i].toFixed(2)+'</b> &nbsp; 最高 <b style="color:'+UP+'">'+highs[i].toFixed(2)+'</b><br>';
      s+='最低 <b style="color:'+DOWN+'">'+lows[i].toFixed(2)+'</b> &nbsp; 收盘 <b style="color:'+col+';font-size:15px">'+closes[i].toFixed(2)+'</b><br>';
      s+='涨跌 <b style="color:'+col+'">'+(c>=0?"+":"")+c.toFixed(2)+'%</b> &nbsp; 成交额 '+amounts[i]+' 万元<br>';
      if(bbUpper[i]!=null) s+='布林上轨 '+bbUpper[i].toFixed(2)+' 中轨 '+bbMid[i].toFixed(2)+' 下轨 '+bbLower[i].toFixed(2)+'<br>';
      if(dif_[i]!=null) s+='MACD DIF '+dif_[i].toFixed(2)+' DEA '+dea_[i].toFixed(2);
      return s+'</div>';
    }
  },
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
    {name:"BB上轨",type:"line",data:bbUpper,symbol:"none",lineStyle:{width:1,color:"#f39c12",type:"dashed"},itemStyle:{color:"#f39c12"}},
    {name:"BB下轨",type:"line",data:bbLower,symbol:"none",lineStyle:{width:1,color:"#f39c12",type:"dashed"},itemStyle:{color:"#f39c12"}},
    {name:"BB中轨",type:"line",data:bbMid,symbol:"none",lineStyle:{width:0.8,color:"#f39c12"},itemStyle:{color:"#f39c12"}},
    // Golden cross markers
    {name:"金叉(MA5>MA10)",type:"scatter",data:GC_5_10,symbol:"triangle",symbolSize:14,itemStyle:{color:"#e74c3c"},z:10,label:{show:true,position:"bottom",color:"#e74c3c",fontSize:9,formatter:"金"}},
    // Death cross markers
    {name:"死叉(MA5<MA10)",type:"scatter",data:DC_5_10,symbol:"triangle",symbolRotate:180,symbolSize:14,itemStyle:{color:"#2ecc71"},z:10,label:{show:true,position:"top",color:"#2ecc71",fontSize:9,formatter:"死"}},
    // Support / Resistance lines
    {name:"阻力位",type:"line",markLine:{silent:true,symbol:"none",lineStyle:{color:"#e74c3c",type:"dashed",width:1},label:{color:"#e74c3c",fontSize:10},data:[{yAxis:RECENT_HIGH,name:"阻力 ¥R_H"},{yAxis:ALL_H,name:"历史高 ¥A_H"}]}},
    {name:"支撑位",type:"line",markLine:{silent:true,symbol:"none",lineStyle:{color:"#2ecc71",type:"dashed",width:1},label:{color:"#2ecc71",fontSize:10},data:[{yAxis:RECENT_LOW,name:"支撑 ¥R_L"},{yAxis:ALL_LOW,name:"历史低 ¥A_L"}]}}
  ]
});

// ── Volume Chart ──
var vch=echarts.init(document.getElementById("vol-chart"));
vch.setOption({
  backgroundColor:"#161b22",
  tooltip:{trigger:"axis",backgroundColor:"rgba(13,17,23,0.96)",borderColor:"#21262d",textStyle:{color:"#c9d1d9",fontSize:12},formatter:function(ps){var i=ps[0].dataIndex;return dates[i]+"<br>成交量 <b>"+vols[i].toFixed(2)+"</b> 万手";}},
  grid:{left:"7%",right:"3%",top:6,bottom:22},
  xAxis:{type:"category",data:dates,axisLabel:{show:false},axisLine:{lineStyle:{color:"#21262d"}},axisTick:{show:false},splitLine:{show:false}},
  yAxis:{type:"value",name:"万手",nameTextStyle:{color:"#484f58",fontSize:11},splitLine:{lineStyle:{color:"#21262d",type:"dashed"}},axisLabel:{color:"#484f58",fontSize:10},axisLine:{show:false}},
  dataZoom:[{type:"inside",start:ZS,end:ZE,xAxisIndex:0},{type:"slider",start:ZS,end:ZE,height:18,bottom:2}],
  series:[{type:"bar",data:vols.map(function(v,i){return{value:v,itemStyle:{color:pcts[i]>=0?"rgba(231,76,60,0.65)":"rgba(46,204,113,0.65)"}};}),barWidth:"60%"}]
});

// ── MACD Chart ──
var mch=echarts.init(document.getElementById("macd-chart"));
mch.setOption({
  backgroundColor:"#161b22",
  tooltip:{trigger:"axis",backgroundColor:"rgba(13,17,23,0.96)",borderColor:"#21262d",textStyle:{color:"#c9d1d9",fontSize:12},formatter:function(ps){var i=ps[0].dataIndex;if(dif_[i]==null)return"";return dates[i]+"<br>DIF <b style='color:#e67e22'>"+dif_[i].toFixed(2)+"</b> &nbsp; DEA <b style='color:#3498db'>"+dea_[i].toFixed(2)+"</b><br>MACD <b style='color:"+(macdHist[i]>=0?"#e74c3c":"#2ecc71")+"'>"+macdHist[i].toFixed(2)+"</b>";}},
  legend:{data:["MACD柱","DIF","DEA"],top:4,left:50,textStyle:{color:"#6e7681",fontSize:11},itemWidth:18,itemHeight:10},
  grid:{left:"7%",right:"3%",top:36,bottom:24},
  xAxis:{type:"category",data:dates,axisLine:{lineStyle:{color:"#21262d"}},axisLabel:{color:"#484f58",fontSize:9,formatter:function(v){return v.substring(5);},rotate:45},axisTick:{show:false},splitLine:{show:false}},
  yAxis:{type:"value",name:"MACD",nameTextStyle:{color:"#484f58",fontSize:11},splitLine:{lineStyle:{color:"#21262d",type:"dashed"}},axisLabel:{color:"#484f58",fontSize:10},axisLine:{show:false}},
  dataZoom:[{type:"inside",start:ZS,end:ZE,xAxisIndex:0},{type:"slider",start:ZS,end:ZE,height:18,bottom:2}],
  series:[
    {name:"MACD柱",type:"bar",data:macdHist.map(function(v,i){if(v==null)return 0;return{value:v,itemStyle:{color:v>=0?"rgba(231,76,60,0.6)":"rgba(46,204,113,0.6)"}};}),barWidth:"60%"},
    {name:"DIF",type:"line",data:dif_,symbol:"none",lineStyle:{width:1.2,color:"#e67e22"}},
    {name:"DEA",type:"line",data:dea_,symbol:"none",lineStyle:{width:1.2,color:"#3498db"}}
  ]
});

// ── Sync ──
kch.group="sync";vch.group="sync";mch.group="sync";
echarts.connect("sync");

// ── Responsive ──
window.addEventListener("resize",function(){kch.resize();vch.resize();mch.resize();});

// ── MACD DIF/DEA cross markers ──
var macdGC = MACD_GC;
var macdDC = MACD_DC;
</script>
</body>
</html>"""

# ── Prepare marker data for JS ──
def gc_data(crosses):
    """Golden cross = MA5 crosses above MA10."""
    items = []
    for idx, typ in crosses:
        if typ == "gold":
            items.append("[" + str(idx) + "," + str(round(lows[idx], 2)) + "]")
    return "[" + ",".join(items) + "]" if items else "[]"

def dc_data(crosses):
    """Death cross = MA5 crosses below MA10."""
    items = []
    for idx, typ in crosses:
        if typ == "death":
            items.append("[" + str(idx) + "," + str(round(highs[idx], 2)) + "]")
    return "[" + ",".join(items) + "]" if items else "[]"

def eq(a,b):
    return f"{a:.2f}" if isinstance(a,float) else str(a)

# Only MA5/MA10 crosses for the scatter markers (most commonly watched)
gc_5_10_only = gc_5_10  # already filtered to last 4

gc_js = gc_data(gc_5_10_only)
dc_js = dc_data(gc_5_10_only)

# MACD crosses
def macd_markers(crosses, typ):
    items = []
    for idx, t in crosses:
        if t == typ and idx < N:
            val = macd_hist[idx] if macd_hist[idx] is not None else 0
            items.append("[" + str(idx) + "," + str(round(val if val else 0, 4)) + "]")
    return "[" + ",".join(items) + "]" if items else "[]"

macd_gc_js = macd_markers(gc_dif_dea, "gold")
macd_dc_js = macd_markers(gc_dif_dea, "death")

# ── Last cross dates ──
def last_cross_str(crosses, typ):
    for idx, t in reversed(crosses):
        if t == typ and idx < N:
            return dates[idx]
    return "—"

last_gc = last_cross_str(gc_5_10_only, "gold")
last_dc = last_cross_str(gc_5_10_only, "death")

# ── Placeholder replacements ──
html = TEMPLATE
html = html.replace("DATE_FROM", dates[0]).replace("DATE_TO", dates[-1]).replace("N_DAYS", str(N))
html = html.replace("MA_STATUS", ma_status)
html = html.replace("MACD_SIGNAL", macd_signal).replace("MACD_DIR", macd_hist_dir)
html = html.replace("BB_POS", bb_pos)
html = html.replace("LAST_GC", last_gc)
html = html.replace("LAST_DC", last_dc)
html = html.replace("CLOSE_VAL", f"¥{closes[-1]:.2f}")
html = html.replace("START_VAL", f"¥{closes[0]:.2f}")
chg = closes[-1] - closes[0]
chg_pct = (closes[-1]/closes[0] - 1) * 100
html = html.replace("CLR_CHG", "up" if chg>=0 else "down")
html = html.replace("CHG_VAL", f"{'+'if chg>=0 else ''}{chg:.2f}")
html = html.replace("CLR_PCT", "up" if chg_pct>=0 else "down")
html = html.replace("PCT_VAL", f"{'+'if chg_pct>=0 else ''}{chg_pct:.2f}%")
html = html.replace("HIGH_VAL", f"¥{max(highs):.2f}")
html = html.replace("LOW_VAL", f"¥{min(lows):.2f}")
html = html.replace("JS_DATA", js_vars)
html = html.replace("GC_5_10", gc_js)
html = html.replace("DC_5_10", dc_js)
html = html.replace("MACD_GC", macd_gc_js)
html = html.replace("MACD_DC", macd_dc_js)
html = html.replace("RECENT_HIGH", f"{recent_high:.2f}")
html = html.replace("RECENT_LOW", f"{recent_low:.2f}")
html = html.replace("ALL_H", f"{all_high:.2f}")
html = html.replace("ALL_LOW", f"{all_low:.2f}")
html = html.replace("R_H", f"{recent_high:.0f}")
html = html.replace("R_L", f"{recent_low:.0f}")
html = html.replace("A_H", f"{all_high:.0f}")
html = html.replace("A_L", f"{all_low:.0f}")

# ── Write ──
OUT = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_chart.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[OK] {OUT}")
print(f"  Days: {N}, {dates[0]} ~ {dates[-1]}")
print(f"  Close: {closes[0]:.2f} -> {closes[-1]:.2f} ({chg:+.2f}, {chg_pct:+.2f}%)")
print(f"  MA: {ma_status.replace('<span','').replace('</span>','')}")
print(f"  MACD: {macd_signal.replace('<span','').replace('</span>','')} | {macd_hist_dir}")
if bb_upper[last] is not None:
    print(f"  BB: {bb_pos} (上{bb_upper[last]:.2f} 中{bb_mid[last]:.2f} 下{bb_lower[last]:.2f})")
else:
    print(f"  BB: {bb_pos}")
