# 淘宝用户行为分析（MySQL + PySpark + sklearn）

> 草稿，随项目推进补充。

## 数据
- 来源：阿里天池 User Behavior Data from Taobao for Recommendation
- 规模：100,150,807 行，2017-11-25 ~ 2017-12-03（9 天），字段：用户ID、商品ID、类目ID、行为类型、时间戳
- 行为：pv 浏览 / fav 收藏 / cart 加购 / buy 购买；原始数据含约 0.06% 时间戳异常记录，清洗时剔除
- 原始文件不入库（见 .gitignore）

## 结构
- `sql/`：MySQL 建表、导入、清洗、分析脚本（编号执行）
- `spark/`：PySpark 全量特征工程
- `notebooks/`：清洗、分析、建模、可视化
- `scripts/`：抽样等辅助脚本
- `figures/`：输出图表

## 进度
- [x] 数据检查
- [x] MySQL 导入与清洗（`sql/00`–`03`）
- [x] SQL 业务分析（`sql/04`–`09`：指标、趋势、漏斗、类目、加购流失、复购）
- [x] 可视化（`scripts/make_figures.py` → `figures/`）
- [ ] PySpark 特征工程
- [ ] sklearn 建模（用户分群 + 购买预测）
- [ ] 业务结论与建议

## 初步结果（5% 用户样本，约 4.9 万用户、497 万条记录）
> 样本按用户抽取（每 20 个用户取 1 个），保证每个用户的行为轨迹完整。样本中 68% 的用户有购买，明显高于真实平台水平，说明数据集本身偏活跃/偏购买用户，结论不能直接外推到平台整体。

![每日趋势](figures/01_daily_trend.png)
12 月 2–3 日的访问用户数比此前日均高约 35%。

![分时段](figures/02_hourly.png)
浏览高峰在晚间，转化率（购买次数/浏览次数）在上午 10 点最高。

![漏斗](figures/03_funnel_pairs.png)
未经收藏/加购直接购买的用户-商品对多于收藏/加购后再购买的。漏斗按“是否发生过该行为”统计，不要求时间顺序。

![类目转化率](figures/04_category_conversion.png)
![复购](figures/05_repurchase.png)

## 工程笔记
- 原始数据 100,150,807 行，其中约 0.06% 时间戳异常，清洗时剔除。
- MySQL 默认 InnoDB 缓冲池仅 128MB，500 万行表上的聚合查询耗时 4–28 分钟；调至 8GB 后同类查询降至秒级。
- 同一批 SQL 在 DuckDB 上交叉验证，结果完全一致。
- 全量 1 亿行不适合直接放进 MySQL 分析，全量特征工程交给 PySpark。

## 复现
1. 从阿里天池下载 `UserBehavior.csv`，放到项目根目录（不入库）。
2. `python scripts/make_sample.py UserBehavior.csv data/sample_5pct.csv 20`
3. 在 MySQL 中依次执行 `sql/00`–`03`，再执行 `sql/04`–`09`。
4. `pip install -r requirements.txt` 后运行 `python scripts/make_figures.py`。
