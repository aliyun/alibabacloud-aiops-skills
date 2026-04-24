#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态文档 OCR 识别工具。

批量上传文件夹内的文件或指定文件进行 OCR 识别，并行轮询获取所有文件的识别文本。

用法：
    # 方式1：上传文件夹内所有支持的文件
    python document_remote_ocr.py <文件夹路径>

    # 方式2：上传指定的多个文件
    python document_remote_ocr.py --files <文件1> <文件2> <文件3>

参数：
    <文件夹路径>         包含待识别文件的目录路径
    --files              指定要识别的文件列表（可多个）
    --upload-workers     最大并发上传线程数（默认 5）
    --poll-workers       最大并行轮询线程数（默认 10）
    --poll-interval      初始轮询间隔秒数（默认 3，使用指数退避策略）

输出：
    JSON 数组格式：[{"fileName": "xxx", "parsedText": "识别文本"}, ...]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加 scripts 目录到路径(以便导入 common 模块)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import request_openapi, require_user_id, read_config

# 支持的文件格式（根据接口文档）
SUPPORTED_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.jp2', '.webp', '.gif', '.bmp',
    '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.csv'
}

# 最大文件大小 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# 最大轮询时间 120 秒
MAX_POLL_TIME = 120


def upload_document(file_path: str, config: dict) -> Dict[str, Any]:
    """
    上传单个文档文件进行 OCR 识别。

    Args:
        file_path: 文件绝对路径
        config: 配置字典

    Returns:
        上传响应数据，包含 taskId 等信息
    """
    uri = "/openapi/v2/document/upload"
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小 {file_size / 1024 / 1024:.2f}MB 超过限制 10MB: {file_path.name}")

    print(f"[上传] 正在上传: {file_path.name} ({file_size / 1024:.1f}KB)", flush=True)

    # 使用 multipart/form-data 上传文件
    # 注意：签名时 sign_params 为空，不要设置 content_type（requests 会自动处理）
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/octet-stream')}
        resp = request_openapi(
            "POST",
            uri,
            sign_params=None,  # 文件上传时签名为空
            config=config,
            files=files,
        )

    result = resp.json()
    print(f"[上传] 响应: {json.dumps(result, ensure_ascii=False)}", flush=True)

    # 处理响应可能是字符串的情况
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            raise RuntimeError(f"上传响应解析失败: {result}")

    if not result.get("success"):
        error_msg = result.get("message", "未知错误")
        error_code = result.get("code", "UNKNOWN")
        raise RuntimeError(f"上传失败 [{error_code}]: {error_msg}")

    return result.get("data", {})


def upload_documents_batch(
    file_paths: List[str],
    config: dict,
    max_workers: int = 5
) -> Dict[str, Dict[str, Any]]:
    """
    并发批量上传文档文件。

    Args:
        file_paths: 文件路径列表
        config: 配置字典
        max_workers: 最大并发上传线程数

    Returns:
        {文件名: {taskId, filename, fileType, ...}} 映射
    """
    upload_results = {}

    print(f"\n[上传] 开始并发上传 {len(file_paths)} 个文件（最大 {max_workers} 线程）", flush=True)

    # 使用线程池并发上传
    with ThreadPoolExecutor(max_workers=min(max_workers, len(file_paths))) as executor:
        # 提交所有上传任务
        future_to_filepath = {
            executor.submit(upload_document, file_path, config): file_path
            for file_path in file_paths
        }

        # 收集结果
        for future in as_completed(future_to_filepath):
            file_path = future_to_filepath[future]
            file_name = Path(file_path).name

            try:
                data = future.result()
                upload_results[file_name] = data
                print(f"[上传] ✓ {file_name} -> taskId: {data.get('taskId')}", flush=True)
            except Exception as e:
                print(f"[上传] ✗ {file_name} 失败: {e}", flush=True)
                upload_results[file_name] = {
                    "taskId": None,
                    "filename": file_name,
                    "status": "upload_failed",
                    "errorMessage": str(e)
                }

    return upload_results


