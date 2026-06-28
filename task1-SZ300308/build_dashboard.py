import json

# 读取数据
with open('zhongji_xuchuang_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

start_date = data[0]['trade_date']
end_date = data[-1]['trade_date']
count = len(data)
raw_json = json.dumps(data, ensure_ascii=False)

css = """<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #0f1923; color: #e1e5ea; padding: 20px; }
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #1e3050; }
.header h1 { font-size: 22px; font-weight: 600; color: #e1e5ea; }
.header .subtitle { font-size: 13px; color: #6b7b8d; margin-top: 4px; }
.stats { display: flex; gap: 24px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-card { background: #162230; border: 1px solid #1e3050; border-radius: 8px; padding: 14px 20px; min-width: 150px; }
.stat-card .label { font-size: 12px; color: #6b7b8d; margin-bottom: 6px; }
.stat-card .value { font-size: 22px; font-weight: 700; }
.up { color: #ef5350; } .down { color: #26a69a; }
.chart-container { background: #162230; border: 1px solid #1e3050; border-radius: 8px; padding: 12px; margin-bottom: 16px; }
.chart-title { font-size: 14px; font-weight: 600; color: #c5cdd5; margin-bottom: 8px; padding-left: 4px; }
#kline-chart { width: 100%; height: 480px; }
#volume-chart { width: 100%; height: 200px; }
.footer { text-align: center; font-size: 12px; color: #3a4a5a; margin-top: 20px; }
</style>"""

js = f"""<script>
var RAW_DATA = {raw_json};

(function() {{
    var data = RAW_DATA;
    var dates = data.map(function(d) {{ return d.trade_date; }});
    var volumes = data.map(function(d) {{ return d.vol; }});
    var klineData = data.map(function(d) {{ return [d.open, d.close, d.low, d.high]; }});

    var latest = data[data.length - 1];
    var first = data[0];
    var changePct = ((latest.close - first.close) / first.close * 100).toFixed(2);
    var maxPrice = Math.max.apply(null, data.map(function(d) {{ return d.high; }}));
    var minPrice = Math.min.apply(null, data.map(function(d) {{ return d.low; }}));
    var avgVol = (volumes.reduce(function(a, b) {{ return a + b; }}, 0) / volumes.length / 10000).toFixed(0);
    var isUp = latest.pct_chg >= 0;

    document.getElementById('stats').innerHTML =
        '<div class="stat-card"><div class="label">最新价 (' + latest.trade_date + ')</div>' +
        '<div class="value ' + (isUp ? 'up' : 'down') + '">' + latest.close.toFixed(2) + '</div></div>' +
        '<div class="stat-card"><div class="label">近一年涨跌幅</div>' +
        '<div class="value ' + (changePct >= 0 ? 'up' : 'down') + '">' + changePct + '%</div></div>' +
        '<div class="stat-card"><div class="label">近一年最高</div>' +
        '<div class="value up">' + maxPrice.toFixed(2) + '</div></div>' +
        '<div class="stat-card"><div class="label">近一年最低</div>' +
        '<div class="value down">' + minPrice.toFixed(2) + '</div></div>' +
        '<div class="stat-card"><div class="label">平均成交量(万手)</div>' +
        '<div class="value" style="color:#e1e5ea">' + avgVol + '</div></div>';

    var klineChart = echarts.init(document.getElementById('kline-chart'));
    klineChart.setOption({{
        backgroundColor: '#162230',
        tooltip: {{
            trigger: 'axis',
            backgroundColor: '#1e3050',
            borderColor: '#2a4060',
            textStyle: {{ color: '#e1e5ea', fontSize: 12 }},
            formatter: function(params) {{
                var p = params[0];
                var d = data[p.dataIndex];
                var up = d.close >= d.pre_close;
                var clr = up ? '#ef5350' : '#26a69a';
                return '<b>' + d.trade_date + '</b><br/>' +
                    '开盘: ' + d.open.toFixed(2) + '<br/>' +
                    '收盘: <span style="color:' + clr + '">' + d.close.toFixed(2) + '</span><br/>' +
                    '最高: ' + d.high.toFixed(2) + '<br/>' +
                    '最低: ' + d.low.toFixed(2) + '<br/>' +
                    '涨跌: ' + d.pct_chg.toFixed(2) + '%<br/>' +
                    '成交额: ' + (d.amount / 100000000).toFixed(2) + '亿';
            }}
        }},
        grid: {{ left: 60, right: 30, top: 20, bottom: 30 }},
        xAxis: {{
            type: 'category', data: dates,
            axisLine: {{ lineStyle: {{ color: '#2a4060' }} }},
            axisLabel: {{ color: '#6b7b8d', fontSize: 10, formatter: function(v) {{ return v.slice(4); }} }},
            axisTick: {{ show: false }}, splitNumber: 8
        }},
        yAxis: {{
            type: 'value',
            axisLine: {{ show: false }},
            axisLabel: {{ color: '#6b7b8d', fontSize: 10 }},
            splitLine: {{ lineStyle: {{ color: '#1e3050', type: 'dashed' }} }}
        }},
        series: [{{
            type: 'candlestick', data: klineData,
            itemStyle: {{ color: '#ef5350', color0: '#26a69a', borderColor: '#ef5350', borderColor0: '#26a69a' }}
        }}]
    }});

    var volumeChart = echarts.init(document.getElementById('volume-chart'));
    var volColors = data.map(function(d) {{ return d.close >= d.pre_close ? '#ef5350' : '#26a69a'; }});
    volumeChart.setOption({{
        backgroundColor: '#162230',
        tooltip: {{
            trigger: 'axis',
            backgroundColor: '#1e3050', borderColor: '#2a4060',
            textStyle: {{ color: '#e1e5ea', fontSize: 12 }},
            formatter: function(params) {{
                var d = data[params[0].dataIndex];
                return d.trade_date + '<br/>成交量: ' + (d.vol / 10000).toFixed(2) + '万手<br/>成交额: ' + (d.amount / 100000000).toFixed(2) + '亿';
            }}
        }},
        grid: {{ left: 60, right: 30, top: 10, bottom: 30 }},
        xAxis: {{
            type: 'category', data: dates,
            axisLine: {{ lineStyle: {{ color: '#2a4060' }} }},
            axisLabel: {{ color: '#6b7b8d', fontSize: 10, formatter: function(v) {{ return v.slice(4); }} }},
            axisTick: {{ show: false }}, splitNumber: 8
        }},
        yAxis: {{
            type: 'value',
            axisLine: {{ show: false }},
            axisLabel: {{ color: '#6b7b8d', fontSize: 10, formatter: function(v) {{ return (v / 10000).toFixed(0) + '万'; }} }},
            splitLine: {{ lineStyle: {{ color: '#1e3050', type: 'dashed' }} }}
        }},
        series: [{{
            type: 'bar',
            data: volumes.map(function(v, i) {{ return {{ value: v, itemStyle: {{ color: volColors[i] }} }}; }}),
            barWidth: '60%'
        }}]
    }});

    [klineChart, volumeChart].forEach(function(c) {{
        c.on('updateAxisPointer', function(params) {{
            var opt = params.option;
            [klineChart, volumeChart].forEach(function(chart) {{
                if (chart !== c) {{
                    chart.dispatchAction({{ type: 'updateAxisPointer', currTrigger: 'none', xAxisIndex: 0, option: opt }});
                }}
            }});
        }});
    }});

    window.addEventListener('resize', function() {{
        klineChart.resize();
        volumeChart.resize();
    }});
}})();
</script>"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中际旭创(300308.SZ) - 近一年行情</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    {css}
</head>
<body>
    <div class="header">
        <div>
            <h1>中际旭创 (300308.SZ)</h1>
            <div class="subtitle">近一年日线行情 · 数据来源：Tushare</div>
        </div>
    </div>
    <div class="stats" id="stats"></div>
    <div class="chart-container">
        <div class="chart-title">K线图</div>
        <div id="kline-chart"></div>
    </div>
    <div class="chart-container">
        <div class="chart-title">交易量（成交量）</div>
        <div id="volume-chart"></div>
    </div>
    <div class="footer">数据区间：{start_date} ~ {end_date} · 共 {count} 个交易日 · 仅作参考，不构成投资建议</div>
    {js}
</body>
</html>"""

with open('zhongji_xuchuang_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML 已生成，包含 {count} 条数据")
