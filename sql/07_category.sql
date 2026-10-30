-- 类目分析：热门类目、转化率、购买集中度
USE taobao;

-- 1) 浏览量前 20 的类目及转化率
WITH c AS (
  SELECT category_id,
         SUM(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS pv,
         SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_cnt
  FROM user_behavior
  GROUP BY category_id
)
SELECT category_id, pv, buy_cnt, ROUND(buy_cnt / pv * 100, 2) AS buy_per_pv_pct
FROM c
ORDER BY pv DESC
LIMIT 20;

-- 2) 购买集中度：前 10 / 前 100 个类目占全部购买的比例
WITH c AS (
  SELECT category_id, SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_cnt
  FROM user_behavior
  GROUP BY category_id
),
r AS (
  SELECT category_id, buy_cnt,
         SUM(buy_cnt) OVER ()                  AS total_buy,
         ROW_NUMBER() OVER (ORDER BY buy_cnt DESC) AS rn
  FROM c
)
SELECT COUNT(*) AS categories,
       ROUND(SUM(CASE WHEN rn <= 10  THEN buy_cnt ELSE 0 END) / MAX(total_buy) * 100, 2) AS top10_buy_share_pct,
       ROUND(SUM(CASE WHEN rn <= 100 THEN buy_cnt ELSE 0 END) / MAX(total_buy) * 100, 2) AS top100_buy_share_pct
FROM r;