def poll_task_status(task_id: str, config: dict, poll_interval: float = 3.0) -> Dict[str, Any]:
    """
    轮询单个 OCR 任务状态，直到完成或超时。
    使用指数退避策略优化轮询效率。

    Args:
        task_id: 任务 ID
        config: 配置字典
        poll_interval: 初始轮询间隔（秒）

    Returns:
        最终任务状态数据
    """
    uri = "/openapi/v2/document/task"
    start_time = time.time()

    # 指数退避参数
    current_interval = poll_interval
    min_interval = poll_interval
    max_interval = 10.0  # 最大轮询间隔 10 秒
    backoff_factor = 1.5  # 退避因子

    print(f"[轮询] 开始轮询 taskId: {task_id}", flush=True)

    while True:
        elapsed = time.time() - start_time

        # 检查超时
        if elapsed > MAX_POLL_TIME:
            print(f"[轮询] ⚠ 任务 {task_id} 超时 ({elapsed:.1f}s > {MAX_POLL_TIME}s)", flush=True)
            return {
                "taskId": task_id,
                "status": "timeout",
                "statusDesc": "处理超时",
                "completed": True,
                "parsedText": None,
                "errorMessage": f"任务处理超时 ({elapsed:.1f}s)"
            }

        # 查询任务状态
        params = {"taskId": task_id}
        try:
            resp = request_openapi("GET", uri, params=params, config=config)
            result = resp.json()

            if not result.get("success"):
                error_msg = result.get("message", "查询失败")
                print(f"[轮询] ✗ 查询失败: {error_msg}", flush=True)
                return {
                    "taskId": task_id,
                    "status": "query_failed",
                    "completed": True,
                    "parsedText": None,
                    "errorMessage": error_msg
                }

            data = result.get("data", {})
            status = data.get("status", "unknown")
            completed = data.get("completed", False)

            print(f"[轮询] 任务 {task_id[:20]}... 状态: {status} ({data.get('statusDesc', '')}) - 已耗时 {elapsed:.1f}s", flush=True)

            # 任务完成
            if completed:
                if status == "success":
                    print(f"[轮询] ✓ 任务 {task_id[:20]}... 解析成功", flush=True)
                elif status == "failed":
                    print(f"[轮询] ✗ 任务 {task_id[:20]}... 解析失败: {data.get('errorMessage', '')}", flush=True)
                elif status == "not_supported":
                    print(f"[轮询] ⚠ 任务 {task_id[:20]}... 不支持的文件类型", flush=True)

                return data

            # 指数退避：如果任务仍在处理中，逐渐增加轮询间隔
            # 处理初期可能较快，后期OCR识别通常较慢
            if status in ("processing", "pending"):
                new_interval = min(current_interval * backoff_factor, max_interval)
                if new_interval != current_interval:
                    current_interval = new_interval
            else:
                # 未知状态使用固定间隔
                current_interval = min_interval

            # 等待下一次轮询
            time.sleep(current_interval)

        except Exception as e:
            print(f"[轮询] ✗ 查询异常: {e}", flush=True)
            # 检查是否是试用到期
            error_str = str(e)
            from config_loader import check_trial_expired
            if check_trial_expired(error_str):
                raise

            # 其他异常，使用较短间隔重试
            time.sleep(min_interval)


