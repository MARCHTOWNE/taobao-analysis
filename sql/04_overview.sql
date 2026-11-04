-- [EN] Overview: row count, events per behavior type, number of buyers.
-- 整体指标：规模、各行为次数、购买用户数
USE taobao;

SELECT COUNT(*)                                   AS total_rows,
       COUNT(DISTINCT user_id)                    AS uv,
       COUNT(DISTINCT item_id)                    AS items,
       COUNT(DISTINCT category_id)                AS categories,
       SUM(CASE WHEN behavior = 'pv'   THEN 1 ELSE 0 END) AS pv,
       SUM(CASE WHEN behavior = 'fav'  THEN 1 ELSE 0 END) AS fav,
       SUM(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS cart,
       SUM(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS buy,
       COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN user_id END) AS buyers
FROM user_behavior;

-- 派生指标：人均浏览、购买用户占比、购买次数/浏览次数
WITH o AS (
  SELECT COUNT(DISTINCT user_id) AS uv,
         SUM(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS pv,
         SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy,
         COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN user_id END) AS buyers
  FROM user_behavior
)
SELECT ROUND(pv / uv, 2)           AS pv_per_user,
       ROUND(buyers / uv * 100, 2) AS buyer_rate_pct,
       ROUND(buy / pv * 100, 2)    AS buy_per_pv_pct,
       ROUND(buy / buyers, 2)      AS buy_per_buyer
FROM o;
