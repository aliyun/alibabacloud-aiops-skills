-- DWD order detail table
-- Runs after ods_order completes

INSERT OVERWRITE TABLE dwd_order_detail PARTITION (dt='${bizdate}')
SELECT
    o.order_id,
    o.user_id,
    u.user_name,
    o.product_id,
    p.product_name,
    o.amount,
    o.order_time
FROM ods_order o
LEFT JOIN dim_user u ON o.user_id = u.user_id
LEFT JOIN dim_product p ON o.product_id = p.product_id
WHERE o.dt = '${bizdate}';
