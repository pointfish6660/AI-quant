# BA-quant 任务索引

> 所有任务均在各自独立子目录下工作，根目录只保留项目级通用文件。
> 新建任务时复制 `task_template/` 目录结构。

---

## 已有任务

| 任务ID | 目录 | 标的 | 状态 | 说明 |
|---------|------|------|------|------|
| task1 | `task1-SZ300308/` | 中际旭创 300308.SZ | 进行中 | 数据采集、K线图表、GitHub Pages 部署 |
| task2 | `task2-HK00700/` | 腾讯控股 00700.HK | 进行中 | 港股数据采集、深度分析图表、GitHub Pages 部署 |
| task3 | `task3-Zhipu/` | 智谱 02513.HK | 进行中 | 港股新股数据采集（腾讯自选股）、深度分析图表、GitHub Pages 部署 |
| task4 | `task4-SMIC/` | 中芯国际 688981.SH + 00981.HK | 计划中 | A+H 双重上市，半导体龙头，spec 已就绪：`specs/smic.yaml` |
| task5 | `task5-BYD/` | 比亚迪 002594.SZ + 01211.HK | 计划中 | A+H 双重上市，新能源车+电池，spec 已就绪：`specs/byd.yaml` |
| task6 | `task6-CYPC/` | 长江电力 600900.SH | 计划中 | 纯 A股，水电蓝筹，分红标的，spec 已就绪：`specs/cypc.yaml` |

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

## 取数 Spec 规范（task4+ 新增）

task4 及以后的新取数任务，**必须先在 `specs/` 目录下准备 spec 文件**，作为该任务的取数契约：

- `specs/SPEC_FORMAT.md` — Spec 文件格式说明
- `specs/template.yaml` — 通用模板
- `specs/smic.yaml` / `specs/byd.yaml` / `specs/cypc.yaml` — 三只标的实例

Spec 固化了标的元信息、数据源、字段映射、输出格式、质量校验规则，写脚本前先固化取数规则。

---

*最后更新: 2026-07-01*
