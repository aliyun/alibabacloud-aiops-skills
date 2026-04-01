-- Transform: Data cleansing and transformation
INSERT OVERWRITE TABLE dwd_order PARTITION (dt='${bizdate}')
SELECT
    order_id,
    user_id,
    COALESCE(amount, 0) AS amount,
    CASE WHEN status = 1 THEN 'completed' ELSE 'pending' END AS status,
    order_time
FROM ods_raw_order
WHERE dt = '${bizdate}'
  AND order_id IS NOT NULL;
