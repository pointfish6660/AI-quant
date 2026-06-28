import json

# Data from Tushare API (passed as string to avoid escaping issues)
data_str = '''[REPLACE_ME]'''

# Parse and save
data = json.loads(data_str)
with open('zhongji_xuchuang_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Saved {len(data)} records")
