-- process_orders: Order data cleansing
INSERT OVERWRITE TABLE dwd_order PARTITION (dt='${bizdate}')
SELECT
    order_id,
    user_id,
    COALESCE(amount, 0) AS amount,
    order_time
FROM ods_raw_order
WHERE dt = '${bizdate}'
  AND order_id IS NOT NULL;