def poll_tasks_parallel(
    tasks: Dict[str, Dict[str, Any]],
    config: dict,
    max_workers: int = 10,
    poll_interval: float = 3.0
) -> List[Dict[str, Any]]:
    """
    并行轮询多个 OCR 任务。

    Args:
        tasks: {文件名: {taskId, ...}} 映射
        config: 配置字典
        max_workers: 最大并行线程数
        poll_interval: 轮询间隔（秒）

    Returns:
        [{"fileName": "xxx", "parsedText": "文本"}, ...] 列表
    """
    # 过滤出有效 taskId
    valid_tasks = {
        name: data for name, data in tasks.items()
        if data.get("taskId")
    }

    if not valid_tasks:
        print("[轮询] 没有有效的任务需要轮询", flush=True)
        return []

    print(f"\n[轮询] 开始并行轮询 {len(valid_tasks)} 个任务（最大 {max_workers} 线程）", flush=True)

    results = []

    # 使用线程池并行轮询
    with ThreadPoolExecutor(max_workers=min(max_workers, len(valid_tasks))) as executor:
        # 提交所有任务
        future_to_filename = {
            executor.submit(poll_task_status, data["taskId"], config, poll_interval): filename
            for filename, data in valid_tasks.items()
        }

        # 收集结果
        for future in as_completed(future_to_filename):
            filename = future_to_filename[future]
            try:
                task_data = future.result()

                # 组装结果（使用 file 字段）
                result_item = {
                    "file": filename,
                    "parsedText": task_data.get("parsedText")
                }
                results.append(result_item)

                # 输出状态
                status = task_data.get("status", "unknown")
                if status == "success":
                    text_len = len(task_data.get("parsedText", "") or "")
                    print(f"[结果] ✓ {filename}: 识别成功 ({text_len} 字符)", flush=True)
                else:
                    error_msg = task_data.get("errorMessage", "未知错误")
                    print(f"[结果] ✗ {filename}: {status} - {error_msg}", flush=True)
                    result_item["parsedText"] = None  # 确保失败时为 None
                    result_item["error"] = error_msg

            except Exception as e:
                print(f"[结果] ✗ {filename} 轮询异常: {e}", flush=True)
                results.append({
                    "fileName": filename,
                    "parsedText": None,
                    "error": str(e)
                })

    return results


def collect_files_from_directory(directory: str) -> List[str]:
    """
    从目录中收集所有支持的文件（递归扫描子目录）。

    Args:
        directory: 目录路径

    Returns:
        文件绝对路径列表
    """
    dir_path = Path(directory).resolve()

    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"路径不是目录: {directory}")

    files = []
    for file_path in dir_path.rglob('*'):  # 递归扫描
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                # 检查文件大小
                try:
                    file_size = file_path.stat().st_size
                    if file_size <= MAX_FILE_SIZE:
                        files.append(str(file_path))
                    else:
                        print(f"[扫描] ⚠ 跳过超大文件: {file_path.name} ({file_size / 1024 / 1024:.2f}MB > 10MB)", flush=True)
                except Exception as e:
                    print(f"[扫描] ⚠ 无法访问文件: {file_path.name} - {e}", flush=True)

    return sorted(files)


def validate_and_collect_files(
    directory: Optional[str] = None,
    files: Optional[List[str]] = None
) -> List[str]:
    """
    验证并收集待识别的文件列表。

    Args:
        directory: 目录路径（与 files 二选一）
        files: 文件路径列表（与 directory 二选一）

    Returns:
        文件绝对路径列表

    Raises:
        ValueError: 参数不正确
    """
    if directory and files:
        raise ValueError("不能同时指定目录和文件列表，请选择其中一种方式")

    if not directory and not files:
        raise ValueError("必须指定目录或文件列表")

    if directory:
        # 从目录收集文件
        return collect_files_from_directory(directory)

    # 验证指定的文件
    valid_files = []
    for file_path_str in files:
        file_path = Path(file_path_str).resolve()

        if not file_path.exists():
            print(f"[验证] ✗ 文件不存在: {file_path}", flush=True)
            continue

        if not file_path.is_file():
            print(f"[验证] ✗ 路径不是文件: {file_path}", flush=True)
            continue

        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            print(f"[验证] ✗ 不支持的文件格式: {file_path.name} ({ext})", flush=True)
            continue

        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            print(f"[验证] ✗ 文件过大: {file_path.name} ({file_size / 1024 / 1024:.2f}MB > 10MB)", flush=True)
            continue

        valid_files.append(str(file_path))

    return sorted(valid_files)


