"""Build comprehensive ECharts analysis HTML for Tencent Holdings (00700.HK)."""
import json, math, csv
from datetime import datetime

# ── Raw data from Tushare hk_daily (already fetched, processed below) ──
# Data represents 2025-06-30 ~ 2026-06-26, reverse-chronological from API
raw_data_raw = None  # Will be loaded from JSON

# Load pre-fetched data
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# ── Step 1: Read processed data ──
with open(os.path.join(data_dir, 'tencent_raw.json'), 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# Sort chronologically (oldest first)
raw_data.sort(key=lambda x: x['trade_date'])

rows = []
for r in raw_data:
    d = r['trade_date']
    rows.append({
        'date': f"{d[:4]}-{d[4:6]}-{d[6:8]}",
        'open': float(r['open']),
        'close': float(r['close']),
        'high': float(r['high']),
        'low': float(r['low']),
        'vol': float(r['vol']),
        'amount': float(r['amount']),
        'pct_chg': float(r['pct_chg'])
    })

n = len(rows)
closes = [r['close'] for r in rows]
dates = [r['date'] for r in rows]
opens = [r['open'] for r in rows]
highs = [r['high'] for r in rows]
lows = [r['low'] for r in rows]
vols_raw = [r['vol'] for r in rows]  # shares
pct_chgs = [r['pct_chg'] for r in rows]

# Vol in 万手 (Hong Kong: 1 lot = 100 shares on most, but vol field is shares)
vols = [round(v/10000, 2) for v in vols_raw]

# ── Step 2: Calculate Technical Indicators ──

def ema(data, period):
    """Calculate EMA."""
    result = [None] * len(data)
    if len(data) < period:
        return result
    # SMA as first EMA
    sma = sum(data[:period]) / period
    result[period-1] = sma
    multiplier = 2 / (period + 1)
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i-1]) * multiplier + result[i-1]
    return result

def sma(data, period):
    """Calculate SMA."""
    result = [None] * len(data)
    for i in range(period-1, len(data)):
        result[i] = sum(data[i-period+1:i+1]) / period
    return result

def bollinger_bands(data, period=20, std_dev=2):
    """Calculate Bollinger Bands."""
    ma = sma(data, period)
    upper = [None] * len(data)
    lower = [None] * len(data)
    mid = ma[:]
    for i in range(period-1, len(data)):
        window = data[i-period+1:i+1]
        mean = sum(window) / period
        variance = sum((x - mean)**2 for x in window) / period
        std = math.sqrt(variance)
        upper[i] = mean + std_dev * std
        lower[i] = mean - std_dev * std
    return upper, mid, lower

def macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD."""
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    dif = [None] * len(data)
    for i in range(len(data)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif[i] = ema_fast[i] - ema_slow[i]
    dea = ema([d if d is not None else 0 for d in dif], signal)
    # Fix DEA: first valid at slow+signal-2
    for i in range(slow + signal - 3):
        dea[i] = None
    hist = [None] * len(data)
    for i in range(len(data)):
        if dif[i] is not None and dea[i] is not None:
            hist[i] = 2 * (dif[i] - dea[i])
    return dif, dea, hist

def rsi(data, period=14):
    """Calculate RSI."""
    result = [None] * len(data)
    if len(data) < period + 1:
        return result
    gains = []
    losses = []
    for i in range(1, len(data)):
        change = data[i] - data[i-1]
        gains.append(change if change > 0 else 0)
        losses.append(abs(change) if change < 0 else 0)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains) + 1):
        if avg_loss == 0:
            result[i] = 100
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))
        if i < len(gains):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    return result

def find_crosses(fast_line, slow_line, dates):
    """Find golden cross (金叉) and death cross (死叉) points."""
    gc, dc = [], []
    for i in range(1, len(dates)):
        if fast_line[i] is None or slow_line[i] is None:
            continue
        if fast_line[i-1] is None or slow_line[i-1] is None:
            continue
        # Golden cross: fast crosses above slow
        if fast_line[i-1] <= slow_line[i-1] and fast_line[i] > slow_line[i]:
            gc.append({"coord": [dates[i], closes[i]], "value": "金叉"})
        # Death cross: fast crosses below slow
        if fast_line[i-1] >= slow_line[i-1] and fast_line[i] < slow_line[i]:
            dc.append({"coord": [dates[i], closes[i]], "value": "死叉"})
    return gc, dc

# Calculate all indicators
ma5 = sma(closes, 5)
ma10 = sma(closes, 10)
ma20 = sma(closes, 20)
bb_upper, bb_mid, bb_lower = bollinger_bands(closes, 20, 2)
dif, dea, macd_hist = macd(closes)
rsi_14 = rsi(closes, 14)

# Golden/Death crosses (MA5 vs MA10)
gc_markers, dc_markers = find_crosses(ma5, ma10, dates)

# MACD Golden/Death crosses (DIF vs DEA)
macd_gc, macd_dc = find_crosses(dif, dea, dates)

# ── Step 3: Statistics ──
start_price = closes[0]
end_price = closes[-1]
total_change = end_price - start_price
total_pct = (total_change / start_price) * 100
max_high = max(highs)
min_low = min(lows)
max_close = max(closes)
min_close = min(closes)

# Recent 20-day high/low
r20_closes = closes[-20:] if n >= 20 else closes
r20_hi = max(r20_closes)
r20_lo = min(r20_closes)

# Latest values
latest_ma5 = ma5[-1] if ma5[-1] is not None else 0
latest_ma10 = ma10[-1] if ma10[-1] is not None else 0
latest_ma20 = ma20[-1] if ma20[-1] is not None else 0
latest_dif = dif[-1] if dif[-1] is not None else 0
latest_dea = dea[-1] if dea[-1] is not None else 0
latest_macd_hist = macd_hist[-1] if macd_hist[-1] is not None else 0
latest_rsi = rsi_14[-1] if rsi_14[-1] is not None else 50
latest_bb_upper = bb_upper[-1] if bb_upper[-1] is not None else 0
latest_bb_mid = bb_mid[-1] if bb_mid[-1] is not None else 0
latest_bb_lower = bb_lower[-1] if bb_lower[-1] is not None else 0

# Volume statistics
vol_20_avg = sum(vols[-20:]) / 20 if n >= 20 else sum(vols) / n
latest_vol = vols[-1]

# MA arrangement
ma_arrangement = "多头排列▲" if latest_ma5 > latest_ma10 > latest_ma20 else "空头排列▼" if latest_ma5 < latest_ma10 < latest_ma20 else "交叉震荡"

# MACD status
macd_status = "多头 (DIF>DEA)" if latest_dif > latest_dea else "空头 (DIF<DEA)"
if latest_macd_hist > 0:
    macd_hist_trend = "红柱扩大" if (n >= 2 and macd_hist[-2] is not None and macd_hist[-1] > macd_hist[-2]) else "红柱缩小"
else:
    macd_hist_trend = "绿柱扩大" if (n >= 2 and macd_hist[-2] is not None and macd_hist[-1] < macd_hist[-2]) else "绿柱缩小"

# BB position
if end_price >= latest_bb_upper * 0.98:
    bb_status = "接近上轨<br><span>超买</span>"
elif end_price <= latest_bb_lower * 1.02:
    bb_status = "接近下轨<br><span>超卖</span>"
elif end_price >= latest_bb_mid:
    bb_status = "上轨~中轨<br><span>偏强</span>"
else:
    bb_status = "中轨~下轨<br><span>偏弱</span>"

# Last golden/death cross dates
last_gc_date = gc_markers[-1]['coord'][0] if gc_markers else "无"
last_dc_date = dc_markers[-1]['coord'][0] if dc_markers else "无"

# RSI status
rsi_status = "超买" if latest_rsi > 70 else "超卖" if latest_rsi < 30 else "中性"

# Volume status
if latest_vol > vol_20_avg * 1.5:
    vol_status = "放量"
elif latest_vol < vol_20_avg * 0.5:
    vol_status = "缩量"
else:
    vol_status = "正常"

# Capitalization: shares × price; approximate 93.4B shares outstanding
total_shares = 93.4e8  # ~9.34 billion
market_cap = end_price * total_shares / 1e8  # in 亿 HKD

# Signals for recent period
ma5_vals = json.dumps([round(v, 2) if v is not None else None for v in ma5])
ma10_vals = json.dumps([round(v, 2) if v is not None else None for v in ma10])
ma20_vals = json.dumps([round(v, 2) if v is not None else None for v in ma20])
bb_upper_vals = json.dumps([round(v, 2) if v is not None else None for v in bb_upper])
bb_mid_vals = json.dumps([round(v, 2) if v is not None else None for v in bb_mid])
bb_lower_vals = json.dumps([round(v, 2) if v is not None else None for v in bb_lower])
dif_vals = json.dumps([round(v, 2) if v is not None else None for v in dif])
dea_vals = json.dumps([round(v, 2) if v is not None else None for v in dea])
macd_hist_vals = json.dumps([round(v, 2) if v is not None else None for v in macd_hist])

# ── Step 4: Embed into data JSON ──
D = {
    "dates": dates,
    "opens": [round(v, 2) for v in opens],
    "closes": [round(v, 2) for v in closes],
    "highs": [round(v, 2) for v in highs],
    "lows": [round(v, 2) for v in lows],
    "vols": vols,
    "pcts": [round(v, 2) for v in pct_chgs],
    "ma5": json.loads(ma5_vals),
    "ma10": json.loads(ma10_vals),
    "ma20": json.loads(ma20_vals),
    "bbUpper": json.loads(bb_upper_vals),
    "bbMid": json.loads(bb_mid_vals),
    "bbLower": json.loads(bb_lower_vals),
    "dif": json.loads(dif_vals),
    "dea": json.loads(dea_vals),
    "macdHist": json.loads(macd_hist_vals),
    "gcMarkers": gc_markers,
    "dcMarkers": dc_markers,
    "allHi": round(max_high, 2),
    "allLo": round(min_low, 2),
    "r20Hi": round(r20_hi, 2),
    "r20Lo": round(r20_lo, 2),
}

data_json = json.dumps(D, ensure_ascii=False)

# ── Step 5: Prepare template variables ──
sign = '+' if total_change >= 0 else ''
up_class = 'up' if end_price >= start_price else 'down'

# Recent 5 days recap
recent_5 = rows[-5:]
recap_lines = []
for r in recent_5:
    pct = r['pct_chg']
    arrow = '▲' if pct >= 0 else '▼'
    recap_lines.append(f"{r['date']} {arrow}{abs(pct):.1f}%")
recap_text = ' | '.join(recap_lines)

# Determine overall trend
if latest_ma5 > latest_ma10 > latest_ma20:
    trend_summary = "均线多头排列，中长期上升趋势完好。"
elif latest_ma5 < latest_ma10 < latest_ma20:
    trend_summary = "均线空头排列，短期弱势调整中。"
else:
    trend_summary = "均线交叉震荡，方向不明确。"

# MACD analysis
if latest_dif > latest_dea:
    macd_detail = f"MACD处于多头状态（DIF={latest_dif:.2f} > DEA={latest_dea:.2f}），"
    if macd_hist_trend == "红柱扩大":
        macd_detail += "红柱扩大，上涨动能增强。"
    elif macd_hist_trend == "红柱缩小":
        macd_detail += "但红柱缩短，上涨动能减弱。"
    else:
        macd_detail += "短期动能方向需观察。"
else:
    macd_detail = f"MACD处于空头状态（DIF={latest_dif:.2f} < DEA={latest_dea:.2f}），"
    if macd_hist_trend == "绿柱扩大":
        macd_detail += "绿柱扩大，下跌动能仍在释放中。"
    elif macd_hist_trend == "绿柱缩小":
        macd_detail += "但绿柱缩短，下跌动能减弱。"
    else:
        macd_detail += "短期动能方向需观察。"

# BB analysis
if end_price >= latest_bb_upper * 0.98:
    bb_detail = f"股价接近布林上轨({latest_bb_upper:.2f})，属于超买区域，短期回调风险增大。中轨支撑在{latest_bb_mid:.2f}，下轨在{latest_bb_lower:.2f}。"
elif end_price <= latest_bb_lower * 1.02:
    bb_detail = f"股价接近布林下轨({latest_bb_lower:.2f})，属于超卖区域，技术性反弹可期。中轨阻力在{latest_bb_mid:.2f}，上轨在{latest_bb_upper:.2f}。"
elif end_price >= latest_bb_mid:
    bb_detail = f"股价位于布林上轨~中轨之间，处于偏强区域。上轨压力{latest_bb_upper:.2f}，中轨支撑{latest_bb_mid:.2f}，下轨{latest_bb_lower:.2f}。"
else:
    bb_detail = f"股价位于布林中轨~下轨之间，处于偏弱区域。中轨阻力{latest_bb_mid:.2f}，下轨支撑{latest_bb_lower:.2f}，上轨{latest_bb_upper:.2f}。"

# ── Step 6: Generate HTML ──
sign_class = 'up' if total_pct >= 0 else 'down'

# Determine operation advice based on indicators
# Buy signal conditions
buy_signals = 0
sell_signals = 0
if latest_ma5 > latest_ma10 > latest_ma20:
    buy_signals += 1
else:
    sell_signals += 1
if latest_dif > latest_dea:
    buy_signals += 1
else:
    sell_signals += 1
if latest_rsi < 30:
    buy_signals += 1
elif latest_rsi > 70:
    sell_signals += 1
if end_price > latest_bb_mid:
    buy_signals += 1
else:
    sell_signals += 1

vol_ratio = latest_vol / vol_20_avg
# Volume analysis for recent 5 days
recent_5_vols = vols[-5:]
recent_5_avg_vol = sum(recent_5_vols) / 5

# Recent price trend (last 5 days)
recent_pcts = pct_chgs[-5:]
down_days = sum(1 for p in recent_pcts if p < -1)
up_days = sum(1 for p in recent_pcts if p > 1)

# Determine core advice
if down_days >= 3:
    core_advice = "观望为主，等待止跌信号"
    advice_color = "#f39c12"
    aggressive_zone = f"¥{closes[-1]-closes[-1]*0.02:.0f} ~ ¥{closes[-1]:.0f}"
    conservative_zone = f"等待站回 ¥{latest_ma5:.0f} 以上"
    stop_loss = f"跌破 ¥{latest_bb_lower:.0f} 坚决止损"
elif buy_signals >= 3:
    core_advice = "逢低吸纳，逐步建仓"
    advice_color = "#e74c3c"
    aggressive_zone = f"¥{closes[-1]:.0f} ~ ¥{closes[-1]*1.02:.0f}"
    conservative_zone = f"回调至 ¥{latest_ma20:.0f} 以下"
    stop_loss = f"跌破 ¥{latest_ma20:.0f} 止损"
elif sell_signals >= 3:
    core_advice = "逢高减仓，控制风险"
    advice_color = "#2ecc71"
    aggressive_zone = f"反弹至 ¥{latest_ma5:.0f} ~ ¥{latest_bb_upper:.0f}"
    conservative_zone = f"观望，不追高"
    stop_loss = f"跌破 ¥{latest_ma20:.0f} 止损"
else:
    core_advice = "轻仓观望，等待方向明确"
    advice_color = "#f39c12"
    aggressive_zone = f"¥{closes[-1]*0.95:.0f} ~ ¥{closes[-1]:.0f}"
    conservative_zone = f"等待MACD金叉确认"
    stop_loss = f"跌破 ¥{latest_bb_lower:.0f} 止损"

# Recent significant events
sig_events = []
for i in range(max(0, n-20), n):
    if pct_chgs[i] > 5:
        sig_events.append((dates[i], pct_chgs[i], '大涨'))
    elif pct_chgs[i] < -5:
        sig_events.append((dates[i], pct_chgs[i], '大跌'))
    elif pct_chgs[i] > 3:
        sig_events.append((dates[i], pct_chgs[i], '上涨'))
    elif pct_chgs[i] < -3:
        sig_events.append((dates[i], pct_chgs[i], '下跌'))

# 52-week high/low
if len(closes) >= 250:
    hi_52w = max(closes[-250:])
    lo_52w = min(closes[-250:])
else:
    hi_52w = max_high
    lo_52w = min_low

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>腾讯控股 (00700.HK) 深度分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#0d1117;color:#c9d1d9;}}
.header{{background:linear-gradient(135deg,#161b22,#0d1117);border-bottom:1px solid #21262d;padding:18px 32px 12px;text-align:center;}}
.header h1{{font-size:28px;font-weight:700;margin-bottom:4px;background:linear-gradient(90deg,#e74c3c,#f39c12);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.header .subtitle{{font-size:12px;color:#6e7681;}}
.advice-section{{max-width:1200px;margin:16px auto;padding:0 16px;}}
.advice-card{{background:linear-gradient(135deg,#1a0a0a,#0d1117);border:2px solid #e74c3c;border-radius:10px;padding:20px 24px;margin-bottom:14px;}}
.advice-card h2{{font-size:20px;color:#e74c3c;margin-bottom:12px;display:flex;align-items:center;gap:8px;}}
.advice-card h2 .badge{{background:#e74c3c;color:#fff;font-size:14px;padding:2px 10px;border-radius:4px;}}
.advice-card .disclaimer{{font-size:12px;color:#e74c3c;margin-bottom:14px;padding:8px 12px;background:rgba(231,76,60,0.1);border-radius:6px;}}
.advice-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:12px;}}
.advice-item{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px 16px;}}
.advice-item .ai-title{{font-size:12px;color:#6e7681;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;}}
.advice-item .ai-value{{font-size:18px;font-weight:700;}}
.advice-item .ai-detail{{font-size:12px;color:#6e7681;margin-top:4px;line-height:1.5;}}
.levels-table{{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;}}
.levels-table th{{text-align:left;padding:6px 10px;color:#6e7681;font-size:11px;border-bottom:1px solid #21262d;}}
.levels-table td{{padding:6px 10px;border-bottom:1px solid #1a1f29;}}
.signal-bar{{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;padding:10px 24px;background:#161b22;border-bottom:1px solid #21262d;}}
.signal-card{{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 16px;text-align:center;min-width:120px;}}
.signal-card .label{{font-size:11px;color:#6e7681;margin-bottom:3px;}}
.signal-card .value{{font-size:14px;font-weight:600;}}
.up{{color:#e74c3c;}}.down{{color:#2ecc71;}}
.stats{{display:flex;justify-content:center;gap:24px;padding:10px 24px;background:#161b22;border-bottom:1px solid #21262d;flex-wrap:wrap;}}
.stat-item{{text-align:center;}}
.stat-val{{font-size:20px;font-weight:700;margin-bottom:1px;}}
.stat-lbl{{font-size:11px;color:#6e7681;}}
.container{{max-width:1440px;margin:0 auto;padding:8px 12px;}}
.chart-box{{background:#161b22;border-radius:8px;border:1px solid #21262d;padding:10px;margin-bottom:8px;}}
#kline-chart{{width:100%;height:500px;}}
#vol-chart{{width:100%;height:160px;}}
#macd-chart{{width:100%;height:200px;}}
.analysis-section{{max-width:1200px;margin:20px auto;padding:0 16px;}}
.analysis-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:20px 24px;margin-bottom:14px;line-height:1.8;font-size:14px;}}
.analysis-card h3{{font-size:18px;color:#f39c12;margin-bottom:12px;border-bottom:1px solid #21262d;padding-bottom:8px;}}
.analysis-card h4{{color:#e67e22;margin:14px 0 6px;font-size:15px;}}
.analysis-card p{{margin-bottom:10px;}}
.analysis-card ul,.analysis-card ol{{margin:8px 0 8px 20px;}}
.analysis-card li{{margin-bottom:4px;}}
.analysis-card .highlight{{color:#e74c3c;font-weight:600;}}
.analysis-card .warn{{color:#2ecc71;font-weight:600;}}
.analysis-card code{{background:#0d1117;padding:1px 6px;border-radius:3px;font-size:13px;color:#a29bfe;}}
.analysis-card table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px;}}
.analysis-card table th{{text-align:left;padding:6px 10px;background:#0d1117;color:#6e7681;font-size:11px;}}
.analysis-card table td{{padding:6px 10px;border-bottom:1px solid #1a1f29;}}
.analysis-card .tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;margin:2px;}}
.tag-bull{{background:rgba(231,76,60,0.2);color:#e74c3c;}}
.tag-bear{{background:rgba(46,204,113,0.2);color:#2ecc71;}}
.footer{{text-align:center;padding:14px;color:#484f58;font-size:11px;border-top:1px solid #21262d;margin-top:6px;}}
@media(max-width:768px){{
  .header h1{{font-size:18px;}}
  .advice-grid{{grid-template-columns:1fr;}}
  .signal-card{{padding:6px 8px;min-width:80px;}}.signal-card .value{{font-size:12px;}}
  #kline-chart{{height:350px;}}#vol-chart{{height:120px;}}#macd-chart{{height:150px;}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>腾讯控股 &nbsp;00700.HK</h1>
  <div class="subtitle">深度技术分析 &nbsp;|&nbsp; {dates[0]} ~ {dates[-1]} &nbsp;|&nbsp; 共 {n} 个交易日</div>
</div>

<div class="advice-section">
  <div class="advice-card">
    <h2><span class="badge">⚠️ 操作建议</span> 6月29日（周一）— 当前仅供参考</h2>
    <div class="disclaimer">⚠️ 以下分析基于技术面数据，仅供参考，不构成投资建议。股市有风险，投资需谨慎。</div>
    <div class="advice-grid">
      <div class="advice-item">
        <div class="ai-title">核心策略</div>
        <div class="ai-value" style="color:{advice_color}">{core_advice}</div>
        <div class="ai-detail">基于均线排列、MACD信号、RSI状态和布林带位置综合判断。最近一周涨跌天数：涨{5-down_days}天 / 跌{down_days}天。</div>
      </div>
      <div class="advice-item">
        <div class="ai-title">激进建仓区</div>
        <div class="ai-value" style="color:#e74c3c">{aggressive_zone}</div>
        <div class="ai-detail">MA20附近支撑区。若回调至此出现放量止跌信号，可轻仓试探，仓位不超过30%。</div>
      </div>
      <div class="advice-item">
        <div class="ai-title">保守建仓条件</div>
        <div class="ai-value" style="color:#3498db">{conservative_zone}</div>
        <div class="ai-detail">需同时满足：① MACD金叉或绿柱缩短 ② 站回MA5 ③ 成交量放大确认。可建仓40-50%。</div>
      </div>
      <div class="advice-item">
        <div class="ai-title">止损位</div>
        <div class="ai-value" style="color:#e74c3c">{stop_loss}</div>
        <div class="ai-detail">若跌破关键支撑且无法收回，需果断止损，避免亏损扩大。</div>
      </div>
    </div>
    <table class="levels-table" style="margin-top:16px;">
      <tr><th>点位</th><th>价格</th><th>性质</th><th>操作</th></tr>
      <tr><td style="color:#e74c3c">强阻力</td><td>HK${max_close:.2f}</td><td>区间最高收盘价</td><td>突破前不建议追高</td></tr>
      <tr><td style="color:#e74c3c">52周高</td><td>HK${hi_52w:.2f}</td><td>52周最高价</td><td>历史高位参考</td></tr>
      <tr><td style="color:#f39c12">阻力</td><td>HK${latest_ma5:.0f} ~ HK${latest_bb_upper:.0f}</td><td>MA5 / 布林上轨</td><td>收复此区转多头</td></tr>
      <tr><td style="color:#1abc9c">当前价</td><td>HK${end_price:.2f}</td><td>{dates[-1]} 收盘</td><td>—</td></tr>
      <tr><td style="color:#3498db">支撑1</td><td>HK${latest_ma20:.0f}</td><td>MA20均线</td><td>回调关键支撑</td></tr>
      <tr><td style="color:#3498db">支撑2</td><td>HK${latest_bb_lower:.0f}</td><td>布林带下轨(20日,2σ)</td><td>强支撑，若跌至此可加仓</td></tr>
      <tr><td style="color:#2ecc71">强支撑</td><td>HK${min_low:.2f}</td><td>区间最低价</td><td>极端回调目标</td></tr>
    </table>
  </div>
</div>

<div class="signal-bar">
  <div class="signal-card"><div class="label">均线状态</div><div class="value up">{ma_arrangement}</div></div>
  <div class="signal-card"><div class="label">MA5/MA10/MA20</div><div class="value">{latest_ma5:.2f}/{latest_ma10:.2f}/{latest_ma20:.2f}</div></div>
  <div class="signal-card"><div class="label">MACD</div><div class="value {'up' if latest_dif > latest_dea else 'down'}">{macd_status}<br><span style="font-size:11px">{macd_hist_trend}</span></div></div>
  <div class="signal-card"><div class="label">布林带</div><div class="value" style="color:#f39c12">{bb_status}</div></div>
  <div class="signal-card"><div class="label">最近金叉</div><div class="value up">{last_gc_date}</div></div>
  <div class="signal-card"><div class="label">最近死叉</div><div class="value down">{last_dc_date}</div></div>
  <div class="signal-card"><div class="label">RSI(14)</div><div class="value" style="color:{'#e74c3c' if latest_rsi > 70 else '#2ecc71' if latest_rsi < 30 else '#f39c12'}">{latest_rsi:.0f} ({rsi_status})</div></div>
  <div class="signal-card"><div class="label">成交量</div><div class="value">{vol_status}<br><span style="font-size:11px">{latest_vol:.1f}万手 vs 均{vol_20_avg:.1f}</span></div></div>
</div>

<div class="stats">
  <div class="stat-item"><div class="stat-val {'up' if total_change >= 0 else 'down'}">HK${end_price:.2f}</div><div class="stat-lbl">最新收盘</div></div>
  <div class="stat-item"><div class="stat-val">HK${start_price:.2f}</div><div class="stat-lbl">期初收盘</div></div>
  <div class="stat-item"><div class="stat-val {'up' if total_change >= 0 else 'down'}">{sign}{total_change:.2f}</div><div class="stat-lbl">期间涨跌</div></div>
  <div class="stat-item"><div class="stat-val {'up' if total_pct >= 0 else 'down'}">{sign}{total_pct:.2f}%</div><div class="stat-lbl">涨跌幅</div></div>
  <div class="stat-item"><div class="stat-val up">HK${max_high:.2f}</div><div class="stat-lbl">区间最高</div></div>
  <div class="stat-item"><div class="stat-val down">HK${min_low:.2f}</div><div class="stat-lbl">区间最低</div></div>
  <div class="stat-item"><div class="stat-val">HK${market_cap:.0f}亿</div><div class="stat-lbl">市值(约)</div></div>
</div>

<div class="container">
  <div class="chart-box"><div id="kline-chart"></div></div>
  <div class="chart-box"><div id="vol-chart"></div></div>
  <div class="chart-box"><div id="macd-chart"></div></div>
</div>

<div class="analysis-section">
  <div class="analysis-card">
    <h3>📊 近期盘面回顾</h3>
    <p>腾讯控股近5个交易日走势：<code>{recap_text}</code></p>
    <ul>
"""

