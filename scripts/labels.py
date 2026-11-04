"""Chinese / English labels for charts and output files.
图表与输出文件的中英文标签。每个键对应 (中文, English)，保证两种语言一一对应。

Usage: S = labels.get("en")  or  labels.get("zh")
"""

_STR = {
    # ---- common ----
    "sample_note": (
        "数据：淘宝用户行为数据集，按用户抽样 5%（约 4.9 万用户），2017-11-25 至 12-03",
        "Data: Taobao user-behavior dataset, 5% user sample (~49K users), 2017-11-25 to 12-03",
    ),
    # ---- fig 01 daily ----
    "daily_title": (
        "12 月 2–3 日访问用户数比此前日均高约 {jump:.0%}（橙色为这两天）",
        "Daily visitors on Dec 2–3 were about {jump:.0%} above the prior daily average (orange)",
    ),
    "daily_uv": ("每日访问用户数（UV）", "Daily visitors (UV)"),
    "daily_pv": ("每日浏览量（PV）", "Daily page views (PV)"),
    "daily_buy": ("每日购买次数", "Daily purchases"),
    # ---- fig 02 hourly ----
    "hourly_pv_title": ("各小时浏览量（9 天合计）", "Page views by hour (9-day total)"),
    "hour_xlabel": ("小时", "Hour of day"),
    "hourly_peak_pv": ("{h} 时浏览最多", "Most views at {h}:00"),
    "hourly_conv_title": ("各小时购买次数 / 浏览次数（%）", "Purchases per page view (%)"),
    "hourly_peak_conv": ("{h} 时最高 {v:.2f}%", "Peak at {h}:00: {v:.2f}%"),
    "hourly_suptitle": ("浏览高峰在晚间，转化高峰在上午", "Views peak in the evening; conversion peaks in the morning"),
    # ---- fig 03 funnel ----
    "funnel_s1": ("浏览过的用户-商品对", "User–item pairs viewed"),
    "funnel_s2": ("其中收藏或加购过", "…of which favorited or carted"),
    "funnel_s3": ("收藏/加购后购买", "Bought after fav/cart"),
    "funnel_s4": ("未收藏/加购、直接购买", "Bought directly (no fav/cart)"),
    "funnel_note_view": ("{v:,.0f}（占浏览 {p:.1%}）", "{v:,.0f} ({p:.1%} of viewed)"),
    "funnel_note_fc": ("{v:,.0f}（占收藏/加购 {p:.1%}）", "{v:,.0f} ({p:.1%} of fav/cart)"),
    "funnel_xlabel": ("用户-商品对数量", "Number of user–item pairs"),
    "funnel_title": (
        "直接购买的商品数量多于收藏/加购后再购买的",
        "More items are bought directly than after being favorited or carted",
    ),
    "funnel_footer": (
        "；漏斗按“是否发生过该行为”统计，不要求时间顺序",
        "; funnel counts whether a behavior occurred at all, regardless of order",
    ),
    # ---- fig 04 category ----
    "cat_label": ("类目 {c}", "Category {c}"),
    "cat_overall": ("整体 {x:.2f}%", "Overall {x:.2f}%"),
    "cat_value": ("{v:.2f}%   浏览 {pv_wan:.1f} 万", "{v:.2f}%   {pv_k:.0f}K views"),
    "cat_xlabel": ("购买次数 / 浏览次数（%）", "Purchases per page view (%)"),
    "cat_title": ("浏览量前 20 的类目：转化率差异很大", "Top 20 categories by page views: conversion varies widely"),
    "cat_footer": ("；自上而下按浏览量从高到低", "; sorted by page views, highest at top"),
    # ---- fig 05 repurchase ----
    "rep_xlabel": ("9 天内购买次数", "Purchases within 9 days"),
    "rep_title": (
        "购买用户的购买次数分布：复购用户占 {rate:.1f}%",
        "Purchases per buyer: {rate:.1f}% bought more than once",
    ),
    # ---- fig 06/07 models ----
    "m_rule": ("规则基线（观察窗内买过）", "Rule baseline (bought in window)"),
    "m_lr": ("逻辑回归", "Logistic regression"),
    "m_gb": ("梯度提升树", "Gradient boosting"),
    "roc_title": ("ROC 曲线", "ROC curve"),
    "fpr": ("假阳性率", "False positive rate"),
    "tpr": ("真阳性率", "True positive rate"),
    "auc_label": ("{name}（AUC {v:.3f}）", "{name} (AUC {v:.3f})"),
    "pr_title": ("精确率-召回率曲线", "Precision–recall curve"),
    "recall": ("召回率", "Recall"),
    "precision": ("精确率", "Precision"),
    "prauc_label": ("{name}（PR-AUC {v:.3f}）", "{name} (PR-AUC {v:.3f})"),
    "random_text": ("随机猜测 = 购买用户占比 {r:.1%}", "Random guess = buyer rate {r:.1%}"),
    "curves_title": (
        "购买预测模型对比（时间向前、用户不重叠的测试集）",
        "Purchase prediction: model comparison (time-forward, user-disjoint test set)",
    ),
    "prauc_prefix": ("PR-AUC：", "PR-AUC: "),
    "prauc_sep": ("，", ", "),
    "model_note": (
        "数据：淘宝用户行为数据集全量；训练=11/25-11/29 行为预测 11/30-12/01，测试=11/27-12/01 行为预测 12/02-12/03；测试用户与训练用户互不重叠",
        "Data: full Taobao user-behavior dataset; train = behavior 11/25–11/29 predicting 11/30–12/01; "
        "test = behavior 11/27–12/01 predicting 12/02–12/03; test users do not overlap with training users",
    ),
    "imp_title": ("影响购买预测的主要特征（排列重要性，前 12）", "Top 12 features by permutation importance"),
    "imp_xlabel": (
        "打乱该特征后 PR-AUC 的下降幅度（越大越重要）",
        "Drop in PR-AUC when the feature is shuffled (larger = more important)",
    ),
    # ---- fig 08 segments ----
    "seg_low": ("低活跃型", "Low activity"),
    "seg_mid": ("中等活跃·浏览型", "Medium activity · browsers"),
    "seg_fav": ("高活跃·收藏型", "High activity · favoriters"),
    "seg_cart": ("高活跃·加购购买型", "High activity · cart & buy"),
    "seg_panel_share": ("占全部用户的比例", "Share of all users"),
    "seg_panel_bought": ("观察窗内购买过的用户占比", "Bought during observation window"),
    "seg_panel_next": ("之后 2 天购买率", "Bought in the following 2 days"),
    "seg_overall": ("全体 {x:.1%}", "All users {x:.1%}"),
    "seg_title": (
        "用户分群画像：之后购买率最高 {hi:.1%}（{hin}），最低 {lo:.1%}（{lon}）",
        "User segments: next-2-day purchase rate from {lo:.1%} ({lon}) to {hi:.1%} ({hin})",
    ),
    "seg_note": (
        "数据：淘宝用户行为数据集全量，观察窗 11/27–12/01（约 98 万用户）；“之后购买率”为 12/02–12/03 内是否购买",
        "Data: full Taobao user-behavior dataset, observation window 11/27–12/01 (~979K users); "
        "\"next-2-day rate\" = bought during 12/02–12/03",
    ),
    "seg_note_suffix": (
        "；K-Means（K={k}），轮廓系数 {sil:.2f}，分群为描述工具",
        "; K-Means (K={k}), silhouette {sil:.2f}; segments are a descriptive tool",
    ),
}

