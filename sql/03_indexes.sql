-- [EN] Build indexes after loading and cleaning (indexing before the load is much slower).
-- 清洗并导入完成后再建索引（导入前建索引会明显变慢）
USE taobao;
ALTER TABLE user_behavior
  ADD INDEX idx_user (user_id),
  ADD INDEX idx_dt_hr (dt, hr),
  ADD INDEX idx_category (category_id),
  ADD INDEX idx_behavior (behavior);
