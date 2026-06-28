# BA-quant 任务索引

> 所有任务均在各自独立子目录下工作，根目录只保留项目级通用文件。
> 新建任务时复制 `task_template/` 目录结构。

---

## 已有任务

| 任务ID | 目录 | 标的 | 状态 | 说明 |
|---------|------|------|------|------|
| task1 | `task1-SZ300308/` | 中际旭创 300308.SZ | 进行中 | 数据采集、K线图表、GitHub Pages 部署 |

---

## 新任务创建规范

1. 目录命名：`task{N}-<简称>`，如 `task2-SH600519`
2. 在 `TASKS.md` 中登记新任务
3. 复制 `task_template/` 作为起点（如尚未创建模板，则手动建立标准结构）
4. 所有脚本、数据、图表、输出文件均放在任务目录下
5. 根目录只放 `TASKS.md`、`.gitignore`、项目级 README

---

## 任务目录标准结构（参考）

```
task{N}-XXXXXX/
├── data/                # 原始数据文件
├── scripts/             # 数据处理/分析脚本
├── outputs/             # 生成的图表、报告
├── *.html               # 可视化网页（如有）
└── README.md            # 本任务说明
```

---

## 任务模板

首次创建新任务前，先执行一次：
```bash
mkdir -p task_template/data task_template/scripts task_template/outputs
echo "# 任务模板" > task_template/README.md
```

---

*最后更新: 2026-06-28*