# 特征名 (中文, English)
FEATURE_NAMES = {
    "pv_cnt": ("浏览次数", "Page views"),
    "fav_cnt": ("收藏次数", "Favorites"),
    "cart_cnt": ("加购次数", "Add-to-carts"),
    "buy_cnt": ("购买次数", "Purchases"),
    "active_days": ("活跃天数", "Active days"),
    "items_cnt": ("浏览商品数", "Distinct items viewed"),
    "cats_cnt": ("浏览类目数", "Distinct categories viewed"),
    "pv_last_day": ("最后一天浏览", "Views on last day"),
    "cart_last_day": ("最后一天加购", "Carts on last day"),
    "buy_last_day": ("最后一天购买", "Purchases on last day"),
    "days_since_active": ("距上次活跃天数", "Days since last activity"),
    "days_since_buy": ("距上次购买天数", "Days since last purchase"),
    "cart_pending": ("加购未买商品数", "Carted, not bought"),
    "fav_pending": ("收藏未买商品数", "Favorited, not bought"),
    "buy_pv_ratio": ("购买/浏览", "Purchases / views"),
    "cart_pv_ratio": ("加购/浏览", "Carts / views"),
    "fav_pv_ratio": ("收藏/浏览", "Favorites / views"),
}

# 分群画像 CSV 表头 (中文, English)，顺序固定
SEGMENT_CSV_COLUMNS = [
    ("分群", "Segment"),
    ("用户数", "Users"),
    ("占比", "Share"),
    ("浏览中位数", "Median page views"),
    ("收藏中位数", "Median favorites"),
    ("加购中位数", "Median add-to-carts"),
    ("购买中位数", "Median purchases"),
    ("活跃天数中位数", "Median active days"),
    ("浏览类目数中位数", "Median categories viewed"),
    ("观察窗内购买过占比", "Bought in observation window"),
    ("之后2天购买率", "Bought in following 2 days"),
]


def get(lang):
    if lang not in ("zh", "en"):
        raise ValueError("lang must be 'zh' or 'en'")
    i = 0 if lang == "zh" else 1
    out = {k: v[i] for k, v in _STR.items()}
    out["features"] = {k: v[i] for k, v in FEATURE_NAMES.items()}
    out["segment_columns"] = [c[i] for c in SEGMENT_CSV_COLUMNS]
    return out
