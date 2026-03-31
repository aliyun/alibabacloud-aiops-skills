#!/usr/bin/env python3
"""
PDS 文档/视频精读分析轮询处理器

用于自动轮询 PDS 精读分析任务，直到处理完成并下载所有结果。
支持文档分析 (doc/analysis) 和视频分析 (video/analysis)。
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class PDSPollProcessor:
    """PDS 精读分析轮询处理器"""
    
    def __init__(self, drive_id, file_id, revision_id, x_pds_process="doc/analysis", 
                 max_attempts=30, output_dir="/tmp"):
        """
        初始化处理器
        
        Args:
            drive_id: 空间 ID
            file_id: 文件 ID
            revision_id: 文件版本 ID
            x_pds_process: 处理类型，doc/analysis 或 video/analysis
            max_attempts: 最大轮询次数
            output_dir: 输出目录
        """
        self.drive_id = drive_id
        self.file_id = file_id
        self.revision_id = revision_id
        self.process_type = x_pds_process
        self.max_attempts = max_attempts
        self.output_dir = Path(output_dir)
        self.result = None
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def poll_analysis(self):
        """
        轮询精读分析结果
        
        Returns:
            dict: 分析结果，如果失败则返回 None
        """
        print("=" * 60)
        print(f"开始轮询 {self.process_type} 分析任务")
        print("=" * 60)
        print(f"Drive ID: {self.drive_id}")
        print(f"File ID: {self.file_id}")
        print(f"Revision ID: {self.revision_id}")
        print(f"Process Type: {self.process_type}")
        print(f"Max Attempts: {self.max_attempts}")
        print()
        
        # 使用列表形式构建命令，避免命令注入风险
        cmd = [
            "aliyun",
            "pds",
            "process",
            "--resource-type", "file",
            "--drive-id", str(self.drive_id),
            "--file-id", str(self.file_id),
            "--revision-id", str(self.revision_id),
            "--x-pds-process", str(self.process_type),
            "--user-agent", "AlibabaCloud-Agent-Skills"
        ]
        
        attempt = 0
        while attempt < self.max_attempts:
            attempt += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] ⏳ 第 {attempt}/{self.max_attempts} 次请求...")
            
            proc_result = subprocess.run(
                cmd, 
                shell=False,
                capture_output=True, 
                text=True,
                timeout=10,
            )
            
            # 1. 先判断是否有错误：returncode != 0 表示 CLI 命令失败（HTTP 非 2xx）
            if proc_result.returncode != 0:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] ❌ 请求失败")
                print(f"     错误信息：{proc_result.stderr.strip()}")
                print()
                print("=" * 60)
                print("❌ 遇到错误，停止轮询")
                print("=" * 60)
                return None
            
            # 2. 解析成功响应的 Body
            try:
                response = json.loads(proc_result.stdout)
                
                # 3. 判断是否需要继续轮询（存在 retry_time 字段表示处理中）
                if 'retry_time' in response:
                    retry_time = response.get('retry_time', 5)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"  [{timestamp}] ⏰ 处理中，等待 {retry_time} 秒后重试...")
                    time.sleep(retry_time)
                    continue
                
                # 4. 无错误且无 retry_time，视为分析完成
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] ✅ 分析完成!")
                self.result = response
                return response
                
            except json.JSONDecodeError as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] ❌ JSON 解析失败：{e}")
                print(f"  原始输出：{proc_result.stdout[:200]}")
                print()
                print("=" * 60)
                print("❌ 遇到错误，停止轮询")
                print("=" * 60)
                return None
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] ❌ 发生错误：{e}")
                print()
                print("=" * 60)
                print("❌ 遇到错误，停止轮询")
                print("=" * 60)
                return None
        
        # 超过最大尝试次数
        print()
        print("=" * 60)
        print("❌ 超过最大尝试次数，分析可能仍在进行中")
        print("=" * 60)
        return None
    
    def save_raw_result(self, filename=None):
        """
        保存原始 JSON 结果 (仅包含签名 URL，不下载内容)
        
        Args:
            filename: 文件名，默认自动生成
            
        Returns:
            str: 保存的文件路径
        """
        if self.result is None:
            print("❌ 没有结果可保存")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "doc" if self.process_type == "doc/analysis" else "video"
            filename = f"{prefix}_analysis_{timestamp}.json"
        
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.result, f, ensure_ascii=False, indent=2)
        
        print(f"💾 原始结果已保存到：{filepath}")
        return str(filepath)
    



def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PDS 文档/视频精读分析轮询处理器')
    parser.add_argument('--drive-id', required=True, help='空间 ID')
    parser.add_argument('--file-id', required=True, help='文件 ID')
    parser.add_argument('--revision-id', required=True, help='文件版本 ID')
    parser.add_argument('--x-pds-process', required=True,
                       choices=['doc/analysis', 'video/analysis'],
                       help='处理类型：doc/analysis（文档）或 video/analysis（音视频）')
    parser.add_argument('--max-attempts', type=int, default=30, help='最大轮询次数')
    parser.add_argument('--output-dir', default='/tmp', help='输出目录')
    parser.add_argument('-o', '--output', help='结果保存文件名，保存到 --output-dir 指定目录（默认 /tmp）')
    
    args = parser.parse_args()
    
    # 创建处理器
    processor = PDSPollProcessor(
        drive_id=args.drive_id,
        file_id=args.file_id,
        revision_id=args.revision_id,
        x_pds_process=args.x_pds_process,
        max_attempts=args.max_attempts,
        output_dir=args.output_dir
    )
    
    # 轮询分析
    result = processor.poll_analysis()
    
    if result:
        # 保存原始结果 (包含签名 URL)
        processor.save_raw_result(args.output)
    else:
        print("\n❌ 分析任务失败或被中断")
        sys.exit(1)


if __name__ == "__main__":
    main()
