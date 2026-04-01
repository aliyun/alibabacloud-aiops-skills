-- ODS order table
INSERT OVERWRITE TABLE ods_order PARTITION (dt='${bizdate}')
SELECT
    order_id,
    user_id,
    product_id,
    amount,
    order_time
FROM raw_order
WHERE dt = '${bizdate}';
