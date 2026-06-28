import json

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 中际旭创 (300308.SZ) 数据分析 Notebook\n",
                "\n",
                "本 Notebook 用于探索和分析中际旭创的股价数据。\n",
                "- 数据来源: Tushare Pro / 本地 CSV\n",
                "- 数据文件: `zhongji_xuchuang_data.csv`\n",
                "- 最后更新: 2026-06-28"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import numpy as np\n",
                "import matplotlib.pyplot as plt\n",
                "import matplotlib\n",
                "matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']\n",
                "matplotlib.rcParams['axes.unicode_minus'] = False\n",
                "import warnings\n",
                "warnings.filterwarnings('ignore')\n",
                "\n",
                "print('Libraries loaded.')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. 加载数据\n",
                "\n",
                "从本地 CSV 文件加载中际旭创历史数据。"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 加载数据\n",
                "df = pd.read_csv('zhongji_xuchuang_data.csv')\n",
                "\n",
                "# 转换日期格式\n",
                "df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')\n",
                "df = df.sort_values('trade_date').reset_index(drop=True)\n",
                "\n",
                "print(f'数据条数: {len(df)}')\n",
                "print(f'日期范围: {df[\"trade_date\"].min().date()} ~ {df[\"trade_date\"].max().date()}')\n",
                "df.head()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. 基本统计\n",
                "\n",
                "查看价格区间、涨跌幅分布等基本统计信息。"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "print('=== 价格统计 ===')\n",
                "print(f'最高价: {df[\"high\"].max():.2f}')\n",
                "print(f'最低价: {df[\"low\"].min():.2f}')\n",
                "print(f'最新收盘: {df[\"close\"].iloc[-1]:.2f}')\n",
                "start_price = df['close'].iloc[0]\n",
                "end_price = df['close'].iloc[-1]\n",
                "chg = end_price - start_price\n",
                "chg_pct = (end_price / start_price - 1) * 100\n",
                "print(f'期间涨跌: {chg:+.2f} ({chg_pct:+.2f}%)')\n",
                "print()\n",
                "print('=== 涨跌幅分布 ===')\n",
                "print(df['pct_chg'].describe())\n",
                "print()\n",
                "print('=== 成交量统计 (万手) ===')\n",
                "df['vol_wan'] = df['vol'] / 10000\n",
                "print(df['vol_wan'].describe())"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. 计算均线指标\n",
                "\n",
                "计算 MA5、MA10、MA20 移动平均线，以及多头排列信号。"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 计算均线\n",
                "df['MA5']   = df['close'].rolling(5).mean()\n",
                "df['MA10']  = df['close'].rolling(10).mean()\n",
                "df['MA20']  = df['close'].rolling(20).mean()\n",
                "\n",
                "# 多头排列信号: MA5 > MA10 > MA20\n",
                "df['bull_signal'] = (df['MA5'] > df['MA10']) & (df['MA10'] > df['MA20'])\n",
                "\n",
                "print('最近 10 个交易日均线状态:')\n",
                "cols = ['trade_date', 'close', 'MA5', 'MA10', 'MA20', 'bull_signal']\n",
                "display(df[cols].tail(10))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. 绘制收盘价 + 均线图"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "plt.figure(figsize=(14, 6))\n",
                "plt.plot(df['trade_date'], df['close'], label='收盘价', linewidth=1.5, color='#3498db')\n",
                "plt.plot(df['trade_date'], df['MA5'],   label='MA5',  linewidth=1,   color='#e67e22', alpha=0.8)\n",
                "plt.plot(df['trade_date'], df['MA10'],  label='MA10', linewidth=1,   color='#9b59b6', alpha=0.8)\n",
                "plt.plot(df['trade_date'], df['MA20'],  label='MA20', linewidth=1.2, color='#1abc9c', alpha=0.8)\n",
                "plt.fill_between(df['trade_date'], df['close'], alpha=0.05, color='#3498db')\n",
                "plt.title('中际旭创 (300308.SZ) 收盘价走势', fontsize=14, fontweight='bold')\n",
                "plt.xlabel('日期')\n",
                "plt.ylabel('收盘价 (¥)')\n",
                "plt.legend()\n",
                "plt.grid(alpha=0.3)\n",
                "plt.xticks(rotation=45)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5. 成交量分析"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)\n",
                "\n",
                "# 收盘价\n",
                "ax1.plot(df['trade_date'], df['close'], color='#3498db', linewidth=1.5)\n",
                "ax1.set_ylabel('收盘价 (¥)')\n",
                "ax1.set_title('中际旭创 价格 + 成交量')\n",
                "ax1.grid(alpha=0.3)\n",
                "\n",
                "# 成交量 (红涨绿跌，中国习惯)\n",
                "colors = ['#e74c3c' if c >= 0 else '#2ecc71' for c in df['pct_chg']]\n",
                "ax2.bar(df['trade_date'], df['vol_wan'], color=colors, alpha=0.7, width=0.8)\n",
                "ax2.set_ylabel('成交量 (万手)')\n",
                "ax2.set_xlabel('日期')\n",
                "ax2.grid(alpha=0.3)\n",
                "\n",
                "plt.xticks(rotation=45)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 6. 从 Tushare 获取最新数据 (可选)\n",
                "\n",
                "如需更新数据，取消注释下方代码并运行。\n",
                "需要配置 Tushare token。"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 从 Tushare 获取最新数据 (需要 token)\n",
                "# import tushare as ts\n",
                "# ts.set_token('YOUR_TUSHARE_TOKEN')\n",
                "# pro = ts.pro_api()\n",
                "# \n",
                "# new_data = pro.daily(\n",
                "#     ts_code='300308.SZ',\n",
                "#     start_date='20250601',\n",
                "#     end_date='20260628'\n",
                "# )\n",
                "# print(f'获取到 {len(new_data)} 条新数据')\n",
                "# new_data.head()"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.13.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open("explore.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print(f"Notebook created: explore.ipynb ({len(notebook['cells'])} cells)")
