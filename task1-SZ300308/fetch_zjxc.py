import tushare as ts
import json
from datetime import datetime, timedelta

# 初始化 Tushare
ts.set_token('8bae0978de7b176f1d480ae3273ba4dc18606a692c27fb0802b132f1')
pro = ts.pro_api()

# 计算日期范围（近一年）
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

print(f"获取中际旭创(300308.SZ)数据: {start_date} ~ {end_date}")

# 获取日线数据
df = pro.daily(ts_code='300308.SZ', start_date=start_date, end_date=end_date)

# 按日期升序排列（方便图表展示）
df = df.sort_values('trade_date')

# 转换为字典列表
records = df.to_dict('records')

print(f"获取到 {len(records)} 条交易记录")

# 保存为 JSON
with open('zhongji_xuchuang_data.json', 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("数据已保存到 zhongji_xuchuang_data.json")

# 同时保存为 CSV 方便查看
df.to_csv('zhongji_xuchuang_data.csv', index=False, encoding='utf-8-sig')
print("数据已保存到 zhongji_xuchuang_data.csv")
