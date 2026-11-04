"""User segmentation (K-Means): group users into 4 segments by 5-day behavior profile.
用户分群（K-Means）：把用户按 5 天内的行为画像分成 4 类，便于描述和运营解读。

Notes (keep when reporting) / 说明（写报告时请保留）:
  - Only behavior features are used (views/favorites/carts/purchases, active days, categories viewed;
    log1p then standardized). The "next 2-day purchase rate" only describes the segments; it is not a clustering input.
    分群只使用行为特征，“之后 2 天购买率”只用来描述各群，不参与分群。
  - The silhouette score is low (~0.25): behavior is continuous, there are no naturally separated clusters.
    K=4 is chosen for interpretability; segments are a descriptive tool.
    轮廓系数偏低（约 0.25），说明用户行为是连续分布、没有天然分开的簇；分群是描述工具，K=4 是为了可解释。
  - Uses the observation window of the test snapshot (11/27–12/01). / 使用 test 快照的观察窗（11/27–12/01）。

Usage / 用法:
    python scripts/cluster_users.py              # Chinese -> figures/08_user_segments.png, models/segment_profile.csv
    python scripts/cluster_users.py --lang en    # English -> figures/en/08_user_segments.png, models/segment_profile.en.csv
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
import labels  # noqa: E402
from make_figures import BLUE, INK2, ORANGE, setup_style, style_axes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEATS = ["pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "active_days", "cats_cnt"]
K = 4


def name_segments(prof):
    """Name segments by rule on the profile medians (returns label keys); fall back to a generic name.
    按画像中位数用规则命名（返回标签键）；结构不符合预期时退回通用名。"""
    keys = {}
    heavy = prof[(prof["active_days"] >= 5) & (prof["pv_cnt"] >= 50)].index.tolist()
    light = [s for s in prof.index if s not in heavy]
    if len(heavy) == 2:
        a, b = sorted(heavy, key=lambda s: prof.loc[s, "fav_cnt"])
        keys[a], keys[b] = "seg_cart", "seg_fav"
    if len(light) == 2:
        lo, hi = sorted(light, key=lambda s: prof.loc[s, "pv_cnt"])
        keys[lo], keys[hi] = "seg_low", "seg_mid"
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(ROOT / "data" / "user_features.csv"))
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--fig-dir", default=None)
    ap.add_argument("--model-dir", default=str(ROOT / "models"))
    args = ap.parse_args()
    S = labels.get(args.lang)
    fig_dir = Path(args.fig_dir) if args.fig_dir else (ROOT / "figures" if args.lang == "zh" else ROOT / "figures" / "en")
    setup_style(args.lang)
    fig_dir.mkdir(parents=True, exist_ok=True)
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
    print(f"Users {len(d):,}, K={K}, silhouette (30K-user sample) = {sil:.3f}")

    med = d.groupby("seg")[FEATS].median()
    keys = name_segments(med)
    names = {s: (S[keys[s]] if s in keys else f"{'群' if args.lang == 'zh' else 'Segment '}{s}") for s in med.index}
    g = d.groupby("seg").agg(
        users=("user_id", "count"),
        bought_in_window=("buy_cnt", lambda s: (s > 0).mean()),
        next_buy_rate=("label", "mean"),
    )
    g["share"] = g["users"] / g["users"].sum()
    prof = med.join(g)
    prof["name"] = [names[s] for s in prof.index]
    prof = prof.loc[prof.sort_values(["pv_cnt", "buy_cnt"]).index]

    # CSV：列顺序固定，表头按语言输出 / fixed column order, header in the chosen language
    cols = ["name", "users", "share", "pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "active_days", "cats_cnt",
            "bought_in_window", "next_buy_rate"]
    out = prof[cols].copy()
    out.columns = S["segment_columns"]
    csv_name = "segment_profile.csv" if args.lang == "zh" else "segment_profile.en.csv"
    out.to_csv(Path(args.model_dir) / csv_name, index=False, encoding="utf-8-sig")
    print(out.round(3).to_string(index=False))

    overall = d["label"].mean()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
    labs = prof["name"].tolist()
    y = list(range(len(labs)))
    panels = [("share", S["seg_panel_share"]), ("bought_in_window", S["seg_panel_bought"]),
              ("next_buy_rate", S["seg_panel_next"])]
    for ax, (col, title) in zip(axes, panels):
        vals = prof[col].values
        ax.barh(y, vals, color=BLUE, height=0.6)
        for yi, v in zip(y, vals):
            # 第三个面板有“全体”参考线，标签放到参考线右侧，避免被线盖住
            # Third panel has an overall reference line: put labels to the right of it.
            x = max(v, overall) if col == "next_buy_rate" else v
            ax.text(x + 0.012, yi, f"{v:.1%}", va="center", fontsize=9, color=INK2)
        ax.set_xlim(0, max(vals.max() * 1.25, 0.5 if col != "share" else 0.0))
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_yticks(y)
        ax.set_yticklabels(labs)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        style_axes(ax, grid="x")
    axes[0].set_ylim(-0.6, len(labs) - 0.1)  # 顶部留白放参考线标注 / headroom for the reference-line label
    axes[2].axvline(overall, color=ORANGE, linewidth=2, linestyle="--")
    axes[2].text(overall, len(labs) - 0.5, S["seg_overall"].format(x=overall), color=ORANGE, fontsize=9, ha="center")
    axes[0].set_xlim(0, prof["share"].max() * 1.3)
    hi, lo = prof["next_buy_rate"].idxmax(), prof["next_buy_rate"].idxmin()
    fig.suptitle(S["seg_title"].format(hi=prof.loc[hi, "next_buy_rate"], hin=names[hi],
                                       lo=prof.loc[lo, "next_buy_rate"], lon=names[lo]),
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, S["seg_note"] + S["seg_note_suffix"].format(k=K, sil=sil), fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(fig_dir / "08_user_segments.png", dpi=160)
    plt.close(fig)
    print(f"Generated {fig_dir / '08_user_segments.png'} and {Path(args.model_dir) / csv_name}")


if __name__ == "__main__":
    main()
