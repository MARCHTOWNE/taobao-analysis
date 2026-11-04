-- [EN] Time trends: by day, by hour, weekday vs weekend.
-- 时间趋势：按天、按小时、工作日 vs 周末
USE taobao;

-- 1) 按天
SELECT dt,
       SUM(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS pv,
       COUNT(DISTINCT user_id)                           AS uv,
       SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_cnt,
       COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN user_id END) AS buyers
FROM user_behavior
GROUP BY dt
ORDER BY dt;

-- 2) 按小时（9 天合计）
SELECT hr,
       SUM(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS pv,
       SUM(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS cart,
       SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_cnt,
       ROUND(SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END) * 100, 2) AS buy_per_pv_pct
FROM user_behavior
GROUP BY hr
ORDER BY hr;

-- 3) 周末（11/25-26、12/2-3）与工作日对比，用日均值避免天数不同
WITH d AS (
  SELECT dt,
         CASE WHEN dt IN ('2017-11-25','2017-11-26','2017-12-02','2017-12-03')
              THEN 'weekend' ELSE 'weekday' END AS day_type,
         SUM(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS pv,
         SUM(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS buy_cnt
  FROM user_behavior
  GROUP BY dt
)
SELECT day_type,
       COUNT(*)                 AS days,
       ROUND(AVG(pv), 0)        AS avg_daily_pv,
       ROUND(AVG(buy_cnt), 0)   AS avg_daily_buy,
       ROUND(SUM(buy_cnt) / SUM(pv) * 100, 2) AS buy_per_pv_pct
FROM d
GROUP BY day_type;
