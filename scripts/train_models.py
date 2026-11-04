"""Purchase prediction with scikit-learn: from 5 days of behavior features, predict whether a user buys in the next 2 days.
sklearn 购买预测：用观察窗内的行为特征，预测用户在随后 2 天内是否购买。

Evaluation design (avoids two kinds of leakage) / 评估设计（避免两类泄露）:
  1) Time-forward / 时间向前：训练用 train 快照（预测窗 11/30-12/01），测试用 test 快照（预测窗 12/02-12/03）
  2) User-disjoint / 用户互不重叠：按 user_id 的哈希值 % 10 分组 —— 0、1（约 20%）只用于测试，
     2（约 10%）用于选阈值，其余用于训练
Models / 模型：rule baseline (bought in window), logistic regression, HistGradientBoosting
Metrics / 指标：ROC-AUC, PR-AUC (average precision), precision / recall / F1 at a threshold

Usage / 用法:
    pip install pandas matplotlib scikit-learn
    python scripts/train_models.py              # Chinese charts -> figures/
    python scripts/train_models.py --lang en    # English charts -> figures/en/
Output / 输出：figures/06_model_curves.png, figures/07_feature_importance.png, models/metrics.json
"""
import argparse
import json
import sys
import textwrap
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
import labels  # noqa: E402
from make_figures import BLUE, GRID, INK, INK2, ORANGE, SURFACE, setup_style, style_axes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEATURES = [
    "pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "active_days", "items_cnt", "cats_cnt",
    "pv_last_day", "cart_last_day", "buy_last_day", "days_since_active", "days_since_buy",
    "cart_pending", "fav_pending", "buy_pv_ratio", "cart_pv_ratio", "fav_pv_ratio",
]
LOG_COLS = ["pv_cnt", "fav_cnt", "cart_cnt", "buy_cnt", "items_cnt", "cats_cnt",
            "pv_last_day", "cart_last_day", "buy_last_day", "cart_pending", "fav_pending"]
GRAY = "#8a8984"
MODEL_KEYS = ["rule", "lr", "gb"]  # also the display order
MODEL_STYLE = {"rule": (GRAY, "--"), "lr": (ORANGE, "-"), "gb": (BLUE, "-")}
JSON_KEYS = {"rule": "rule_baseline", "lr": "logistic_regression", "gb": "gradient_boosting"}


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


