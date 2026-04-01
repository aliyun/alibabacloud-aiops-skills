-- DWD user info table
-- Processed from ODS layer daily at 2:00 AM

INSERT OVERWRITE TABLE dwd_user_info PARTITION (dt='${bizdate}')
SELECT
    user_id,
    user_name,
    age,
    gender,
    city,
    register_time,
    CURRENT_TIMESTAMP AS etl_time
FROM ods_user_info
WHERE dt = '${bizdate}';
