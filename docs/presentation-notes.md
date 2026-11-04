**English** | [简体中文](presentation-notes.zh-CN.md)

# Presentation notes (about 3 minutes)

## One-sentence version

Using 100 million Taobao behavior records, I built a full pipeline from MySQL cleaning and analysis through PySpark feature engineering to purchase prediction and user segmentation, and used a rule baseline and diagnostic experiments to explain why the model's gain is small.

## Three-minute walkthrough

1. **Data and goal (20 s)**: 100M behavior logs over 9 days: who did what to which item and when, with no prices or user profiles. The goal is to answer business questions and predict whether a user will buy.
2. **SQL analysis (60 s)**: pick two or three findings, e.g. purchases peak at 10 am while views peak at 9 pm; many purchases happen without a favorite or cart step; active users jump on Dec 2-3. Each finding has a chart and a matching SQL file.
3. **Engineering trade-offs (30 s)**: MySQL handles a 5% sample, PySpark the full data; MySQL's default 128 MB buffer pool made queries take minutes, 8 GB brought them to seconds; SQL was cross-checked on DuckDB.
4. **Prediction and diagnosis (60 s)**: time-forward, user-disjoint evaluation against a rule baseline. Gradient boosting reaches PR-AUC 0.404 vs 0.375 for the baseline, a small gain. Diagnosis shows no leakage and no overfitting; the aggregated behavior features simply carry limited information, and the test window falls in a traffic surge.
5. **Segmentation and limits (10 s)**: 4 segments for description; the silhouette score is low, so they are a descriptive tool only.

## Likely questions

**Why both MySQL and PySpark?** MySQL covers SQL business analysis, the most common job skill; 100M rows are too slow in MySQL, so full-scale feature engineering goes to Spark. They match different data scales, not stack-padding.

**Why is the model gain so small?** The diagnosis: even same-period new users give AUC of only 0.63, so the features carry limited information; the test window has a higher overall purchase rate, which makes discrimination harder. Causality was not tested; I call it a data phenomenon and an inference.

**How did you avoid leakage?** Two layers: a time split (test labels come after train labels) and a hash-based user split (test users are not in training), verified by comparing against the "same users" control.

**What did you verify yourself?** SQL results match between MySQL and DuckDB; Spark features match an independent DuckDB recomputation per user on the 5% sample (not on the full data).

**What would you do with more time?** User-item level prediction (cart recall), daily-sequence and recent-hours features, LightGBM with hyperparameter search, and validation on a longer period.

## Things not to say

- Do not call the model "accurate" or "great"; say "a small improvement over the baseline".
- Do not present sample purchase or conversion rates as platform-wide levels.
- Do not say promotions caused the 12/02-12/03 rise; say "that period rose clearly".
