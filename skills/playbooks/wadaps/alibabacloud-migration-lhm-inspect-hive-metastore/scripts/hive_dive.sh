#!/bin/bash

# ==============================================================================
# Hive 数据表深度探查脚本 (批量版)
# 功能:
# 1. 支持探查一个、多个或所有数据库。
# 2. 查询指定数据库下所有表的元数据（库、表、Location）。
# 3. 计算每个表在 HDFS、OSS 或其他兼容文件系统上的存储大小。
# 4. 导出每个表的建表语句 (DDL) 到单独的文件。
# ==============================================================================

# 如果任何未被捕获的命令失败，则立即退出脚本。
# 我们通过 `if` 语句来捕获预期的失败，以防止脚本意外退出。
set -e
# set -x # 如果需要进行详细的命令执行跟踪，请取消此行的注释

echo "====== Hive 数据表深度探查开始 ======"

# --- (1) 数据库连接信息 ---
# 请根据你的环境修改这些值
MYSQL_HOST="localhost"
MYSQL_USER="root"
MYSQL_PASSWORD="***"
MYSQL_DATABASE="hive" # Hive元数据库的名称

# --- 函数: 将字节转换成可读格式 ---
format_bytes() {
    local bytes=$1
    if ! [[ "$bytes" =~ ^[0-9]+$ ]]; then
        echo "N/A"
        return
    fi
    if [ "$bytes" -eq 0 ]; then
        echo "0 B"
        return
    fi
    echo "$bytes" | awk '{
        bytes = $1;
        if (bytes < 1024) { printf "%.0f B", bytes }
        else if (bytes < 1024^2) { printf "%.2f KB", bytes/1024 }
        else if (bytes < 1024^3) { printf "%.2f MB", bytes/1024^2 }
        else if (bytes < 1024^4) { printf "%.2f GB", bytes/1024^3 }
        else { printf "%.2f TB", bytes/1024^4 }
    }'
}

TODAY=$(date +%Y%m%d)

# --- (2) 动态处理输入参数 ---
TARGET_DBS=("$@")
WHERE_CLAUSE=""

