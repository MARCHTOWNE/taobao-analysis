"""sklearn 购买预测：用观察窗内的行为特征，预测用户在随后 2 天内是否购买。

评估设计（避免两类泄露）：
  1) 时间向前：训练用 train 快照（预测窗 11/30-12/01），测试用 test 快照（预测窗 12/02-12/03）
  2) 用户互不重叠：按 user_id 的哈希值 % 10 把用户分开 —— 0、1（约 20%）只用于测试，2（约 10%）用于选阈值，其余用于训练
模型：规则基线（观察窗内买过 = 会再买）、逻辑回归、HistGradientBoosting（sklearn 自带的梯度提升树）
指标：ROC-AUC、PR-AUC（average precision，更适合类别不均衡）、阈值下的精确率/召回率/F1

用法：
    pip install pandas matplotlib scikit-learn
    python scripts/train_models.py
输出：figures/06_model_curves.png、figures/07_feature_importance.png、models/metrics.json
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_figures import BLUE, GRID, INK, INK2, ORANGE, SURFACE, setup_style, style_axes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEATURES = [
    "pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "active_days", "items_cnt", "cats_cnt",
    "pv_last_day", "cart_last_day", "buy_last_day", "days_since_active", "days_since_buy",
    "cart_pending", "fav_pending", "buy_pv_ratio", "cart_pv_ratio", "fav_pv_ratio",
]
LOG_COLS = ["pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "items_cnt", "cats_cnt",
            "pv_last_day", "cart_last_day", "buy_last_day", "cart_pending", "fav_pending"]
CN = {
    "pv_cnt": "浏览次数", "fav_cnt": "收藏次数", "cart_cnt": "加购次数", "buy_cnt": "购买次数",
    "active_days": "活跃天数", "items_cnt": "浏览商品数", "cats_cnt": "浏览类目数",
    "pv_last_day": "最后一天浏览", "cart_last_day": "最后一天加购", "buy_last_day": "最后一天购买",
    "days_since_active": "距上次活跃天数", "days_since_buy": "距上次购买天数",
    "cart_pending": "加购未买商品数", "fav_pending": "收藏未买商品数",
    "buy_pv_ratio": "购买/浏览", "cart_pv_ratio": "加购/浏览", "fav_pv_ratio": "收藏/浏览",
}
GRAY = "#8a8984"
NOTE = "数据：淘宝用户行为数据集全量；训练=11/25-11/29 行为预测 11/30-12/01，测试=11/27-12/01 行为预测 12/02-12/03；测试用户与训练用户互不重叠"


def log_prep(X):
    X = X.copy()
    X[LOG_COLS] = np.log1p(X[LOG_COLS])
    return X


def metrics(y, score, thr):
    pred = (score >= thr).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "threshold": float(thr),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
    }


def best_f1_threshold(y, score):
    p, r, t = precision_recall_curve(y, score)
    f1 = 2 * p[:-1] * r[:-1] / np.maximum(p[:-1] + r[:-1], 1e-12)
    return float(t[int(np.argmax(f1))])


def plot_curves(y, scores, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    styles = {"规则基线（观察窗内买过）": (GRAY, "--"), "逻辑回归": (ORANGE, "-"), "梯度提升树": (BLUE, "-")}
    for name, s in scores.items():
        color, ls = styles[name]
        fpr, tpr, _ = roc_curve(y, s)
        a1.plot(fpr, tpr, color=color, linestyle=ls, linewidth=2,
                label=f"{name}（AUC {roc_auc_score(y, s):.3f}）")
        p, r, _ = precision_recall_curve(y, s)
        a2.plot(r, p, color=color, linestyle=ls, linewidth=2,
                label=f"{name}（PR-AUC {average_precision_score(y, s):.3f}）")
    a1.plot([0, 1], [0, 1], color=GRID, linewidth=1)
    a1.set_title("ROC 曲线", loc="left", fontsize=11)
    a1.set_xlabel("假阳性率")
    a1.set_ylabel("真阳性率")
    a2.axhline(y.mean(), color=GRID, linewidth=1.5)
    a2.text(0.5, y.mean() - 0.045, f"随机猜测 = 购买用户占比 {y.mean():.1%}", ha="center", fontsize=8.5, color=INK2)
    a2.set_title("精确率-召回率曲线", loc="left", fontsize=11)
    a2.set_xlabel("召回率")
    a2.set_ylabel("精确率")
    a2.set_ylim(0, 1.02)
    for ax in (a1, a2):
        style_axes(ax)
        ax.legend(loc="lower right" if ax is a1 else "upper right", fontsize=9, frameon=False)
    ap = {n: average_precision_score(y, s) for n, s in scores.items()}
    fig.suptitle("购买预测模型对比（时间向前、用户不重叠的测试集）",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.905, "PR-AUC：" + "，".join(f"{n.split('（')[0]} {v:.3f}" for n, v in ap.items()),
             fontsize=10, color=INK2)
    fig.text(0.01, 0.01, NOTE, fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def plot_importance(names, values, out):
    order = np.argsort(values)[::-1][:12]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    y = list(range(len(order)))
    ax.barh(y, values[order], color=BLUE, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels([CN[names[i]] for i in order])
    ax.invert_yaxis()
    for yi, i in zip(y, order):
        ax.text(values[i] + values.max() * 0.01, yi, f"{values[i]:.4f}", va="center", fontsize=9, color=INK2)
    ax.set_xlim(0, values.max() * 1.15)
    ax.set_xlabel("打乱该特征后 PR-AUC 的下降幅度（越大越重要）")
    style_axes(ax, grid="x")
    ax.set_title("影响购买预测的主要特征（排列重要性，前 12）", loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, NOTE, fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


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
    # 用 user_id 的哈希值分组，避免与抽样规则（user_id % 20）等取模规则相关
    g = pd.util.hash_array(df["user_id"].to_numpy().astype("int64")) % 10
    g = pd.Series(g, index=df.index)
    train = df[(df["snapshot"] == "train") & (g >= 3)]
    val = df[(df["snapshot"] == "train") & (g == 2)]
    test = df[(df["snapshot"] == "test") & (g <= 1)]
    print(f"训练 {len(train):,} 行（购买占比 {train.label.mean():.1%}），验证 {len(val):,} 行，测试 {len(test):,} 行（购买占比 {test.label.mean():.1%}）")
    Xtr, ytr = train[FEATURES], train["label"].values
    Xva, yva = val[FEATURES], val["label"].values
    Xte, yte = test[FEATURES], test["label"].values

    scores_val, scores_te, models = {}, {}, {}

    # 规则基线：观察窗内买过几次，就按几次排序
    scores_val["规则基线（观察窗内买过）"] = Xva["buy_cnt"].values.astype(float)
    scores_te["规则基线（观察窗内买过）"] = Xte["buy_cnt"].values.astype(float)

    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, C=1.0))
    lr.fit(log_prep(Xtr), ytr)
    scores_val["逻辑回归"] = lr.predict_proba(log_prep(Xva))[:, 1]
    scores_te["逻辑回归"] = lr.predict_proba(log_prep(Xte))[:, 1]

    hgb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
                                         l2_regularization=1.0, early_stopping=True,
                                         validation_fraction=0.1, random_state=42)
    hgb.fit(Xtr, ytr)
    scores_val["梯度提升树"] = hgb.predict_proba(Xva)[:, 1]
    scores_te["梯度提升树"] = hgb.predict_proba(Xte)[:, 1]
    print(f"梯度提升树实际迭代 {hgb.n_iter_} 轮")

    result = {}
    for name in scores_te:
        thr = 1.0 if name.startswith("规则") else best_f1_threshold(yva, scores_val[name])
        result[name] = metrics(yte, scores_te[name], thr)
    result["_meta"] = {"train_rows": int(len(train)), "val_rows": int(len(val)), "test_rows": int(len(test)),
                       "test_positive_rate": float(yte.mean())}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    (Path(args.model_dir) / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    plot_curves(yte, scores_te, Path(args.fig_dir) / "06_model_curves.png")

    rng = np.random.RandomState(0)
    idx = rng.choice(len(Xte), size=min(50000, len(Xte)), replace=False)
    pi = permutation_importance(hgb, Xte.iloc[idx], yte[idx], scoring="average_precision",
                                n_repeats=3, random_state=0, n_jobs=-1)
    plot_importance(FEATURES, pi.importances_mean, Path(args.fig_dir) / "07_feature_importance.png")
    top = np.argsort(pi.importances_mean)[::-1][:5]
    print("最重要的 5 个特征：", [(CN[FEATURES[i]], round(float(pi.importances_mean[i]), 4)) for i in top])


if __name__ == "__main__":
    main()
