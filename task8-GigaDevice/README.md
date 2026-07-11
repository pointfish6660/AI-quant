# task8-兆易创新 双均线策略回测

## 标的
- 兆易创新 (603986.SH) — 科创板半导体龙头
- 数据范围: 2025-07-01 ~ 2026-07-10 (250 交易日)
- 数据源: 腾讯行情 (qfq 前复权)

## 策略
- MA5/MA15 双均线交叉
- 金叉买入(当日open价)、死叉卖出(当日open价)
- 信号: signal=1/-1(状态) → position=signal.diff()(±2交叉) → exec_signal=signal.shift(1)(避免未来函数)

## 交易成本
- 佣金万2.5双边 + 印花税卖出千1 + 滑点单边千2
- 买入总成本率: 0.225%
- 卖出总成本率: 0.325%

## 回测结果
| 指标 | 策略 | 基准(买入持有) |
|------|------|--------------|
| 累计回报 | +205.42% | +396.72% |
| 年化收益 | +208.16% | +403.13% |
| 最大回撤 | -35.88% | -28.19% |
| 夏普比率 | 2.121 | 2.627 |
| 胜率 | 60.0% | — |
| 盈亏比 | 4.20 | — |
| 交易次数 | 10轮 | — |
| 总交易成本 | ¥9,053 | — |
| 期末权益 | ¥305,424 | ¥496,724 |
| 超额收益 | -¥191,301 | — |

## 分析
兆易创新这一年涨了近4倍，是极端牛市行情。双均线策略在单边上涨中表现不佳：
1. 死叉卖出后踏空，下一个金叉买回时价格已大幅上涨
2. 频繁切换(1.7信号/月)产生的交易成本侵蚀收益
3. 最大回撤反而比买入持有更大，因为策略在回调卖出后可能在更高位置买回

**结论**: 双均线策略适合震荡市和温和趋势市，在极端单边牛市中不如买入持有。

## 文件结构
```
task8-GigaDevice/
├── data/
│   ├── gdpy_daily.csv      # 日线数据
│   └── gdpy_daily.json     # JSON格式
├── scripts/
│   ├── fetch_gdpy.py       # 取数脚本
│   ├── build_dashboard.py  # 回测+看板生成(合并脚本)
│   └── dashboard_template.html  # 看板模板
├── outputs/
│   └── gdpy_backtest_dashboard.html  # 回测看板
└── README.md
```

## Skill
- dual-ma-backtest Skill 位于 `.workbuddy/skills/dual-ma-backtest/`
- 含 SKILL.md + references/strategy.py + references/backtest.py + references/chart_template.html
