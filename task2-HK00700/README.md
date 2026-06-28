# Task2: 腾讯控股 (00700.HK) 深度技术分析

## 标的
- 名称：腾讯控股有限公司
- 代码：00700.HK
- 市场：香港联交所主板

## 数据来源
- Tushare Pro API (hk_daily)
- 数据范围：2025-06-30 ~ 2026-06-26 (244个交易日)

## 输出文件
- `tencent_chart.html` — 完整交互式分析网页（K线+成交量+MACD+RSI+布林带）

## 技术指标
- MA5/MA10/MA20 移动均线
- MACD (DIF/DEA/柱)
- 布林带 (20日, 2σ)
- RSI(14)
- 金叉/死叉标记
- 量价分析

## 目录结构
```
task2-HK00700/
├── data/                    # 原始数据
│   └── tencent_raw.json     # Tushare API原始返回
├── scripts/                 # 处理脚本
│   └── build_chart.py       # 数据计算+HTML生成
├── outputs/                 # 输出文件
├── tencent_chart.html       # 最终分析网页
└── README.md                # 本文件
```