def plot_curves(S, y, scores, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    ap = {}
    for key in MODEL_KEYS:
        s = scores[key]
        name = S["m_" + key]
        color, ls = MODEL_STYLE[key]
        fpr, tpr, _ = roc_curve(y, s)
        a1.plot(fpr, tpr, color=color, linestyle=ls, linewidth=2,
                label=S["auc_label"].format(name=name, v=roc_auc_score(y, s)))
        p, r, _ = precision_recall_curve(y, s)
        ap[name] = average_precision_score(y, s)
        a2.plot(r, p, color=color, linestyle=ls, linewidth=2,
                label=S["prauc_label"].format(name=name, v=ap[name]))
    a1.plot([0, 1], [0, 1], color=GRID, linewidth=1)
    a1.set_title(S["roc_title"], loc="left", fontsize=11)
    a1.set_xlabel(S["fpr"])
    a1.set_ylabel(S["tpr"])
    a2.axhline(y.mean(), color=GRID, linewidth=1.5)
    a2.text(0.5, y.mean() - 0.045, S["random_text"].format(r=y.mean()), ha="center", fontsize=8.5, color=INK2)
    a2.set_title(S["pr_title"], loc="left", fontsize=11)
    a2.set_xlabel(S["recall"])
    a2.set_ylabel(S["precision"])
    a2.set_ylim(0, 1.02)
    for ax in (a1, a2):
        style_axes(ax)
        ax.legend(loc="lower right" if ax is a1 else "upper right", fontsize=9, frameon=False)
    fig.suptitle(S["curves_title"], x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.905,
             S["prauc_prefix"] + S["prauc_sep"].join(f"{n.split('（')[0].split(' (')[0]} {v:.3f}" for n, v in ap.items()),
             fontsize=10, color=INK2)
    fig.text(0.01, 0.01, S["model_note"], fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def plot_importance(S, names, values, out, wrap=None):
    order = np.argsort(values)[::-1][:12]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    y = list(range(len(order)))
    ax.barh(y, values[order], color=BLUE, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels([S["features"][names[i]] for i in order])
    ax.invert_yaxis()
    for yi, i in zip(y, order):
        ax.text(values[i] + values.max() * 0.01, yi, f"{values[i]:.4f}", va="center", fontsize=9, color=INK2)
    ax.set_xlim(0, values.max() * 1.15)
    ax.set_xlabel(S["imp_xlabel"])
    style_axes(ax, grid="x")
    ax.set_title(S["imp_title"], loc="left", fontsize=13, fontweight="bold")
    note = textwrap.fill(S["model_note"], wrap) if wrap else S["model_note"]
    fig.text(0.01, 0.01, note, fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.07 if wrap else 0.04, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


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
    # 用 user_id 的哈希值分组，避免与抽样规则（user_id % 20）等取模规则相关
    # Group users by a hash of user_id so the split is independent of modulo-based sampling rules.
    g = pd.util.hash_array(df["user_id"].to_numpy().astype("int64")) % 10
    g = pd.Series(g, index=df.index)
    train = df[(df["snapshot"] == "train") & (g >= 3)]
    val = df[(df["snapshot"] == "train") & (g == 2)]
    test = df[(df["snapshot"] == "test") & (g <= 1)]
    print(f"train {len(train):,} rows (buyers {train.label.mean():.1%}), validation {len(val):,}, "
          f"test {len(test):,} (buyers {test.label.mean():.1%})")
    Xtr, ytr = train[FEATURES], train["label"].values
    Xva, yva = val[FEATURES], val["label"].values
    Xte, yte = test[FEATURES], test["label"].values

    scores_val, scores_te = {}, {}

    # 规则基线：观察窗内买过几次，就按几次排序 / rule baseline: rank users by purchases in the observation window
    scores_val["rule"] = Xva["buy_cnt"].values.astype(float)
    scores_te["rule"] = Xte["buy_cnt"].values.astype(float)

    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, C=1.0))
    lr.fit(log_prep(Xtr), ytr)
    scores_val["lr"] = lr.predict_proba(log_prep(Xva))[:, 1]
    scores_te["lr"] = lr.predict_proba(log_prep(Xte))[:, 1]

    hgb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
                                         l2_regularization=1.0, early_stopping=True,
                                         validation_fraction=0.1, random_state=42)
    hgb.fit(Xtr, ytr)
    scores_val["gb"] = hgb.predict_proba(Xva)[:, 1]
    scores_te["gb"] = hgb.predict_proba(Xte)[:, 1]
    print(f"Gradient boosting used {hgb.n_iter_} iterations")

    zh, en = labels.get("zh"), labels.get("en")
    result = {}
    for key in MODEL_KEYS:
        thr = 1.0 if key == "rule" else best_f1_threshold(yva, scores_val[key])
        result[JSON_KEYS[key]] = {"name_zh": zh["m_" + key], "name_en": en["m_" + key],
                                  **metrics(yte, scores_te[key], thr)}
    result["_meta"] = {"train_rows": int(len(train)), "val_rows": int(len(val)), "test_rows": int(len(test)),
                       "test_positive_rate": float(yte.mean())}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    (Path(args.model_dir) / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    plot_curves(S, yte, scores_te, fig_dir / "06_model_curves.png")

    rng = np.random.RandomState(0)
    idx = rng.choice(len(Xte), size=min(50000, len(Xte)), replace=False)
    pi = permutation_importance(hgb, Xte.iloc[idx], yte[idx], scoring="average_precision",
                                n_repeats=3, random_state=0, n_jobs=-1)
    plot_importance(S, FEATURES, pi.importances_mean, fig_dir / "07_feature_importance.png",
                    wrap=110 if args.lang == "en" else None)
    top = np.argsort(pi.importances_mean)[::-1][:5]
    print("Top 5 features:", [(S["features"][FEATURES[i]], round(float(pi.importances_mean[i]), 4)) for i in top])


if __name__ == "__main__":
    main()
