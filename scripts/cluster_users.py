"""用户分群（K-Means）：把用户按 5 天内的行为画像分成 4 类，便于描述和运营解读。

说明（写报告时请保留）：
  - 分群只使用行为特征（浏览/收藏/加购/购买次数、活跃天数、浏览类目数，取 log1p 后标准化），
    "之后 2 天购买率"只用来描述各群，不参与分群。
  - 轮廓系数偏低（约 0.25），说明用户行为是连续分布、没有天然分开的簇；
    这里分群是一种描述工具，k=4 是为了可解释，而不是数据本身分成了 4 类。
  - 使用 test 快照的观察窗（11/27–12/01）。

用法：
    python scripts/cluster_users.py
输出：figures/08_user_segments.png、models/segment_profile.csv
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_figures import BLUE, INK2, ORANGE, setup_style, style_axes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEATS = ["pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "active_days", "cats_cnt"]
K = 4
NOTE = "数据：淘宝用户行为数据集全量，观察窗 11/27–12/01（约 98 万用户）；“之后购买率”为 12/02–12/03 内是否购买"


def name_segments(prof):
    """按画像中位数用规则命名；结构不符合预期时退回“群 N”。"""
    names = {}
    heavy = prof[(prof["active_days"] >= 5) & (prof["pv_cnt"] >= 50)].index.tolist()
    light = [s for s in prof.index if s not in heavy]
    if len(heavy) == 2:
        a, b = sorted(heavy, key=lambda s: prof.loc[s, "fav_cnt"])
        names[a], names[b] = "高活跃·加购购买型", "高活跃·收藏型"
    if len(light) == 2:
        lo, hi = sorted(light, key=lambda s: prof.loc[s, "pv_cnt"])
        names[lo], names[hi] = "低活跃型", "中等活跃·浏览型"
    for s in prof.index:
        names.setdefault(s, f"群{s}")
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(ROOT / "data" / "user_features.csv"))
    ap.add_argument("--fig-dir", default=str(ROOT / "figures"))
    ap.add_argument("--model-dir", default=str(ROOT / "models"))
    args = ap.parse_args()
    setup_style()
    Path(args.fig_dir).mkdir(exist_ok=True)
    Path(args.model_dir).mkdir(exist_ok=True)

    df = pd.read_csv(args.features)
    d = df[df["snapshot"] == "test"].reset_index(drop=True)
    X = StandardScaler().fit_transform(np.log1p(d[FEATS].astype(float)))
    rng = np.random.RandomState(0)
    fit_idx = rng.choice(len(X), size=min(100000, len(X)), replace=False)
    km = KMeans(K, n_init=5, random_state=0).fit(X[fit_idx])
    d["seg"] = km.predict(X)
    sil_idx = rng.choice(len(X), size=min(30000, len(X)), replace=False)
    sil = silhouette_score(X[sil_idx], km.predict(X[sil_idx]))
    print(f"用户数 {len(d):,}，K={K}，轮廓系数（3 万用户抽样）= {sil:.3f}")

    med = d.groupby("seg")[FEATS].median()
    names = name_segments(med)
    g = d.groupby("seg").agg(
        users=("user_id", "count"),
        bought_in_window=("buy_cnt", lambda s: (s > 0).mean()),
        next_buy_rate=("label", "mean"),
    )
    g["share"] = g["users"] / g["users"].sum()
    prof = med.join(g)
    prof["name"] = [names[s] for s in prof.index]
    order = prof.sort_values(["pv_cnt", "buy_cnt"]).index
    prof = prof.loc[order]

    out = prof.rename(columns={
        "name": "分群", "users": "用户数", "share": "占比", "pv_cnt": "浏览中位数", "fav_cnt": "收藏中位数",
        "cart_cnt": "加购中位数", "buy_cnt": "购买中位数", "active_days": "活跃天数中位数", "cats_cnt": "浏览类目数中位数",
        "bought_in_window": "观察窗内购买过占比", "next_buy_rate": "之后2天购买率"})
    cols = ["分群", "用户数", "占比", "浏览中位数", "收藏中位数", "加购中位数", "购买中位数",
            "活跃天数中位数", "浏览类目数中位数", "观察窗内购买过占比", "之后2天购买率"]
    out[cols].to_csv(Path(args.model_dir) / "segment_profile.csv", index=False, encoding="utf-8-sig")
    print(out[cols].round(3).to_string(index=False))

    overall = d["label"].mean()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
    labels = prof["name"].tolist()
    y = list(range(len(labels)))
    panels = [("share", "占全部用户的比例"), ("bought_in_window", "观察窗内购买过的用户占比"),
              ("next_buy_rate", "之后 2 天购买率")]
    for ax, (col, title) in zip(axes, panels):
        vals = prof[col].values
        ax.barh(y, vals, color=BLUE, height=0.6)
        for yi, v in zip(y, vals):
            # 第三个面板有“全体”参考线，标签放到参考线右侧，避免被线盖住
            x = max(v, overall) if col == "next_buy_rate" else v
            ax.text(x + 0.012, yi, f"{v:.1%}", va="center", fontsize=9, color=INK2)
        ax.set_xlim(0, max(vals.max() * 1.25, 0.5 if col != "share" else 0.0))
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        style_axes(ax, grid="x")
    axes[2].axvline(overall, color=ORANGE, linewidth=2, linestyle="--")
    axes[2].text(overall, len(labels) - 0.45, f"全体 {overall:.1%}", color=ORANGE, fontsize=9, ha="center")
    axes[0].set_xlim(0, prof["share"].max() * 1.3)
    hi, lo = prof["next_buy_rate"].idxmax(), prof["next_buy_rate"].idxmin()
    fig.suptitle(f"用户分群画像：之后购买率最高 {prof.loc[hi, 'next_buy_rate']:.1%}（{names[hi]}），"
                 f"最低 {prof.loc[lo, 'next_buy_rate']:.1%}（{names[lo]}）",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, NOTE + f"；K-Means（K={K}），轮廓系数 {sil:.2f}，分群为描述工具", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(Path(args.fig_dir) / "08_user_segments.png", dpi=160)
    plt.close(fig)
    print("已生成 figures/08_user_segments.png 和 models/segment_profile.csv")


if __name__ == "__main__":
    main()
