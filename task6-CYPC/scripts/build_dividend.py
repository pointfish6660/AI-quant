#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate dividend history chart for 长江电力 600900.SH.

Data: data/cypc_dividend.csv
Output: outputs/cypc_dividend_history.html
"""
import csv
import json
import os
import sys
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIV_PATH = os.path.join(ROOT, "data", "cypc_dividend.csv")

# Load dividend data
dividends = []
with open(DIV_PATH, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        ex = r["ex_date"]
        dividends.append({
            "ex_date": ex,
            "date": f"{ex[:4]}-{ex[4:6]}-{ex[6:8]}",
            "year": int(ex[:4]),
            "cash_div": float(r["cash_div"]),
        })

dividends.sort(key=lambda x: x["ex_date"])

# Prepare chart data
years = list(range(2004, 2027))
yearly_div = {}
for d in dividends:
    y = d["year"]
    if y not in yearly_div:
        yearly_div[y] = 0
    yearly_div[y] += round(d["cash_div"], 4)

chart_divs = [yearly_div.get(y, 0) for y in years]
chart_years = [str(y) for y in years]

# Find min/max
max_div = max(chart_divs) if chart_divs else 0

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>长江电力 分红历史</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f7f8fa;color:#1f2937;}}
.header{{text-align:center;padding:24px 16px 12px;}}
.header h1{{font-size:24px;color:#1f2937;margin-bottom:4px;}}
.header .sub{{font-size:13px;color:#6b7280;}}
.container{{max-width:1000px;margin:0 auto;padding:0 16px;}}
.chart-box{{background:#fff;border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06);}}
#bar-chart{{width:100%;height:450px;}}
.insight-box{{background:#fff;border-radius:10px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06);}}
.insight-box h3{{font-size:16px;color:#e74c3c;margin-bottom:12px;}}
.insight-box p{{font-size:14px;line-height:1.8;color:#4b5563;}}
.insight-box .highlight{{color:#e74c3c;font-weight:600;}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px;}}
table th{{text-align:left;padding:8px 10px;background:#f9fafb;color:#6b7280;font-size:12px;border-bottom:2px solid #e5e7eb;}}
table td{{padding:8px 10px;border-bottom:1px solid #f3f4f6;}}
table tr:hover{{background:#f9fafb;}}
.footer{{text-align:center;padding:14px;color:#9ca3af;font-size:11px;border-top:1px solid #e5e7eb;margin-top:6px;}}
</style>
</head>
<body>
<div class="header">
  <h1>长江电力 (600900.SH) 分红历史</h1>
  <div class="sub">2004 - 2026 | 共 {len(dividends)} 次分红实施 | 数据来源: Tushare</div>
</div>

<div class="container">
  <div class="insight-box">
    <h3>分红摘要</h3>
    <p>长江电力自2003年上市以来，保持了<span class="highlight">连续23年现金分红</span>的纪录（含2004年首次实施）。</p>
    <p>每股分红从2004年的¥0.072 增长至2024年的¥0.82，<span class="highlight">增长超11倍</span>，年化复合增长率约12%。</p>
    <p>公司承诺分红率不低于70%，近年实际分红率更高。2024年起改为<span class="highlight">半年度分红</span>模式，进一步提升投资者现金流回报。</p>
  </div>

  <div class="chart-box">
    <div id="bar-chart"></div>
  </div>

  <div class="insight-box">
    <h3>历年分红明细</h3>
    <table>
      <tr><th>除权日</th><th>年度</th><th>每股分红 (¥)</th><th>累计分红 (¥)</th></tr>
'''
# Build table rows
cum = 0
for d in dividends:
    cum += d["cash_div"]
    html += f'      <tr><td>{d["date"]}</td><td>{d["year"]}</td><td style="color:#e74c3c;font-weight:600">¥{d["cash_div"]:.4f}</td><td>¥{cum:.4f}</td></tr>\n'

html += f'''    </table>
    <p style="margin-top:12px;font-size:14px;color:#4b5563;">上市以来累计每股分红约 <span class="highlight">¥{cum:.2f}</span>（含税），若持有10000股至今，累计获得分红约 <span class="highlight">¥{cum*10000:,.0f}</span>。</p>
  </div>
</div>

<div class="footer">
  数据来源: Tushare Pro (dividend接口) | 长江电力 600900.SH | 生成: {dividends[-1]["date"] if dividends else "N/A"}<br>
  分红数据为含税口径，仅供参考，不构成投资建议
</div>

<script>
var years = {json.dumps(chart_years)};
var cashDivs = {json.dumps(chart_divs)};

var chart = echarts.init(document.getElementById("bar-chart"));
chart.setOption({{
  tooltip: {{
    trigger: "axis",
    formatter: function(ps) {{
      return ps[0].name + "年<br>每股分红 <b style='color:#e74c3c'>¥" + ps[0].value.toFixed(4) + "</b>";
    }}
  }},
  grid: {{ left: "8%", right: "4%", top: 20, bottom: 50 }},
  xAxis: {{
    type: "category",
    data: years,
    axisLabel: {{ rotate: 45, fontSize: 10 }},
    name: "年度"
  }},
  yAxis: {{
    type: "value",
    name: "每股分红 (元)",
    axisLabel: {{ formatter: "¥{{value}}" }}
  }},
  series: [{{
    type: "bar",
    data: cashDivs.map(function(v) {{
      var color = v >= {max_div * 0.7:.4f} ? "#e74c3c" : "#f39c12";
      return {{ value: v, itemStyle: {{ color: color }} }};
    }}),
    barWidth: "60%",
    label: {{
      show: true,
      position: "top",
      formatter: function(p) {{ return p.value > 0 ? "¥" + p.value.toFixed(3) : ""; }},
      fontSize: 9,
      color: "#6b7280"
    }}
  }}]
}});
</script>
</body>
</html>
'''

OUT = os.path.join(ROOT, "outputs", "cypc_dividend_history.html")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[OK] {OUT}")
print(f"  Dividend records: {len(dividends)}")
print(f"  Year range: {years[0]} - {years[-1]}")
print(f"  Max annual: ¥{max_div:.4f}")
print(f"  Total cumulative: ¥{cum:.2f}")
