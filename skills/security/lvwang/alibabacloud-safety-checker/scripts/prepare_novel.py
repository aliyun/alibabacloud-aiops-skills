#!/usr/bin/env python3
"""
小说/长文本预处理工具 - 将长文本按段落切分为审核样本
用法: python prepare_novel.py <小说文件路径> [--max-chars 1800] [--max-samples 100]
"""
import argparse
import json
import os
import re
import sys
from typing import List, Tuple


def split_novel_to_chunks(
    file_path: str,
    max_chars: int = 1800,
    max_samples: int = 0,
) -> List[Tuple[str, str, int]]:
    """
    将小说文件切分为审核样本
    返回: [(chunk_text, chapter_info, line_number), ...]
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chunks = []
    current_chapter = "未知章节"
    current_chunk = ""
    chunk_start_line = 1

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # 检测章节标题
        if re.match(r"^###第\d+章", line) or re.match(r"^第[一二三四五六七八九十百千\d]+章", line):
            # 保存当前chunk
            if current_chunk.strip():
                chunks.append((current_chunk.strip(), current_chapter, chunk_start_line))
            current_chapter = line.replace("###", "").strip()
            current_chunk = ""
            chunk_start_line = i
            continue

        # 累积内容
        if len(current_chunk) + len(line) + 1 > max_chars:
            # 当前chunk已满，保存并开始新chunk
            if current_chunk.strip():
                chunks.append((current_chunk.strip(), current_chapter, chunk_start_line))
            current_chunk = line
            chunk_start_line = i
        else:
            current_chunk += line + "\n"

    # 最后一个chunk
    if current_chunk.strip():
        chunks.append((current_chunk.strip(), current_chapter, chunk_start_line))

    # 限制样本数
    if max_samples > 0 and len(chunks) > max_samples:
        # 均匀采样
        step = len(chunks) / max_samples
        sampled = []
        for i in range(max_samples):
            idx = int(i * step)
            sampled.append(chunks[idx])
        chunks = sampled

    return chunks


def generate_samples_json(
    chunks: List[Tuple[str, str, int]],
    source_file: str,
    output_path: str,
):
    """生成框架可用的样本JSON文件"""
    source_name = os.path.splitext(os.path.basename(source_file))[0]

    samples = []
    for i, (text, chapter, line_no) in enumerate(chunks, 1):
        samples.append({
            "sample_id": f"novel_{i:04d}",
            "modality": "text",
            "content": text,
            "data_id": f"{source_name}_chunk_{i:04d}",
            "category": f"novel_{chapter}",
            "expected_risk_level": "",
            "expected_labels": [],
            "metadata": {
                "source_file": source_file,
                "chapter": chapter,
                "start_line": line_no,
                "char_count": len(text),
            },
        })

    output_data = {
        "source": source_file,
        "total_chunks": len(samples),
        "samples": samples,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    return len(samples)


def main():
    parser = argparse.ArgumentParser(description="小说/长文本预处理为审核样本")
    parser.add_argument("file", help="小说文件路径")
    parser.add_argument(
        "--max-chars", type=int, default=1800,
        help="每个样本最大字符数（默认1800，API限制2000）"
    )
    parser.add_argument(
        "--max-samples", type=int, default=0,
        help="最大样本数（0=全量，默认0）。设置后会均匀采样"
    )
    parser.add_argument(
        "--output", "-o", default="",
        help="输出文件路径（默认保存到assets/目录）"
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"错误：文件不存在 - {args.file}")
        sys.exit(1)

    # 切分
    print(f"正在处理: {args.file}")
    chunks = split_novel_to_chunks(
        args.file,
        max_chars=args.max_chars,
        max_samples=args.max_samples,
    )
    print(f"切分完成: {len(chunks)} 个文本片段")

    # 输出路径
    if not args.output:
        samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
        os.makedirs(samples_dir, exist_ok=True)
        source_name = os.path.splitext(os.path.basename(args.file))[0]
        # 简化文件名
        safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', source_name)[:50]
        args.output = os.path.join(samples_dir, f"{safe_name}.json")

    count = generate_samples_json(chunks, args.file, args.output)
    print(f"样本文件已生成: {args.output}")
    print(f"共 {count} 个样本，可执行:")
    print(f"  python main.py run --samples {args.output}")


if __name__ == "__main__":
    import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