def main():
    """主函数：批量 OCR 识别文件夹内的所有文件或指定文件。"""
    parser = argparse.ArgumentParser(
        description="批量上传文件夹内的文件或指定文件进行 OCR 识别，并行获取识别文本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 方式1：扫描文件夹内所有支持的文件
  python document_remote_ocr.py /path/to/folder

  # 方式2：上传指定的多个文件
  python document_remote_ocr.py --files file1.pdf file2.png file3.docx
        """
    )
    parser.add_argument(
        "directory",
        nargs='?',
        default=None,
        help="包含待识别文件的目录路径（与 --files 二选一）"
    )
    parser.add_argument(
        "--files",
        nargs='+',
        default=None,
        metavar='FILE',
        help="指定要识别的文件列表（可多个，与 directory 二选一）"
    )
    parser.add_argument(
        "--upload-workers",
        type=int,
        default=5,
        help="最大并发上传线程数（默认 5，最大 10）"
    )
    parser.add_argument(
        "--poll-workers",
        type=int,
        default=10,
        help="最大并行轮询线程数（默认 10，最大 10）"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="初始轮询间隔秒数（默认 3，使用指数退避策略）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出 JSON 文件路径（默认输出到脚本同级 output/ocr_result.json）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="仅输出 JSON 结果（不打印日志，适合脚本调用）"
    )
    parser.add_argument(
        "--workspace-dir",
        default=None,
        help="用户工作目录路径"
    )

    args = parser.parse_args()

    verbose = not args.json

    # 设置工作目录（必须在 read_config 之前）
    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    # 加载配置
    if verbose:
        print("=" * 60, flush=True)
        print("QuickBI 多模态文档 OCR 识别工具", flush=True)
        print("=" * 60, flush=True)

    config = read_config()

    # 确保 user_id 已配置
    try:
        require_user_id(config)
    except Exception as e:
        if verbose:
            print(f"\n[错误] 用户配置失败: {e}", flush=True)
        sys.exit(1)

    # 收集文件
    try:
        files = validate_and_collect_files(
            directory=args.directory,
            files=args.files
        )
    except Exception as e:
        if verbose:
            print(f"\n[错误] {e}", flush=True)
            parser.print_usage()
        sys.exit(1)

    if not files:
        if verbose:
            if args.directory:
                print(f"\n[警告] 目录 {args.directory} 中没有找到支持的文件", flush=True)
            else:
                print(f"\n[警告] 没有找到有效的文件", flush=True)
            print(f"支持的文件格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}", flush=True)
        sys.exit(0)

    if verbose:
        print(f"\n[扫描] 找到 {len(files)} 个待识别文件:", flush=True)
        for f in files:
            size = Path(f).stat().st_size
            print(f"  - {Path(f).name} ({size / 1024:.1f}KB)", flush=True)
        print(flush=True)

    # 限制最大并发数为 10
    max_upload_workers = min(args.upload_workers, 10)
    max_poll_workers = min(args.poll_workers, 10)

    # Step 1: 批量上传
    if verbose:
        print("=" * 60, flush=True)
        print("Step 1: 并发上传文件", flush=True)
        print("=" * 60, flush=True)

    upload_results = upload_documents_batch(
        files,
        config,
        max_workers=max_upload_workers
    )

    # Step 2: 并行轮询
    if verbose:
        print("\n" + "=" * 60, flush=True)
        print("Step 2: 并行轮询获取识别结果（指数退避策略）", flush=True)
        print("=" * 60, flush=True)

    results = poll_tasks_parallel(
        upload_results,
        config,
        max_workers=max_poll_workers,
        poll_interval=args.poll_interval
    )

    # 输出最终 JSON 结果
    output_json = json.dumps(results, ensure_ascii=False, indent=2)

    # 确定输出路径（默认 output/ocr_result_{timestamp}.json）
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        # 默认输出到脚本同级的 output 文件夹，带时间戳
        script_dir = Path(__file__).resolve().parent.parent
        output_dir = script_dir / "output"
        timestamp = int(time.time())
        output_path = output_dir / f"ocr_result_{timestamp}.json"

    # 保存到文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_json, encoding='utf-8')
    if verbose:
        print(f"\n[保存] ✓ JSON 结果已保存到: {output_path}", flush=True)

    # 输出到 stdout（JSON 模式）
    if args.json:
        print(output_json, flush=True)
    elif verbose:
        print("\n" + "=" * 60, flush=True)
        print("最终结果（JSON 格式）", flush=True)
        print("=" * 60, flush=True)
        print(output_json, flush=True)

        # 统计信息
        success_count = sum(1 for r in results if r.get("parsedText") is not None)
        fail_count = len(results) - success_count

        print("\n" + "=" * 60, flush=True)
        print(f"统计: 总计 {len(results)} | 成功 {success_count} | 失败 {fail_count}", flush=True)
        print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
