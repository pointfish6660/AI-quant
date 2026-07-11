#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BA-quant Python 环境验证脚本
用途: 检查量化交易/数据分析/机器学习所需的 Python 包是否正确安装
运行: python verify_env.py
"""
import importlib
import sys

# 分类的包清单 (模块名 -> pip包名)
PACKAGES = {
    "数据分析核心": {
        "pandas": "pandas",
        "numpy": "numpy",
        "scipy": "scipy",
        "statsmodels": "statsmodels",
    },
    "可视化": {
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "plotly": "plotly",
        "mplfinance": "mplfinance",
        "bokeh": "bokeh",
    },
    "金融数据获取": {
        "tushare": "tushare",
        "akshare": "akshare",
        "yfinance": "yfinance",
        "lxml": "lxml",
        "bs4": "beautifulsoup4",
    },
    "量化/技术指标": {
        "pandas_ta": "pandas-ta",
        "ta": "ta",
        "backtrader": "backtrader",
        "vectorbt": "vectorbt",
        "quantstats": "quantstats",
    },
    "机器学习": {
        "sklearn": "scikit-learn",
        "xgboost": "xgboost",
        "lightgbm": "lightgbm",
    },
    "Jupyter": {
        "jupyterlab": "jupyterlab",
        "ipykernel": "ipykernel",
        "notebook": "notebook",
    },
    "工具": {
        "openpyxl": "openpyxl",
        "tqdm": "tqdm",
        "requests": "requests",
    },
}


def main():
    print(f"Python: {sys.version.split()[0]}  ({sys.executable})")
    print("=" * 60)

    ok, fail = [], []
    for category, mods in PACKAGES.items():
        print(f"\n[{category}]")
        for mod, pip_name in mods.items():
            try:
                m = importlib.import_module(mod)
                ver = getattr(m, "__version__", "?")
                print(f"  OK   {mod:<16} {ver:<12} (pip: {pip_name})")
                ok.append(mod)
            except Exception as e:
                print(f"  FAIL {mod:<16} {type(e).__name__}: {e}")
                fail.append((mod, pip_name, str(e)))

    print("\n" + "=" * 60)
    print(f"成功: {len(ok)}  失败: {len(fail)}")
    if fail:
        print("\n缺失包 (可用 pip install 补装):")
        for mod, pip_name, err in fail:
            print(f"  pip install {pip_name}")
    else:
        print("\n全部包可用! 环境就绪。")

    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
