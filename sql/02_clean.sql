-- 清洗：剔除时间范围外的脏数据，并按北京时间(UTC+8)拆出 dt / hr
-- 1511539200 = 2017-11-25 00:00:00 +08:00
-- 1512316800 = 2017-12-04 00:00:00 +08:00（不含）
-- 不依赖 MySQL 服务器时区设置，直接用秒数偏移计算
USE taobao;
TRUNCATE TABLE user_behavior;
INSERT INTO user_behavior (user_id, item_id, category_id, behavior, ts, dt, hr)
SELECT user_id, item_id, category_id, behavior, ts,
       DATE(DATE_ADD('1970-01-01 00:00:00', INTERVAL ts + 28800 SECOND)),
       HOUR(DATE_ADD('1970-01-01 00:00:00', INTERVAL ts + 28800 SECOND))
FROM user_behavior_raw
WHERE ts >= 1511539200 AND ts < 1512316800;

SELECT (SELECT COUNT(*) FROM user_behavior_raw) AS raw_rows,
       (SELECT COUNT(*) FROM user_behavior)     AS clean_rows;
