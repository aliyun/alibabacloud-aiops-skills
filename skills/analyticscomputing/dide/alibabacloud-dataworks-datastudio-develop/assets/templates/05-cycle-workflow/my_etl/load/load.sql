-- Load: Write aggregated results to ADS layer
INSERT OVERWRITE TABLE ads_order_summary PARTITION (dt='${bizdate}')
SELECT
    user_id,
    COUNT(*) AS order_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM dwd_order
WHERE dt = '${bizdate}'
GROUP BY user_id;