# Add significant events
for evt in sig_events[-5:]:
    if evt is not None:
        cls = "highlight" if evt[2] in ('大涨', '下跌') else "warn" if evt[2] == '大跌' else ""
        html += f'      <li><b>{evt[0]}</b>：{evt[2]} <span class="{cls}">{evt[1]:+.2f}%</span></li>\n'

# Price change from high
if max_close > end_price:
    from_high_pct = (max_close - end_price) / max_close * 100
    html += f'    </ul>\n    <p>从区间最高收盘价HK${max_close:.2f}到当前HK${end_price:.2f}，<span class="warn">回调约 -{from_high_pct:.1f}%</span>。</p>\n'
else:
    html += f'    </ul>\n    <p>当前价格接近或处于区间高点附近，趋势偏强。</p>\n'

html += f"""  </div>

  <div class="analysis-card">
    <h3>🔍 技术面深度分析</h3>
    <h4>1. 均线系统</h4>
    <p>当前均线数值：MA5={latest_ma5:.2f} | MA10={latest_ma10:.2f} | MA20={latest_ma20:.2f}</p>
    <p>{trend_summary} MA5与MA10的距离为{abs(latest_ma5-latest_ma10):.2f}港元，{'若继续下跌，MA5可能下穿MA10形成死叉' if latest_ma5 > latest_ma10 and latest_ma5-latest_ma10 < 5 else ''}</p>
    <h4>2. MACD指标</h4>
    <p>DIF={latest_dif:.2f} | DEA={latest_dea:.2f} | MACD柱={latest_macd_hist:.2f}</p>
    <p>{macd_detail}</p>
    <h4>3. 布林带分析</h4>
    <p>布林上轨={latest_bb_upper:.2f} | 中轨={latest_bb_mid:.2f} | 下轨={latest_bb_lower:.2f}</p>
    <p>{bb_detail}</p>
    <h4>4. 成交量分析</h4>
    <p>最新成交{latest_vol:.1f}万手，20日均量{vol_20_avg:.1f}万手，量比{vol_ratio:.2f}。</p>
    <h4>5. 综合判断</h4>
    <p><span class="tag {'tag-bull' if buy_signals >= 3 else 'tag-bear' if sell_signals >= 3 else ''}">{'短线偏多' if buy_signals >= 3 else '短线偏空' if sell_signals >= 3 else '短线中性'}</span></p>
    <p>技术面综合评分：多头信号 {buy_signals} 个，空头信号 {sell_signals} 个。</p>
  </div>

  <div class="analysis-card">
    <h3>🏢 基本面分析</h3>
    <h4>公司概况</h4>
    <p><b>腾讯控股有限公司</b>（Tencent Holdings Limited, HK:0700），成立于1998年11月，2004年6月16日在香港联交所主板上市。总部位于中国深圳，是全球领先的互联网科技公司。</p>
    <p><b>核心业务</b>：社交平台（微信/WeChat、QQ）、网络游戏（国内+国际）、金融科技（微信支付、理财通）、云服务（腾讯云）、数字内容（腾讯视频、腾讯音乐）、企业服务等。</p>
    <p><b>行业地位</b>：中国互联网行业<span class="highlight">绝对龙头</span>，市值长期位居港股第一。微信月活用户超过13亿，是中国最大的社交平台。全球游戏收入排名第一。</p>
    <h4>核心投资逻辑</h4>
    <ol>
      <li><b>超级APP生态壁垒</b>：微信构建了涵盖社交、支付、电商、内容、小程序的超级生态，用户迁移成本极高，是腾讯最核心的<span class="highlight">护城河</span>。</li>
      <li><b>游戏业务全球化</b>：通过投资Riot Games、Epic Games、Supercell等，腾讯已成为全球最大游戏公司。海外游戏收入占比持续提升。</li>
      <li><b>AI大模型布局</b>：推出混元大模型，深度整合到微信、腾讯云、腾讯会议等产品中，AI能力有望打开新增长空间。</li>
      <li><b>视频号商业化加速</b>：视频号DAU持续增长，广告和电商变现进入加速期，有望成为新的增长引擎。</li>
      <li><b>投资帝国价值重估</b>：持有美团、拼多多、京东、快手等大量上市公司股权，投资组合价值约万亿级别。</li>
    </ol>
    <h4>风险因素</h4>
    <ol>
      <li><b>监管政策风险</b>：互联网平台反垄断、数据安全、未成年人保护等监管政策可能影响业务增长</li>
      <li><b>游戏版号不确定性</b>：国内游戏版号审批节奏对游戏业务收入有直接影响</li>
      <li><b>宏观经济压力</b>：广告和云服务收入与宏观经济高度相关，经济下行压力影响企业IT支出</li>
      <li><b>竞争加剧</b>：字节跳动（抖音/TikTok）在用户时长和广告份额上持续竞争</li>
      <li><b>地缘政治风险</b>：中美科技博弈可能影响海外游戏和云业务拓展</li>
    </ol>
  </div>

  <div class="analysis-card">
    <h3>📖 基础知识讲解</h3>
    <h4>什么是K线？</h4>
    <p><b>K线（蜡烛图）</b> 是一种记录价格走势的图表，由日本的米商本间宗久在18世纪发明。每根K线包含<span class="highlight">四个价格</span>：开盘价、收盘价、最高价、最低价。</p>
    <p><b>阳线（红/白）</b>：收盘 > 开盘，表示价格上涨。实体部分用红色填充。<br>
    <b>阴线（绿/黑）</b>：收盘 < 开盘，表示价格下跌。实体部分用绿色填充。<br>
    （注：A股/港股习惯红涨绿跌，与美股相反）</p>
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
      <tr><td>MA（移动平均线）</td><td>趋势方向，金叉/死叉</td><td style="color:{'#e74c3c' if latest_ma5 > latest_ma10 else '#2ecc71'}">{'多头排列' if latest_ma5 > latest_ma10 > latest_ma20 else '空头排列' if latest_ma5 < latest_ma10 < latest_ma20 else '交叉震荡'}</td></tr>
      <tr><td>MACD</td><td>趋势强度，多空转换</td><td style="color:{'#e74c3c' if latest_dif > latest_dea else '#2ecc71'}">{'多头信号' if latest_dif > latest_dea else '空头信号'}</td></tr>
      <tr><td>布林带</td><td>超买/超卖，波动范围</td><td style="color:#f39c12">{'超买' if end_price >= latest_bb_upper*0.98 else '超卖' if end_price <= latest_bb_lower*1.02 else '偏强' if end_price >= latest_bb_mid else '偏弱'}区域</td></tr>
      <tr><td>RSI(14)</td><td>超买(>70)/超卖(<30)</td><td style="color:{'#e74c3c' if latest_rsi > 70 else '#2ecc71' if latest_rsi < 30 else '#f39c12'}">{latest_rsi:.0f} {rsi_status}</td></tr>
      <tr><td>成交量</td><td>趋势确认，放量/缩量</td><td>{vol_status}{' (警示)' if latest_vol > vol_20_avg * 1.5 and pct_chgs[-1] < -1 else ''}</td></tr>
    </table>
    <p style="margin-top:10px;"><b>基本面 vs 技术面</b>：基本面告诉你<span class="highlight">"买什么"</span>、技术面告诉你<span class="highlight">"什么时候买"</span>。两者结合是最有效的投资方法。</p>
  </div>

  <div class="analysis-card">
    <h3>⚠️ 风险提示</h3>
    <p style="color:#6e7681;font-size:13px;">
      本页面所有分析基于公开市场数据和技术指标计算，仅供学习研究参考，<span class="highlight">不构成任何投资建议</span>。<br><br>
      股票投资具有高风险性，腾讯控股（00700.HK）过去一年的走势不代表未来收益，<span class="warn">投资者可能面临本金损失</span>。<br><br>
      互联网行业受宏观经济、监管政策、技术迭代、国际关系等多重因素影响，<span class="warn">投资风险不可忽视</span>。<br><br>
      请根据自身风险承受能力独立做出投资决策。
    </p>
  </div>
</div>

<div class="footer">
  数据来源: Tushare Pro &nbsp;|&nbsp; 腾讯控股 00700.HK &nbsp;|&nbsp; 生成: {datetime.now().strftime('%Y-%m-%d')}<br>
  技术指标: K线 + 布林带 + MACD + RSI &nbsp;|&nbsp; 红涨绿跌 &nbsp;|&nbsp; 仅供参考，不构成投资建议
</div>

<script>
// ── All data in one JSON blob ──
var D = {data_json};

var UP = "#e74c3c", DOWN = "#2ecc71";
var ZS = 50, ZE = 100;

// Build candlestick data
var kl = [];
for (var i = 0; i < D.dates.length; i++) {{
  kl.push([D.opens[i], D.closes[i], D.lows[i], D.highs[i]]);
}}

// ── K-line Chart ──
var kch = echarts.init(document.getElementById("kline-chart"));
kch.setOption({{
  backgroundColor: "#161b22",
  animation: true,
  tooltip: {{
    trigger: "axis",
    axisPointer: {{ type: "cross" }},
    backgroundColor: "rgba(13,17,23,0.96)",
    borderColor: "#21262d",
    textStyle: {{ color: "#c9d1d9", fontSize: 13 }},
    formatter: function(ps) {{
      var i = ps[0].dataIndex;
      var c = D.pcts[i];
      var col = c >= 0 ? UP : DOWN;
      var s = '<div style="font-size:13px;line-height:2"><b>' + D.dates[i] + '</b><br>';
      s += 'O <b>' + D.opens[i].toFixed(2) + '</b> H <b style="color:' + UP + '">' + D.highs[i].toFixed(2) + '</b><br>';
      s += 'L <b style="color:' + DOWN + '">' + D.lows[i].toFixed(2) + '</b> C <b style="color:' + col + ';font-size:15px">' + D.closes[i].toFixed(2) + '</b><br>';
      s += '涨跌 <b style="color:' + col + '">' + (c >= 0 ? "+" : "") + c.toFixed(2) + '%</b><br>';
      if (D.bbUpper[i] != null) s += 'BB上' + D.bbUpper[i].toFixed(2) + ' 中' + D.bbMid[i].toFixed(2) + ' 下' + D.bbLower[i].toFixed(2) + '<br>';
      if (D.dif[i] != null) s += 'DIF ' + D.dif[i].toFixed(2) + ' DEA ' + D.dea[i].toFixed(2);
      return s + '</div>';
    }}
  }},
  legend: {{ data: ["K线", "MA5", "MA10", "MA20", "BB上轨", "BB下轨"], top: 4, left: 50, textStyle: {{ color: "#6e7681", fontSize: 11 }}, itemWidth: 18, itemHeight: 10 }},
  grid: {{ left: "7%", right: "3%", top: 42, bottom: 8 }},
  xAxis: {{ type: "category", data: D.dates, axisLine: {{ lineStyle: {{ color: "#21262d" }} }}, axisLabel: {{ color: "#484f58", fontSize: 10, formatter: function(v) {{ return v.substring(5); }}, rotate: 45 }}, axisTick: {{ show: false }}, splitLine: {{ show: false }} }},
  yAxis: {{ type: "value", name: "价格(HKD)", nameTextStyle: {{ color: "#484f58", fontSize: 11 }}, scale: true, splitLine: {{ lineStyle: {{ color: "#21262d", type: "dashed" }} }}, axisLabel: {{ color: "#484f58", fontSize: 11 }}, axisLine: {{ show: false }} }},
  dataZoom: [
    {{ type: "inside", start: ZS, end: ZE, xAxisIndex: 0 }},
    {{ type: "slider", start: ZS, end: ZE, height: 0, bottom: 0 }}
  ],
  series: [
    {{ name: "K线", type: "candlestick", data: kl, itemStyle: {{ color: UP, color0: DOWN, borderColor: UP, borderColor0: DOWN, borderWidth: 1 }} }},
    {{ name: "MA5", type: "line", data: D.ma5, symbol: "none", lineStyle: {{ width: 1.2, color: "#e67e22" }} }},
    {{ name: "MA10", type: "line", data: D.ma10, symbol: "none", lineStyle: {{ width: 1.2, color: "#a29bfe" }} }},
    {{ name: "MA20", type: "line", data: D.ma20, symbol: "none", lineStyle: {{ width: 1.5, color: "#1abc9c" }} }},
    {{ name: "BB上轨", type: "line", data: D.bbUpper, symbol: "none", lineStyle: {{ width: 1, color: "#f39c12", type: "dashed" }} }},
    {{ name: "BB下轨", type: "line", data: D.bbLower, symbol: "none", lineStyle: {{ width: 1, color: "#f39c12", type: "dashed" }} }},
    {{ name: "BB中轨", type: "line", data: D.bbMid, symbol: "none", lineStyle: {{ width: 0.8, color: "#f39c12" }} }},
    {{ name: "金叉", type: "scatter", data: D.gcMarkers, symbol: "triangle", symbolSize: 14, itemStyle: {{ color: "#e74c3c" }}, z: 10, label: {{ show: true, position: "bottom", color: "#e74c3c", fontSize: 9, formatter: "金" }} }},
    {{ name: "死叉", type: "scatter", data: D.dcMarkers, symbol: "triangle", symbolRotate: 180, symbolSize: 14, itemStyle: {{ color: "#2ecc71" }}, z: 10, label: {{ show: true, position: "top", color: "#2ecc71", fontSize: 9, formatter: "死" }} }},
    {{ name: "阻力", type: "line", data: [], markLine: {{ silent: true, symbol: "none", lineStyle: {{ color: "#e74c3c", type: "dashed", width: 1 }}, label: {{ color: "#e74c3c", fontSize: 10 }}, data: [ {{ yAxis: D.r20Hi, name: "阻 " + D.r20Hi }}, {{ yAxis: D.allHi, name: "高 " + D.allHi }} ] }} }},
    {{ name: "支撑", type: "line", data: [], markLine: {{ silent: true, symbol: "none", lineStyle: {{ color: "#2ecc71", type: "dashed", width: 1 }}, label: {{ color: "#2ecc71", fontSize: 10 }}, data: [ {{ yAxis: D.r20Lo, name: "支 " + D.r20Lo }}, {{ yAxis: D.allLo, name: "低 " + D.allLo }} ] }} }}
  ]
}});

// ── Volume Chart ──
var vch = echarts.init(document.getElementById("vol-chart"));
vch.setOption({{
  backgroundColor: "#161b22",
  animation: true,
  tooltip: {{ trigger: "axis", backgroundColor: "rgba(13,17,23,0.96)", borderColor: "#21262d", textStyle: {{ color: "#c9d1d9", fontSize: 12 }}, formatter: function(ps) {{ var i = ps[0].dataIndex; return D.dates[i] + "<br>成交量 <b>" + D.vols[i].toFixed(2) + "</b> 万手"; }} }},
  grid: {{ left: "7%", right: "3%", top: 6, bottom: 22 }},
  xAxis: {{ type: "category", data: D.dates, axisLabel: {{ show: false }}, axisLine: {{ lineStyle: {{ color: "#21262d" }} }}, axisTick: {{ show: false }}, splitLine: {{ show: false }} }},
  yAxis: {{ type: "value", name: "万手", nameTextStyle: {{ color: "#484f58", fontSize: 11 }}, splitLine: {{ lineStyle: {{ color: "#21262d", type: "dashed" }} }}, axisLabel: {{ color: "#484f58", fontSize: 10 }}, axisLine: {{ show: false }} }},
  dataZoom: [ {{ type: "inside", start: ZS, end: ZE, xAxisIndex: 0 }}, {{ type: "slider", start: ZS, end: ZE, height: 18, bottom: 2 }} ],
  series: [ {{ type: "bar", data: D.vols.map(function(v, i) {{ return {{ value: v, itemStyle: {{ color: D.pcts[i] >= 0 ? "rgba(231,76,60,0.65)" : "rgba(46,204,113,0.65)" }} }}; }}), barWidth: "60%" }} ]
}});

// ── MACD Chart ──
var mch = echarts.init(document.getElementById("macd-chart"));
mch.setOption({{
  backgroundColor: "#161b22",
  animation: true,
  tooltip: {{ trigger: "axis", backgroundColor: "rgba(13,17,23,0.96)", borderColor: "#21262d", textStyle: {{ color: "#c9d1d9", fontSize: 12 }}, formatter: function(ps) {{ var i = ps[0].dataIndex; if (D.dif[i] == null) return ""; return D.dates[i] + "<br>DIF <b style='color:#e67e22'>" + D.dif[i].toFixed(2) + "</b> DEA <b style='color:#3498db'>" + D.dea[i].toFixed(2) + "</b><br>MACD <b style='color:" + (D.macdHist[i] >= 0 ? "#e74c3c" : "#2ecc71") + "'>" + D.macdHist[i].toFixed(2) + "</b>"; }} }},
  legend: {{ data: ["MACD柱", "DIF", "DEA"], top: 4, left: 50, textStyle: {{ color: "#6e7681", fontSize: 11 }}, itemWidth: 18, itemHeight: 10 }},
  grid: {{ left: "7%", right: "3%", top: 36, bottom: 24 }},
  xAxis: {{ type: "category", data: D.dates, axisLine: {{ lineStyle: {{ color: "#21262d" }} }}, axisLabel: {{ color: "#484f58", fontSize: 9, formatter: function(v) {{ return v.substring(5); }}, rotate: 45 }}, axisTick: {{ show: false }}, splitLine: {{ show: false }} }},
  yAxis: {{ type: "value", name: "MACD", nameTextStyle: {{ color: "#484f58", fontSize: 11 }}, splitLine: {{ lineStyle: {{ color: "#21262d", type: "dashed" }} }}, axisLabel: {{ color: "#484f58", fontSize: 10 }}, axisLine: {{ show: false }} }},
  dataZoom: [ {{ type: "inside", start: ZS, end: ZE, xAxisIndex: 0 }}, {{ type: "slider", start: ZS, end: ZE, height: 18, bottom: 2 }} ],
  series: [
    {{ name: "MACD柱", type: "bar", data: D.macdHist.map(function(v) {{ if (v == null) return 0; return {{ value: v, itemStyle: {{ color: v >= 0 ? "rgba(231,76,60,0.6)" : "rgba(46,204,113,0.6)" }} }}; }}), barWidth: "60%" }},
    {{ name: "DIF", type: "line", data: D.dif, symbol: "none", lineStyle: {{ width: 1.2, color: "#e67e22" }} }},
    {{ name: "DEA", type: "line", data: D.dea, symbol: "none", lineStyle: {{ width: 1.2, color: "#3498db" }} }}
  ]
}});

// Sync zoom
kch.group = "sync";
vch.group = "sync";
mch.group = "sync";
echarts.connect("sync");

// Responsive
window.addEventListener("resize", function() {{ kch.resize(); vch.resize(); mch.resize(); }});
</script>
</body>
</html>"""

# ── Step 7: Save ──
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tencent_chart.html')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'[OK] Generated: {output_path}')
print(f'   Data: {n} trading days, {dates[0]} ~ {dates[-1]}')
print(f'   Close: HK${start_price:.2f} -> HK${end_price:.2f} ({sign}{total_change:.2f}, {sign}{total_pct:.2f}%)')
print(f'   Range: HK${min_low:.2f} ~ HK${max_high:.2f}')
print(f'   MA5/MA10/MA20: {latest_ma5:.2f}/{latest_ma10:.2f}/{latest_ma20:.2f}')
print(f'   MACD: DIF={latest_dif:.2f} DEA={latest_dea:.2f} Hist={latest_macd_hist:.2f}')
print(f'   RSI(14)={latest_rsi:.0f} GC={len(gc_markers)} DC={len(dc_markers)}')
