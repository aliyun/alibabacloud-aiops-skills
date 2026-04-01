-- process_users: User data cleansing
INSERT OVERWRITE TABLE dwd_user PARTITION (dt='${bizdate}')
SELECT
    user_id,
    user_name,
    COALESCE(region, 'unknown') AS region,
    register_time
FROM ods_raw_user
WHERE dt = '${bizdate}'
  AND user_id IS NOT NULL;
