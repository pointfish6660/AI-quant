#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双均线策略回测看板生成器（合并脚本）

流程：读取CSV → 生成信号 → 信号统计 → 回测(含交易成本) → 计算指标 → 注入模板 → 输出HTML

信号生成三个关键细节：
1. signal = np.where(ma_short > ma_long, 1, -1)  — 状态标记(非指令)
2. position = signal.diff()  — diff=2金叉, diff=-2死叉(穿越瞬间)
3. exec_signal = signal.shift(1)  — 避免未来函数(前一日信号当日open执行)

Usage: python scripts/build_dashboard.py
Output: outputs/gdpy_backtest_dashboard.html
"""
import sys
import io
import os
import json

# ── UTF-8 修复 (Windows Git Bash 兼容) ──
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np

# ══════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(ROOT, "data", "gdpy_daily.csv")
TEMPLATE_PATH = os.path.join(HERE, "dashboard_template.html")
OUTPUT_PATH = os.path.join(ROOT, "outputs", "gdpy_backtest_dashboard.html")

STOCK_NAME = "兆易创新"
STOCK_CODE = "603986.SH"
SHORT_PERIOD = 5
LONG_PERIOD = 15
INITIAL_CAPITAL = 100000.0

# 交易成本参数
COMMISSION_RATE = 0.00025   # 佣金万2.5（双边）
STAMP_TAX_RATE = 0.001      # 印花税千1（仅卖出）
SLIPPAGE_RATE = 0.002       # 滑点千2（单边）

# 无风险利率（年化）
RF_ANNUAL = 0.03

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


# ══════════════════════════════════════════════════════════════
# Phase 1: 生成信号 (strategy.generate_signals 逻辑)
# ══════════════════════════════════════════════════════════════
def generate_signals(df, short_period, long_period):
    """生成双均线信号 — 三个关键细节。"""
    df = df.copy()

    # 计算均线
    df['ma_short'] = df['close'].rolling(short_period).mean()
    df['ma_long'] = df['close'].rolling(long_period).mean()

    # ── 细节1: signal 是每日状态标记 (1=多头, -1=空头) ──
    df['signal'] = np.where(df['ma_short'] > df['ma_long'], 1, -1)

    # ── 细节2: position = signal.diff() 捕捉穿越瞬间 ──
    # diff=2: 金叉(-1→+1), diff=-2: 死叉(+1→-1)
    df['position'] = df['signal'].diff()

    # ── 细节3: exec_signal = signal.shift(1) 避免未来函数 ──
    # 前一日信号，当日 open 执行
    df['exec_signal'] = df['signal'].shift(1)

    return df


# ══════════════════════════════════════════════════════════════
# Phase 2: 信号统计 + 趋势检测
# ══════════════════════════════════════════════════════════════
def compute_signal_stats(df):
    """计算信号频率统计。"""
    golden_crosses = int((df['position'] == 2).sum())
    death_crosses = int((df['position'] == -2).sum())
    n_days = len(df)
    n_months = n_days / 21.0

    hold_days_list = []
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        pos = df['position'].iloc[i]
        if pos == 2 and not in_position:
            in_position = True
            entry_idx = i
        elif pos == -2 and in_position:
            in_position = False
            hold_days_list.append(i - entry_idx)

    avg_hold_days = sum(hold_days_list) / len(hold_days_list) if hold_days_list else 0

    return {
        'golden_crosses': golden_crosses,
        'death_crosses': death_crosses,
        'total_signals': golden_crosses + death_crosses,
        'signals_per_month': round((golden_crosses + death_crosses) / n_months, 1) if n_months > 0 else 0,
        'avg_hold_days': round(avg_hold_days, 1),
        'complete_trades': len(hold_days_list),
    }


def detect_regime(df, lookback=20):
    """检测趋势期/震荡期。20日内交叉>=3次为震荡期。"""
    regime = []
    for i in range(len(df)):
        start = max(0, i - lookback)
        window = df['position'].iloc[start:i+1]
        cross_count = int(((window == 2) | (window == -2)).sum())
        regime.append('choppy' if cross_count >= 3 else 'trend')
    return regime


# ══════════════════════════════════════════════════════════════
# Phase 3: 回测引擎 (backtest.run_backtest 逻辑) — 含交易成本
# ══════════════════════════════════════════════════════════════
def run_backtest(df, initial_capital):
    """运行回测，open价成交，含交易成本。"""
    df = df.copy().reset_index(drop=True)
    n = len(df)

    cash = initial_capital
    shares = 0.0
    holding = False
    trades = []
    equity_curve = []

    for i in range(n):
        open_p = df['open'].iloc[i]
        close_p = df['close'].iloc[i]

        exec_sig = df['exec_signal'].iloc[i]
        if pd.isna(exec_sig):
            exec_sig = 0

        should_hold = (exec_sig == 1)

        # 买入
        if should_hold and not holding:
            cost_rate = COMMISSION_RATE + SLIPPAGE_RATE  # 0.225%
            buy_cost = cash * cost_rate
            investable = cash - buy_cost
            shares = investable / open_p
            cash = 0.0
            holding = True
            trades.append({
                'idx': i,
                'date': str(df['trade_date'].iloc[i]),
                'type': 'buy',
                'price': round(open_p, 2),
                'shares': round(shares, 2),
                'cost': round(buy_cost, 2),
                'reason': 'golden_cross'
            })
        # 卖出
        elif not should_hold and holding:
            gross = shares * open_p
            cost_rate = COMMISSION_RATE + STAMP_TAX_RATE + SLIPPAGE_RATE  # 0.325%
            sell_cost = gross * cost_rate
            cash = gross - sell_cost
            trades.append({
                'idx': i,
                'date': str(df['trade_date'].iloc[i]),
                'type': 'sell',
                'price': round(open_p, 2),
                'shares': round(shares, 2),
                'cost': round(sell_cost, 2),
                'reason': 'death_cross'
            })
            shares = 0.0
            holding = False

        # mark-to-market
        equity = cash + shares * close_p
        equity_curve.append(equity)

    df['equity'] = equity_curve
    df['strategy_return'] = df['equity'].pct_change().fillna(0)

    # 基准: 买入持有（同样扣除买入成本）
    bench_buy_cost = initial_capital * (COMMISSION_RATE + SLIPPAGE_RATE)
    bench_investable = initial_capital - bench_buy_cost
    bench_shares = bench_investable / df['close'].iloc[0]
    df['benchmark_equity'] = bench_shares * df['close']
    df['benchmark_return'] = df['benchmark_equity'].pct_change().fillna(0)

    # 超额收益
    df['alpha'] = df['equity'] - df['benchmark_equity']

    # 回撤
    df['strategy_peak'] = df['equity'].cummax()
    df['strategy_drawdown'] = (df['equity'] - df['strategy_peak']) / df['strategy_peak']
    df['benchmark_peak'] = df['benchmark_equity'].cummax()
    df['benchmark_drawdown'] = (df['benchmark_equity'] - df['benchmark_peak']) / df['benchmark_peak']

    return df, trades


# ══════════════════════════════════════════════════════════════
# Phase 4: 计算指标 (backtest.compute_metrics 逻辑)
# ══════════════════════════════════════════════════════════════
def compute_metrics(df, trades, initial_capital, rf_annual):
    """计算回测绩效指标。"""
    n_days = len(df)

    final_equity = df['equity'].iloc[-1]
    cum_return = (final_equity / initial_capital - 1) * 100

    final_bench = df['benchmark_equity'].iloc[-1]
    bench_cum_return = (final_bench / initial_capital - 1) * 100

    ann_return = ((final_equity / initial_capital) ** (252.0 / n_days) - 1) * 100
    bench_ann_return = ((final_bench / initial_capital) ** (252.0 / n_days) - 1) * 100

    max_dd = df['strategy_drawdown'].min() * 100
    bench_max_dd = df['benchmark_drawdown'].min() * 100

    rf_daily = rf_annual / 252.0
    excess = df['strategy_return'] - rf_daily
    sharpe = (excess.mean() / excess.std() * (252 ** 0.5)) if excess.std() > 0 else 0.0

    bench_excess = df['benchmark_return'] - rf_daily
    bench_sharpe = (bench_excess.mean() / bench_excess.std() * (252 ** 0.5)) if bench_excess.std() > 0 else 0.0

    # 胜率 & 盈亏比
    win_count = 0
    loss_count = 0
    profits = []
    losses = []
    i = 0
    while i < len(trades) - 1:
        if trades[i]['type'] == 'buy' and trades[i + 1]['type'] == 'sell':
            buy_price = trades[i]['price']
            sell_price = trades[i + 1]['price']
            pnl_pct = (sell_price - buy_price) / buy_price * 100
            if pnl_pct > 0:
                win_count += 1
                profits.append(pnl_pct)
            else:
                loss_count += 1
                losses.append(pnl_pct)
            i += 2
        else:
            i += 1

    total_trades = win_count + loss_count
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
    avg_profit = sum(profits) / len(profits) if profits else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    profit_loss_ratio = (avg_profit / avg_loss) if avg_loss > 0 else (float('inf') if avg_profit > 0 else 0.0)

    total_cost = sum(t.get('cost', 0) for t in trades)

    return {
        'cum_return': round(cum_return, 2),
        'bench_cum_return': round(bench_cum_return, 2),
        'ann_return': round(ann_return, 2),
        'bench_ann_return': round(bench_ann_return, 2),
        'max_drawdown': round(max_dd, 2),
        'bench_max_drawdown': round(bench_max_dd, 2),
        'sharpe': round(sharpe, 3),
        'bench_sharpe': round(bench_sharpe, 3),
        'win_rate': round(win_rate, 1),
        'profit_loss_ratio': round(profit_loss_ratio, 2),
        'total_trades': total_trades,
        'total_cost': round(total_cost, 2),
        'n_days': n_days,
        'final_equity': round(final_equity, 2),
        'bench_final_equity': round(final_bench, 2),
        'alpha_final': round(final_equity - final_bench, 2),
    }


# ══════════════════════════════════════════════════════════════
# Phase 5: 构建数据 JSON + 注入模板
# ══════════════════════════════════════════════════════════════
def build_data_json(df, trades, signal_stats, regime, metrics):
    """组装前端数据对象。"""
    # 日期格式化 YYYYMMDD -> YYYY-MM-DD
    dates = []
    for d in df['trade_date']:
        d = str(d)
        if len(d) == 8:
            dates.append(f"{d[:4]}-{d[4:6]}-{d[6:8]}")
        else:
            dates.append(d)

    # 买卖标记: [idx, price]
    buy_markers = [[t['idx'], t['price']] for t in trades if t['type'] == 'buy']
    sell_markers = [[t['idx'], t['price']] for t in trades if t['type'] == 'sell']

    # NaN -> None (JSON 兼容)
    def clean_list(s):
        return [None if pd.isna(v) else round(float(v), 2) for v in s]

    data_obj = {
        'stockName': STOCK_NAME,
        'stockCode': STOCK_CODE,
        'dateFrom': dates[0] if dates else '',
        'dateTo': dates[-1] if dates else '',
        'nDays': len(df),
        'shortPeriod': SHORT_PERIOD,
        'longPeriod': LONG_PERIOD,
        'initialCapital': INITIAL_CAPITAL,
        'dates': dates,
        'close': clean_list(df['close']),
        'ma5': clean_list(df['ma_short']),
        'ma15': clean_list(df['ma_long']),
        'buyMarkers': buy_markers,
        'sellMarkers': sell_markers,
        'strategyEquity': [round(float(v), 2) for v in df['equity']],
        'benchmarkEquity': [round(float(v), 2) for v in df['benchmark_equity']],
        'alpha': [round(float(v), 2) for v in df['alpha']],
        'strategyDrawdown': [round(float(v) * 100, 2) for v in df['strategy_drawdown']],
        'benchmarkDrawdown': [round(float(v) * 100, 2) for v in df['benchmark_drawdown']],
        'regime': regime,
        'signalStats': signal_stats,
        'metrics': metrics,
        'trades': [{k: v for k, v in t.items() if k != 'idx'} for t in trades],
        'costParams': {
            'commission': COMMISSION_RATE,
            'stampTax': STAMP_TAX_RATE,
            'slippage': SLIPPAGE_RATE
        }
    }

    return json.dumps(data_obj, ensure_ascii=False, default=str)


def main():
    print(f"=== 双均线策略回测看板生成器 ===")
    print(f"  股票: {STOCK_NAME} ({STOCK_CODE})")
    print(f"  策略: MA{SHORT_PERIOD}/MA{LONG_PERIOD} 双均线交叉")
    print(f"  数据: {CSV_PATH}")
    print()

    # ── 1. 加载数据 ──
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    df['trade_date'] = df['trade_date'].astype(str)
    df = df.sort_values('trade_date').reset_index(drop=True)
    print(f"[OK] 加载 {len(df)} 条数据 ({df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]})")

    # ── 2. 生成信号 ──
    df = generate_signals(df, SHORT_PERIOD, LONG_PERIOD)
    gc_count = int((df['position'] == 2).sum())
    dc_count = int((df['position'] == -2).sum())
    print(f"[OK] 信号生成: {gc_count} 金叉, {dc_count} 死叉")

    # ── 3. 信号统计 + 趋势检测 ──
    signal_stats = compute_signal_stats(df)
    regime = detect_regime(df)
    choppy_days = regime.count('choppy')
    print(f"[OK] 信号统计: {signal_stats['signals_per_month']} 信号/月, 平均持仓 {signal_stats['avg_hold_days']} 天")
    print(f"[OK] 趋势检测: {len(regime) - choppy_days} 趋势日, {choppy_days} 震荡日")

    # ── 4. 回测 ──
    df, trades = run_backtest(df, INITIAL_CAPITAL)
    print(f"[OK] 回测完成: {len(trades)} 笔交易")

    # ── 5. 计算指标 ──
    metrics = compute_metrics(df, trades, INITIAL_CAPITAL, RF_ANNUAL)
    print(f"\n{'='*50}")
    print(f"  回测绩效摘要")
    print(f"{'='*50}")
    print(f"  累计回报:   策略 {metrics['cum_return']:+.2f}%  vs  基准 {metrics['bench_cum_return']:+.2f}%")
    print(f"  年化收益:   策略 {metrics['ann_return']:+.2f}%  vs  基准 {metrics['bench_ann_return']:+.2f}%")
    print(f"  最大回撤:   策略 {metrics['max_drawdown']:.2f}%  vs  基准 {metrics['bench_max_drawdown']:.2f}%")
    print(f"  夏普比率:   策略 {metrics['sharpe']:.3f}  vs  基准 {metrics['bench_sharpe']:.3f}")
    print(f"  胜率:       {metrics['win_rate']:.1f}%  ({metrics['total_trades']} 轮)")
    print(f"  盈亏比:     {metrics['profit_loss_ratio']:.2f}")
    print(f"  总交易成本: ¥{metrics['total_cost']:.2f}")
    print(f"  期末权益:   策略 ¥{metrics['final_equity']:.2f}  vs  基准 ¥{metrics['bench_final_equity']:.2f}")
    print(f"  超额收益:   ¥{metrics['alpha_final']:+.2f}")
    print(f"{'='*50}")

    # ── 6. 构建数据 JSON ──
    data_json = build_data_json(df, trades, signal_stats, regime, metrics)
    print(f"[OK] 数据 JSON: {len(data_json)} 字符")

    # ── 7. 注入模板 ──
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    replacements = {
        '__DATA_JSON__': data_json,
        '__STOCK_NAME__': STOCK_NAME,
        '__STOCK_CODE__': STOCK_CODE,
        '__DATE_FROM__': f"{df['trade_date'].iloc[0][:4]}-{df['trade_date'].iloc[0][4:6]}-{df['trade_date'].iloc[0][6:8]}",
        '__DATE_TO__': f"{df['trade_date'].iloc[-1][:4]}-{df['trade_date'].iloc[-1][4:6]}-{df['trade_date'].iloc[-1][6:8]}",
        '__N_DAYS__': str(len(df)),
        '__SHORT_PERIOD__': str(SHORT_PERIOD),
        '__LONG_PERIOD__': str(LONG_PERIOD),
        '__INITIAL_CAPITAL__': str(int(INITIAL_CAPITAL)),
    }

    for k, v in replacements.items():
        template = template.replace(k, v)

    # ── 8. 检查未替换的占位符 ──
    import re
    remaining = re.findall(r'__[A-Z_]+__', template)
    if remaining:
        print(f"[WARN] 未替换的占位符: {set(remaining)}")
    else:
        print(f"[OK] 所有占位符已替换")

    # ── 9. 写出 ──
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(template)
    print(f"\n[DONE] 看板已生成: {OUTPUT_PATH}")
    print(f"  文件大小: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
