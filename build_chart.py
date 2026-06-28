"""Build interactive ECharts HTML for 中际旭创 daily close price chart."""
import csv, json

rows = []
with open('task1-SZ300308/zhongji_xuchuang_data.csv', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        d = r['trade_date']
        rows.append({
            'date': f'{d[:4]}-{d[4:6]}-{d[6:8]}',
            'close': float(r['close']),
            'open': float(r['open']),
            'high': float(r['high']),
            'low': float(r['low']),
            'vol': float(r['vol']),
            'amount': float(r['amount']),
            'pct_chg': float(r['pct_chg'])
        })

start_date = rows[0]['date']
end_date = rows[-1]['date']
start_price = rows[0]['close']
end_price = rows[-1]['close']
total_change = end_price - start_price
total_pct = (total_change / start_price) * 100
sign = '+' if total_change >= 0 else ''
up_class = 'up' if end_price >= start_price else 'down'
max_high = max(r['high'] for r in rows)
min_low = min(r['low'] for r in rows)
count = len(rows)

data = {
    '__DATES__': json.dumps([r['date'] for r in rows], ensure_ascii=False),
    '__CLOSES__': json.dumps([r['close'] for r in rows]),
    '__OPENS__': json.dumps([r['open'] for r in rows]),
    '__HIGHS__': json.dumps([r['high'] for r in rows]),
    '__LOWS__': json.dumps([r['low'] for r in rows]),
    '__VOLS__': json.dumps([round(r['vol']/10000, 2) for r in rows]),
    '__AMOUNTS__': json.dumps([round(r['amount']/10000, 2) for r in rows]),
    '__PCTCHGS__': json.dumps([round(r['pct_chg'], 2) for r in rows]),
    '__START_DATE__': start_date,
    '__END_DATE__': end_date,
    '__COUNT__': str(count),
    '__START_PRICE__': f'{start_price:.2f}',
    '__END_PRICE__': f'{end_price:.2f}',
    '__TOTAL_CHANGE__': f'{sign}{total_change:.2f}',
    '__TOTAL_PCT__': f'{sign}{total_pct:.2f}%',
    '__UP_CLASS__': up_class,
    '__MAX_HIGH__': f'{max_high:.2f}',
    '__MIN_LOW__': f'{min_low:.2f}',
}

with open('task1-SZ300308/chart_template.html', 'r', encoding='utf-8') as f:
    html = f.read()

for key, val in data.items():
    html = html.replace(key, val)

output_path = 'task1-SZ300308/zhongji_xuchuang_chart.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'OK: {output_path}')
print(f'Data: {count} trading days, {start_date} ~ {end_date}')
print(f'Close: {start_price:.2f} -> {end_price:.2f} ({sign}{total_change:.2f}, {sign}{total_pct:.2f}%)')
