"""PySpark 特征工程：从行为日志生成"用户级"特征表，并给出购买标签。

思路（按时间切分，避免数据泄露）：
  把 9 天按序号 0..8 编号（0 = 2017-11-25，8 = 2017-12-03，北京时间）。
  训练快照 train：用第 0-4 天（11/25-11/29）的行为做特征，预测第 5-6 天（11/30-12/01）是否购买
  测试快照 test ：用第 2-6 天（11/27-12/01）的行为做特征，预测第 7-8 天（12/02-12/03）是否购买
  两个快照的观察窗（5 天）和预测窗（2 天）长度相同，特征含义一致；测试标签都发生在训练标签之后。
  注意：12/02-12/03 流量明显高于此前，测试集存在一定分布偏移，评估时要说明。

用法（PowerShell，项目根目录）：
    pip install pyspark pandas pyarrow
    python spark/01_build_features.py --sample          # 先用 5% 样本快速验证
    python spark/01_build_features.py                   # 全量 1 亿行（需要几分钟到十几分钟）

输出：data/user_features.csv（不入库）。Spark 只做聚合；结果只有约百万行，
用 pandas 保存，避免 Windows 上 Spark 写文件需要 winutils 的问题。
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START_TS = 1511539200  # 2017-11-25 00:00:00 +08:00
DAY = 86400
N_DAYS = 9

# (名称, 观察窗起止[含起不含止], 预测窗起止)
SNAPSHOTS = [
    ("train", (0, 5), (5, 7)),
    ("test", (2, 7), (7, 9)),
]

FEATURES = [
    "pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt",
    "active_days", "items_cnt", "cats_cnt",
    "pv_last_day", "cart_last_day", "buy_last_day",
    "days_since_active", "days_since_buy",
    "cart_pending", "fav_pending",
    "buy_pv_ratio", "cart_pv_ratio", "fav_pv_ratio",
]


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="CSV 路径，默认项目根目录的 UserBehavior.csv")
    ap.add_argument("--sample", action="store_true", help="使用 data/sample_5pct.csv")
    ap.add_argument("--output", default=str(ROOT / "data" / "user_features.csv"))
    ap.add_argument("--java-home", default="D:/JDK21", help="JDK 17/21 目录；Spark 不支持 Java 26")
    ap.add_argument("--driver-memory", default="8g")
    return ap.parse_args()


def setup_java(java_home):
    if java_home and Path(java_home).exists():
        os.environ["JAVA_HOME"] = str(java_home)
        os.environ["PATH"] = str(Path(java_home) / "bin") + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)


def build_snapshot(df, name, obs, label):
    from pyspark.sql import functions as F

    obs_start, obs_end = obs
    label_start, label_end = label
    window_len = obs_end - obs_start
    last_day = obs_end - 1

    def cnt(cond):
        return F.sum(F.when(cond, 1).otherwise(0))

    b = F.col("behavior")
    d = F.col("day")
    o = df.filter((d >= obs_start) & (d < obs_end))

    base = o.groupBy("user_id").agg(
        cnt(b == "pv").alias("pv_cnt"),
        cnt(b == "fav").alias("fav_cnt"),
        cnt(b == "cart").alias("cart_cnt"),
        cnt(b == "buy").alias("buy_cnt"),
        F.countDistinct("day").alias("active_days"),
        F.countDistinct("item_id").alias("items_cnt"),
        F.countDistinct("category_id").alias("cats_cnt"),
        cnt((d == last_day) & (b == "pv")).alias("pv_last_day"),
        cnt((d == last_day) & (b == "cart")).alias("cart_last_day"),
        cnt((d == last_day) & (b == "buy")).alias("buy_last_day"),
        F.max("day").alias("_last_active"),
        F.max(F.when(b == "buy", d)).alias("_last_buy"),
    )

    # 待转化意图：加购/收藏了、但观察窗内没买的商品数
    pair = o.groupBy("user_id", "item_id").agg(
        F.max(F.when(b == "cart", 1).otherwise(0)).alias("c"),
        F.max(F.when(b == "fav", 1).otherwise(0)).alias("f"),
        F.max(F.when(b == "buy", 1).otherwise(0)).alias("y"),
    )
    pending = pair.groupBy("user_id").agg(
        F.sum(F.when((F.col("c") == 1) & (F.col("y") == 0), 1).otherwise(0)).alias("cart_pending"),
        F.sum(F.when((F.col("f") == 1) & (F.col("y") == 0), 1).otherwise(0)).alias("fav_pending"),
    )

    feat = (
        base.join(pending, "user_id", "left")
        .withColumn("days_since_active", F.lit(last_day) - F.col("_last_active"))
        # 观察窗内从未购买：记为窗口长度（含义是"至少这么久没买"）
        .withColumn("days_since_buy",
                    F.when(F.col("_last_buy").isNull(), F.lit(window_len))
                    .otherwise(F.lit(last_day) - F.col("_last_buy")))
        .withColumn("buy_pv_ratio", F.when(F.col("pv_cnt") > 0, F.col("buy_cnt") / F.col("pv_cnt")).otherwise(0.0))
        .withColumn("cart_pv_ratio", F.when(F.col("pv_cnt") > 0, F.col("cart_cnt") / F.col("pv_cnt")).otherwise(0.0))
        .withColumn("fav_pv_ratio", F.when(F.col("pv_cnt") > 0, F.col("fav_cnt") / F.col("pv_cnt")).otherwise(0.0))
    )

    # 标签：预测窗内是否至少购买一次
    lab = (
        df.filter((d >= label_start) & (d < label_end) & (b == "buy"))
        .select("user_id").distinct().withColumn("label", F.lit(1))
    )
    out = (
        feat.join(lab, "user_id", "left")
        .fillna({"label": 0})
        .withColumn("snapshot", F.lit(name))
        .select("snapshot", "user_id", *FEATURES, "label")
    )
    return out


def main():
    args = parse_args()
    setup_java(args.java_home)

    from pyspark.sql import SparkSession, functions as F

    src = args.input or (ROOT / "data" / "sample_5pct.csv" if args.sample else ROOT / "UserBehavior.csv")
    src = Path(src)
    if not src.exists():
        sys.exit(f"找不到输入文件：{src}")

    try:
        import pyarrow  # noqa: F401
        arrow = "true"
    except ImportError:
        arrow = "false"

    spark = (
        SparkSession.builder.master("local[*]").appName("taobao-features")
        .config("spark.driver.memory", args.driver_memory)
        .config("spark.driver.maxResultSize", "4g")
        .config("spark.sql.shuffle.partitions", "64")
        .config("spark.sql.execution.arrow.pyspark.enabled", arrow)
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    t0 = time.time()
    print(f"Spark {spark.version}，输入：{src}")

    raw = spark.read.csv(src.as_uri(), schema="user_id INT, item_id INT, category_id INT, behavior STRING, ts LONG")
    df = (
        raw.filter((F.col("ts") >= START_TS) & (F.col("ts") < START_TS + N_DAYS * DAY))  # 剔除异常时间戳
        .withColumn("day", F.floor((F.col("ts") - START_TS) / DAY).cast("int"))
        .select("user_id", "item_id", "category_id", "behavior", "day")
    )

    parts = [build_snapshot(df, name, obs, label) for name, obs, label in SNAPSHOTS]
    result = parts[0]
    for p in parts[1:]:
        result = result.unionByName(p)

    print("开始计算（会扫描 CSV，全量数据需要几分钟）……")
    pdf = result.toPandas()
    print(f"聚合完成，用时 {time.time() - t0:.0f} 秒，共 {len(pdf):,} 行")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    pdf.to_csv(args.output, index=False)
    print(f"已保存：{args.output}")
    summary = pdf.groupby("snapshot").agg(users=("user_id", "count"), buyers=("label", "sum"), label_rate=("label", "mean"))
    print(summary.to_string())
    spark.stop()


if __name__ == "__main__":
    main()
