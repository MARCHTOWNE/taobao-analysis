-- [EN] Conversion funnel (defined by whether a behavior ever occurred for the user or user-item pair; order is not required).
-- 转化漏斗（口径：看用户或"用户-商品对"是否发生过该行为，不要求时间顺序）
USE taobao;

-- 1) 用户级漏斗：有浏览 -> 有收藏或加购 -> 有购买
WITH u AS (
  SELECT user_id,
         MAX(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END)                  AS has_pv,
         MAX(CASE WHEN behavior IN ('fav','cart') THEN 1 ELSE 0 END)       AS has_fc,
         MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END)                 AS has_buy
  FROM user_behavior
  GROUP BY user_id
)
SELECT SUM(has_pv)                                      AS users_pv,
       SUM(CASE WHEN has_pv = 1 AND has_fc = 1 THEN 1 ELSE 0 END)                   AS users_fav_or_cart,
       SUM(CASE WHEN has_pv = 1 AND has_fc = 1 AND has_buy = 1 THEN 1 ELSE 0 END)   AS users_buy_after_fc,
       SUM(CASE WHEN has_pv = 1 AND has_buy = 1 THEN 1 ELSE 0 END)                  AS users_buy_any
FROM u;

-- 2) 用户-商品对漏斗（更贴近"某人看了某商品后是否买了它"）
WITH p AS (
  SELECT user_id, item_id,
         MAX(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END)                  AS has_pv,
         MAX(CASE WHEN behavior IN ('fav','cart') THEN 1 ELSE 0 END)       AS has_fc,
         MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END)                 AS has_buy
  FROM user_behavior
  GROUP BY user_id, item_id
)
SELECT SUM(has_pv)                                                                   AS pairs_pv,
       SUM(CASE WHEN has_pv = 1 AND has_fc = 1 THEN 1 ELSE 0 END)                    AS pairs_fav_or_cart,
       SUM(CASE WHEN has_pv = 1 AND has_fc = 1 AND has_buy = 1 THEN 1 ELSE 0 END)    AS pairs_buy_after_fc,
       SUM(CASE WHEN has_pv = 1 AND has_fc = 0 AND has_buy = 1 THEN 1 ELSE 0 END)    AS pairs_direct_buy
FROM p;
