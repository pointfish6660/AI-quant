#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate K-line (candlestick) chart HTML for 中际旭创 300308.SZ
Replaces the line chart with a proper candlestick chart + volume bars.
"""

import csv
import json
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_data.csv")

# --- Read CSV ---
rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        d = r["trade_date"]
        rows.append({
            "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
            "open":  float(r["open"]),
            "close": float(r["close"]),
            "high":  float(r["high"]),
            "low":   float(r["low"]),
            "vol":   float(r["vol"]),
            "amount":float(r["amount"]),
            "pct_chg": float(r["pct_chg"]),
        })

rows.sort(key=lambda x: x["date"])
dates   = [r["date"] for r in rows]
opens   = [r["open"]   for r in rows]
closes  = [r["close"]  for r in rows]
highs   = [r["high"]   for r in rows]
lows    = [r["low"]    for r in rows]
vols    = [round(r["vol"]   / 10000, 2) for r in rows]   # 万手
amounts = [round(r["amount"] / 10000, 2) for r in rows]   # 亿元
pcts    = [r["pct_chg"] for r in rows]

start_p = closes[0]
end_p   = closes[-1]
chg     = end_p - start_p
chg_pct = (end_p / start_p - 1) * 100
date_from = dates[0]
date_to   = dates[-1]
n_days    = len(dates)

UP   = "#e74c3c"   # 涨 — 红
DOWN = "#2ecc71"  # 跌 — 绿

# --- Embedded data as JS arrays ---
def js_arr(name, vals, precision=2):
    if isinstance(vals[0], (int, float)):
        body = ", ".join(f"{v:.{precision}f}" if precision else str(v) for v in vals)
    else:
        body = ", ".join(f'"{v}"' for v in vals)
    return f"var {name} = [{body}];"

js = "\n".join([
    js_arr("dates",   dates,   precision=None),
    js_arr("opens",   opens),
    js_arr("closes",  closes),
    js_arr("highs",   highs),
    js_arr("lows",    lows),
    js_arr("vols",     vols),
    js_arr("amounts",  amounts, precision=0),
    js_arr("pcts",     pcts),
])

# --- HTML template ---
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中际旭创 (300308.SZ) K线图</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Microsoft YaHei", sans-serif;
  background: #0d1117;
  color: #c9d1d9;
}}
.header {{
  background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
  border-bottom: 1px solid #21262d;
  padding: 20px 32px 16px;
  text-align: center;
}}
.header h1 {{
  font-size: 26px; font-weight: 700; margin-bottom: 6px;
  background: linear-gradient(90deg, #e74c3c, #f39c12);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.header .subtitle {{ font-size: 13px; color: #6e7681; }}
.stats {{
  display: flex; justify-content: center; gap: 48px;
  padding: 14px 32px; background: #161b22;
  border-bottom: 1px solid #21262d; flex-wrap: wrap;
}}
.stat-item {{ text-align: center; }}
.stat-val  {{ font-size: 22px; font-weight: 700; margin-bottom: 2px; }}
.stat-lbl  {{ font-size: 12px; color: #6e7681; }}
.up   {{ color: #e74c3c; }}
.down {{ color: #2ecc71; }}
.container {{ max-width: 1440px; margin: 0 auto; padding: 12px 16px; }}
.chart-box {{
  background: #161b22; border-radius: 8px;
  border: 1px solid #21262d;
  padding: 12px; margin-bottom: 10px;
}}
#kline-chart  {{ width: 100%; height: 520px; }}
#vol-chart   {{ width: 100%; height: 180px; }}
.footer {{
  text-align: center; padding: 18px; color: #484f58; font-size: 12px;
  border-top: 1px solid #21262d; margin-top: 8px;
}}
@media (max-width:768px) {{
  .header h1 {{ font-size: 18px; }}
  .stats {{ gap: 16px; }}
  .stat-val {{ font-size: 16px; }}
  #kline-chart {{ height: 360px; }}
  #vol-chart  {{ height: 130px; }}
}}
</style>
</head>
<body>

<div class="header">
  <h1>中际旭创 &nbsp;300308.SZ</h1>
  <div class="subtitle">K线图 + 成交量 &nbsp;|&nbsp; {date_from} ~ {date_to} &nbsp;|&nbsp; 共 {n_days} 个交易日</div>
</div>

<div class="stats">
  <div class="stat-item">
    <div class="stat-val up">¥{end_p:.2f}</div>
    <div class="stat-lbl">最新收盘</div>
  </div>
  <div class="stat-item">
    <div class="stat-val">¥{start_p:.2f}</div>
    <div class="stat-lbl">期初收盘</div>
  </div>
  <div class="stat-item">
    <div class="stat-val {"up" if chg>=0 else "down"}">{"+" if chg>=0 else ""}{chg:.2f}</div>
    <div class="stat-lbl">期间涨跌</div>
  </div>
  <div class="stat-item">
    <div class="stat-val {"up" if chg_pct>=0 else "down"}">{"+" if chg_pct>=0 else ""}{chg_pct:.2f}%</div>
    <div class="stat-lbl">涨跌幅</div>
  </div>
  <div class="stat-item">
    <div class="stat-val up">¥{max(highs):.2f}</div>
    <div class="stat-lbl">区间最高</div>
  </div>
  <div class="stat-item">
    <div class="stat-val down">¥{min(lows):.2f}</div>
    <div class="stat-lbl">区间最低</div>
  </div>
</div>

<div class="container">
  <div class="chart-box">
    <div id="kline-chart"></div>
  </div>
  <div class="chart-box">
    <div id="vol-chart"></div>
  </div>
</div>

<div class="footer">
  数据来源: Tushare Pro &nbsp;|&nbsp; 中际旭创 300308.SZ &nbsp;|&nbsp; 生成: {date_to}<br>
  本页面仅供学习参考，不构成投资建议
</div>

<script>
{js}

var UP   = "#e74c3c";
var DOWN = "#2ecc71";

/* ---- K-line data: [open, close, low, high] ---- */
var klineData = [];
for (var i = 0; i < dates.length; i++) {{
  klineData.push([opens[i], closes[i], lows[i], highs[i]]);
}}

/* ---- MA helpers ---- */
function calcMA(period) {{
  var r = [];
  for (var i = 0; i < closes.length; i++) {{
    if (i < period - 1) {{ r.push(null); continue; }}
    var s = 0;
    for (var j = 0; j < period; j++) s += closes[i - j];
    r.push(+(s / period).toFixed(2));
  }}
  return r;
}}
var ma5  = calcMA(5);
var ma10 = calcMA(10);
var ma20 = calcMA(20);

/* ---- Sync zoom between two charts ---- */
var ZOOM_START = 50;
var ZOOM_END   = 100;

/* ============================
   K-line chart (main)
   ============================ */
var kChart = echarts.init(document.getElementById("kline-chart"));
var kOption = {{
  backgroundColor: "#161b22",
  animation: true,
  tooltip: {{
    trigger: "axis",
    axisPointer: {{ type: "cross", crossStyle: {{ color: "#484f58" }} }},
    backgroundColor: "rgba(13,17,23,0.95)",
    borderColor: "#21262d",
    textStyle:   {{ color: "#c9d1d9", fontSize: 13 }},
    formatter: function (params) {{
      var i = params[0].dataIndex;
      var c = pcts[i];
      var col = c >= 0 ? UP : DOWN;
      return (
        '<div style="font-size:13px;line-height:1.9;padding:4px 8px">' +
        '<b>' + dates[i] + '</b><br>' +
        '开盘 <b>' + opens[i].toFixed(2) + '</b><br>' +
        '最高 <b style="color:' + UP   + '">' + highs[i].toFixed(2) + '</b><br>' +
        '最低 <b style="color:' + DOWN + '">' + lows[i].toFixed(2)  + '</b><br>' +
        '收盘 <b style="color:' + col + ';font-size:15px">' + closes[i].toFixed(2) + '</b><br>' +
        '涨跌 <b style="color:' + col + '">' + (c >= 0 ? "+" : "") + c.toFixed(2) + '%</b><br>' +
        '成交额 <b>' + amounts[i] + '</b> 万元' +
        '</div>'
      );
    }}
  }},
  legend: {{
    data: ["K线", "MA5", "MA10", "MA20"],
    top: 6, left: 60,
    textStyle: {{ color: "#6e7681", fontSize: 12 }},
    itemWidth: 20, itemHeight: 12
  }},
  grid: {{ left: "7%", right: "3%", top: 48, bottom: 8 }},
  xAxis: {{
    type: "category",
    data: dates,
    axisLine:       {{ lineStyle: {{ color: "#21262d" }} }},
    axisLabel:      {{ color: "#484f58", fontSize: 10,
                     formatter: function(v){{ return v.substring(5); }},
                     rotate: 45 }},
    axisTick:       {{ show: false }},
    splitLine:      {{ show: false }}
  }},
  yAxis: {{
    type: "value",
    name: "价格 (¥)",
    nameTextStyle:  {{ color: "#484f58", fontSize: 11, padding: [0,0,0,0] }},
    scale: true,
    splitLine:     {{ lineStyle: {{ color: "#21262d", type: "dashed" }} }},
    axisLabel:      {{ color: "#484f58", fontSize: 11,
                     formatter: "¥{{value}}" }},
    axisLine:       {{ show: false }}
  }},
  dataZoom: [
    {{ type: "inside",  start: ZOOM_START, end: ZOOM_END, xAxisIndex: 0 }},
    {{ type: "slider", start: ZOOM_START, end: ZOOM_END,
       height: 0, bottom: 0 }}
  ],
  series: [
    {{
      name: "K线",
      type: "candlestick",
      data: klineData,
      itemStyle: {{
        color:  UP,          /* close >= open → 实心红 */
        color0: DOWN,        /* close <  open → 实心绿 */
        borderColor:     UP,
        borderColor0:    DOWN,
        borderWidth:     1
      }},
      emphasis: {{
        itemStyle: {{
          shadowBlur: 4,
          shadowColor: "rgba(255,255,255,0.15)"
        }}
      }}
    }},
    {{
      name: "MA5",
      type: "line",
      data: ma5,
      smooth: false,
      lineStyle: {{ width: 1.2, color: "#e67e22" }},
      itemStyle:  {{ color: "#e67e22" }},
      symbol: "none",
      z: 5
    }},
    {{
      name: "MA10",
      type: "line",
      data: ma10,
      smooth: false,
      lineStyle: {{ width: 1.2, color: "#a29bfe" }},
      itemStyle:  {{ color: "#a29bfe" }},
      symbol: "none",
      z: 5
    }},
    {{
      name: "MA20",
      type: "line",
      data: ma20,
      smooth: false,
      lineStyle: {{ width: 1.5, color: "#1abc9c" }},
      itemStyle:  {{ color: "#1abc9c" }},
      symbol: "none",
      z: 5
    }}
  ]
}};

/* ============================
   Volume chart (bottom)
   ============================ */
var vChart = echarts.init(document.getElementById("vol-chart"));
var vOption = {{
  backgroundColor: "#161b22",
  animation: true,
  tooltip: {{
    trigger: "axis",
    backgroundColor: "rgba(13,17,23,0.95)",
    borderColor: "#21262d",
    textStyle:   {{ color: "#c9d1d9", fontSize: 12 }},
    formatter: function (params) {{
      var i = params[0].dataIndex;
      return dates[i] + "<br>成交量 <b>" + vols[i].toFixed(2) + "</b> 万手";
    }}
  }},
  grid: {{ left: "7%", right: "3%", top: 8, bottom: 24 }},
  xAxis: {{
    type: "category",
    data: dates,
    axisLabel:  {{ show: false }},
    axisLine:   {{ lineStyle: {{ color: "#21262d" }} }},
    axisTick:   {{ show: false }},
    splitLine:  {{ show: false }}
  }},
  yAxis: {{
    type: "value",
    name: "万手",
    nameTextStyle: {{ color: "#484f58", fontSize: 11 }},
    splitLine:    {{ lineStyle: {{ color: "#21262d", type: "dashed" }} }},
    axisLabel:    {{ color: "#484f58", fontSize: 10 }},
    axisLine:     {{ show: false }}
  }},
  dataZoom: [
    {{ type: "inside",  start: ZOOM_START, end: ZOOM_END, xAxisIndex: 0 }},
    {{ type: "slider", start: ZOOM_START, end: ZOOM_END,
       height: 20, bottom: 2 }}
  ],
  series: [{{
    type: "bar",
    data: vols.map(function(v, i) {{
      return {{
        value: v,
        itemStyle: {{
          color: pcts[i] >= 0
            ? "rgba(231,76,60,0.65)"
            : "rgba(46,204,113,0.65)"
        }}
      }};
    }}),
    barWidth: "60%"
  }}]
}};

/* ---- Render ---- */
kChart.setOption(kOption);
vChart.setOption(vOption);

/* ---- Sync zoom ---- */
kChart.group = "klineSync";
vChart.group = "klineSync";
echarts.connect("klineSync");

/* ---- Responsive ---- */
window.addEventListener("resize", function () {{
  kChart.resize();
  vChart.resize();
}});
</script>
</body>
</html>"""

OUT = os.path.join(os.path.dirname(__file__), "zhongji_xuchuang_kline.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[OK] Generated: {OUT}")
print(f"  Days : {n_days}")
print(f"  Range: {date_from} ~ {date_to}")
print(f"  Close: {start_p:.2f} -> {end_p:.2f}  ({chg:+.2f}, {chg_pct:+.2f}%)")
