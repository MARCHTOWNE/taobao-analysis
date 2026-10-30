-- 导入抽样数据到原始表
-- 需要先开启：SET GLOBAL local_infile = 1;  并且客户端连接时加 --local-infile=1
USE taobao;
TRUNCATE TABLE user_behavior_raw;
LOAD DATA LOCAL INFILE 'D:/github/taobao-analysis/data/sample_5pct.csv'
INTO TABLE user_behavior_raw
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
(user_id, item_id, category_id, behavior, ts);

SELECT COUNT(*) AS raw_rows FROM user_behavior_raw;
