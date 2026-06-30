"""Update tencent_raw.json with latest data from westock (Tencent stock app)."""
import json, os

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
json_path = os.path.join(data_dir, 'tencent_raw.json')

# Load existing data
with open(json_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# Find the latest date in existing data
existing_dates = set(r['trade_date'] for r in raw_data)
print(f"Existing data: {len(raw_data)} records, latest: {max(existing_dates)}")

# Latest data from westock (2026-06-29, complete; 2026-06-30 is intraday, skip)
# Westock fields: date, open, last(close), high, low, volume, amount, exchange
new_records_westock = [
    # 2026-06-29 (Monday, complete)
    {"date": "2026-06-29", "open": 417.0, "last": 420.20, "high": 432.0, "low": 415.0, "volume": 33066070, "amount": 13955589615.35},
]

# Get the last close from existing data as pre_close
raw_data.sort(key=lambda x: x['trade_date'])
last_existing = raw_data[-1]
pre_close = last_existing['close']
print(f"Last existing close: {pre_close} ({last_existing['trade_date']})")

# Convert westock format to tushare format and merge
added = 0
for w in new_records_westock:
    # Convert date YYYY-MM-DD to YYYYMMDD
    trade_date = w['date'].replace('-', '')
    
    if trade_date in existing_dates:
        print(f"  Skip {trade_date} (already exists)")
        continue
    
    close = float(w['last'])
    change = round(close - pre_close, 2)
    pct_chg = round((change / pre_close) * 100, 2)
    
    record = {
        "ts_code": "00700.HK",
        "trade_date": trade_date,
        "open": float(w['open']),
        "high": float(w['high']),
        "low": float(w['low']),
        "close": close,
        "pre_close": float(pre_close),
        "change": change,
        "pct_chg": pct_chg,
        "vol": float(w['volume']),
        "amount": float(w['amount'])
    }
    raw_data.append(record)
    print(f"  Added {trade_date}: close={close}, change={change}, pct={pct_chg}%")
    pre_close = close  # Update for next record
    added += 1

# Sort chronologically
raw_data.sort(key=lambda x: x['trade_date'])

# Save
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(raw_data, f, ensure_ascii=False, indent=2)

print(f"\nDone. Added {added} records. Total: {len(raw_data)} records.")
print(f"Date range: {raw_data[0]['trade_date']} ~ {raw_data[-1]['trade_date']}")
