-- [EN] Purchase-count distribution, repeat rate, distribution of last purchase date (recency).
-- 购买次数分布、复购率、最后一次购买日期分布（反映用户近期活跃度 R）
USE taobao;

-- 1) 购买次数分布（5 次及以上合并）
WITH b AS (
  SELECT user_id, COUNT(*) AS buy_cnt
  FROM user_behavior
  WHERE behavior = 'buy'
  GROUP BY user_id
)
SELECT CASE WHEN buy_cnt >= 5 THEN '5+' ELSE CAST(buy_cnt AS CHAR) END AS buy_times,
       COUNT(*) AS users
FROM b
GROUP BY CASE WHEN buy_cnt >= 5 THEN '5+' ELSE CAST(buy_cnt AS CHAR) END
ORDER BY buy_times;

-- 2) 复购率：购买 2 次及以上的用户 / 购买用户
WITH b AS (
  SELECT user_id, COUNT(*) AS buy_cnt
  FROM user_behavior
  WHERE behavior = 'buy'
  GROUP BY user_id
)
SELECT COUNT(*) AS buyers,
       SUM(CASE WHEN buy_cnt >= 2 THEN 1 ELSE 0 END) AS repeat_buyers,
       ROUND(SUM(CASE WHEN buy_cnt >= 2 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS repeat_rate_pct
FROM b;

-- 3) 最后一次购买发生在哪天
WITH b AS (
  SELECT user_id, MAX(dt) AS last_buy
  FROM user_behavior
  WHERE behavior = 'buy'
  GROUP BY user_id
)
SELECT last_buy, COUNT(*) AS users
FROM b
GROUP BY last_buy
ORDER BY last_buy;