if [ ${#TARGET_DBS[@]} -eq 0 ]; then
    echo "未指定数据库，将探查所有 Hive 数据库..."
    OUTPUT_DIR_SUFFIX="all_dbs"
else
    echo "目标数据库: ${TARGET_DBS[@]}"
    db_list_for_sql=""
    for db_name in "${TARGET_DBS[@]}"; do
        db_list_for_sql+="'${db_name}',"
    done
    db_list_for_sql=${db_list_for_sql%,}
    WHERE_CLAUSE="AND db.NAME IN (${db_list_for_sql})"
    OUTPUT_DIR_SUFFIX="batch"
fi

# --- (3) 定义输出路径 ---
OUTPUT_DIR="hive_explore_${OUTPUT_DIR_SUFFIX}_${TODAY}"
OUTPUT_CSV="${OUTPUT_DIR}/summary_report.csv"
DDL_SUBDIR="${OUTPUT_DIR}/ddl_files"
ERROR_LOG="${OUTPUT_DIR}/error.log"

mkdir -p "$DDL_SUBDIR"
> "$ERROR_LOG" # 每次运行时清空旧的错误日志
echo "所有输出文件将保存在目录: $OUTPUT_DIR"
echo "任何异常的标准错误输出都将记录在: $ERROR_LOG"

# --- (4) 初始化 CSV 文件头 ---
echo "db_name,tbl_name,tbl_location,total_size_bytes,total_size_human,ddl_file_path" > "$OUTPUT_CSV"

# --- (5) Metastore 查询 SQL ---
SQL_GET_TABLES="
SELECT 
    db.NAME, 
    tbl.TBL_NAME, 
    sds.LOCATION
FROM TBLS tbl
JOIN DBS db ON tbl.DB_ID = db.DB_ID
JOIN SDS sds ON tbl.SD_ID = sds.SD_ID
WHERE (tbl.TBL_TYPE = 'MANAGED_TABLE' OR tbl.TBL_TYPE = 'EXTERNAL_TABLE')
${WHERE_CLAUSE} 
ORDER BY db.NAME, tbl.TBL_NAME;
"

echo "正在从 Metastore 查询表列表..."

# --- (6) 主循环，逐行处理查询结果 ---
mysql -h "${MYSQL_HOST}" -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -B -e "${SQL_GET_TABLES}" \
| while IFS=$'\t' read -r db_name tbl_name tbl_location; do
    [ -z "$db_name" ] && continue

    echo "-------------------------------------------"
    echo "正在处理: ${db_name}.${tbl_name}"

    # --- 任务1: 获取表 Location 大小 ---
    total_size_bytes="N/A"
    human_readable_size="N/A"

    if [[ -n "$tbl_location" && "$tbl_location" != "null" ]]; then
        echo "  -> 查询存储位置大小: $tbl_location"
        
        # 使用 if 语句安全地执行命令，同时使用 `2>>` 将所有标准错误输出追加到日志文件
        if size_output=$(hadoop fs -du -s "$tbl_location" 2>>"$ERROR_LOG"); then
            total_size_bytes=$(echo "$size_output" | awk '{print $1}')
            if [[ -n "$total_size_bytes" ]]; then
                human_readable_size=$(format_bytes "$total_size_bytes")
                echo "  -> 大小: ${human_readable_size} (${total_size_bytes} Bytes)"
            else
                echo "  -> 警告: 'hadoop fs -du' 命令成功但未返回大小信息。"
                echo "WARNING: 'hadoop fs -du -s ${tbl_location}' succeeded but returned empty output." >> "$ERROR_LOG"
            fi
        else
            echo "  -> 警告: 无法获取位置大小。详细错误已记录到 $ERROR_LOG"
            # 此时，hadoop 命令本身的错误信息已经被 `2>>"$ERROR_LOG"` 捕获了
        fi
    else
        echo "  -> 警告: 表 Location 为空或无效，可能是视图或元数据异常。"
        echo "WARNING: Location for table ${db_name}.${tbl_name} is null or empty." >> "$ERROR_LOG"
    fi

    # --- 任务2: 获取 DDL ---
    ddl_file_path="${DDL_SUBDIR}/${db_name}.${tbl_name}.sql"
    echo "  -> 导出 DDL 到: $ddl_file_path"
    
    # 使用 `if !` 结构来捕获 hive 命令的失败，同时使用 `2>>` 记录所有标准错误
    if ! hive --hiveconf hive.exec.pre.hooks="" \
             --hiveconf hive.exec.post.hooks="" \
             --hiveconf hive.exec.failure.hooks="" \
             -e "SHOW CREATE TABLE \`${db_name}\`.\`${tbl_name}\`;" < /dev/null > "$ddl_file_path" 2>>"$ERROR_LOG"; then
        echo "  -> 错误: 获取 DDL 失败。详细错误已记录到 $ERROR_LOG"
        # 即使命令失败，也要确保 DDL 文件被创建，并包含错误信息
        # 这样可以防止 CSV 文件中的 ddl_file_path 指向一个不存在的文件
        # 详细的 hive 错误已经被 `2>>"$ERROR_LOG"` 捕获
        echo "-- FAILED TO GET DDL for ${db_name}.${tbl_name}" > "$ddl_file_path"
    fi
    
    # --- 任务3: 将结果写入 CSV 报告 ---
    echo "${db_name},${tbl_name},\"${tbl_location}\",${total_size_bytes},${human_readable_size},${ddl_file_path}" >> "$OUTPUT_CSV"
done

echo "==========================================="
echo "所有表处理完毕！"
echo "汇总报告请查看: $OUTPUT_CSV"
echo "所有建表语句 DDL 文件位于: $DDL_SUBDIR"
echo "处理过程中遇到的任何异常，请查看日志文件: $ERROR_LOG"
echo "====== 探查结束 ======"

exit 0
