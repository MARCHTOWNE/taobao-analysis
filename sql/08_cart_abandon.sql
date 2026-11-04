-- [EN] Cart abandonment: share of carted items that were never bought.
-- 加购流失：加购了某商品但没有购买它的比例
USE taobao;

WITH p AS (
  SELECT user_id, item_id,
         MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS has_cart,
         MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS has_buy
  FROM user_behavior
  GROUP BY user_id, item_id
)
SELECT SUM(has_cart)                                                       AS cart_pairs,
       SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 END)       AS cart_then_buy,
       ROUND(SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 END)
             / SUM(has_cart) * 100, 2)                                     AS cart_conv_pct,
       ROUND(100 - SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 END)
             / SUM(has_cart) * 100, 2)                                     AS cart_abandon_pct
FROM p;
