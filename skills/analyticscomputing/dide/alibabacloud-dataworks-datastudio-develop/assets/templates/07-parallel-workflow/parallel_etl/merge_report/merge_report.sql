-- merge_report: Merge order and user data to generate report
INSERT OVERWRITE TABLE ads_user_order_report PARTITION (dt='${bizdate}')
SELECT
    u.user_id,
    u.user_name,
    u.region,
    COUNT(o.order_id) AS order_count,
    SUM(o.amount) AS total_amount
FROM dwd_user u
LEFT JOIN dwd_order o
  ON u.user_id = o.user_id AND o.dt = '${bizdate}'
WHERE u.dt = '${bizdate}'
GROUP BY u.user_id, u.user_name, u.region;
