-- [EN] Taobao user-behavior analysis: create database and tables.
-- 淘宝用户行为分析：建库建表
-- 运行方式：mysql -u root -p < sql/00_schema.sql
CREATE DATABASE IF NOT EXISTS taobao DEFAULT CHARACTER SET utf8mb4;
USE taobao;

-- 原始表：与 CSV 一一对应（CSV 无表头）
DROP TABLE IF EXISTS user_behavior_raw;
CREATE TABLE user_behavior_raw (
  user_id     INT UNSIGNED NOT NULL,
  item_id     INT UNSIGNED NOT NULL,
  category_id INT UNSIGNED NOT NULL,
  behavior    VARCHAR(4)   NOT NULL,   -- pv浏览 / fav收藏 / cart加购 / buy购买
  ts          BIGINT       NOT NULL    -- Unix 时间戳（秒），部分为脏数据
) ENGINE=InnoDB;

-- 清洗表：只保留 2017-11-25 ~ 2017-12-03（北京时间），并拆出日期和小时
DROP TABLE IF EXISTS user_behavior;
CREATE TABLE user_behavior (
  user_id     INT UNSIGNED NOT NULL,
  item_id     INT UNSIGNED NOT NULL,
  category_id INT UNSIGNED NOT NULL,
  behavior    ENUM('pv','fav','cart','buy') NOT NULL,
  ts          BIGINT       NOT NULL,
  dt          DATE         NOT NULL,
  hr          TINYINT UNSIGNED NOT NULL
) ENGINE=InnoDB;
