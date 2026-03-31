#!/usr/bin/env python3
"""
PDS 文档精读结果格式化脚本

功能:
- 下载并解析签名文件
- 格式化输出文档分析结果
- 支持全文总结、章节总结、关键词、问题导读等

注意：如需提交精读任务并轮询，请使用 pds_poll_processor.py
"""

import requests
import json
import argparse
from pathlib import Path


def download_and_parse(signed_url):
    """下载并解析签名文件"""
    response = requests.get(signed_url, timeout=30)
    response.raise_for_status()
    return response.json()


def format_document_analysis(result, output_file=None):
    """
    格式化文档分析结果
    
    参数:
        result: 精读 API 返回的完整结果 (dict 或 JSON 文件路径)
        output_file: 输出文件路径，如果为 None 则打印到控制台
    """
    # 1. 加载结果数据
    if isinstance(result, str):
        with open(result, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
    else:
        result_data = result

    output = []

    # 1. 全文总结
    if "summary" in result_data and result_data["summary"]:
        try:
            summary_data = download_and_parse(result_data["summary"][0])
            output.append("=" * 50)
            output.append("📄 【全文总结】")
            output.append("=" * 50)
            output.append("")

            for item in summary_data:
                if "Text" in item:
                    output.append(item["Text"])
                    output.append("")
                if "Image" in item:
                    img = item["Image"]
                    page_num = img.get('PageNumber', 0) + 1
                    output.append(f"🖼️ 图片：{img['ImagePath']} (第{page_num}页)")
                    output.append("")
        except Exception as e:
            output.append(f"⚠️  获取全文总结失败：{e}")
            output.append("")

    # 2. 关键词
    if "keywords" in result_data and result_data["keywords"]:
        try:
            keywords_data = download_and_parse(result_data["keywords"][0])
            output.append("=" * 50)
            output.append("🏷️ 【关键词】")
            output.append("=" * 50)
            keywords_str = " | ".join([f"#{kw}" for kw in keywords_data])
            output.append(keywords_str)
            output.append("")
        except Exception as e:
            output.append(f"⚠️  获取关键词失败：{e}")
            output.append("")

    # 3. 章节总结
    if "chapter_summaries" in result_data and result_data["chapter_summaries"]:
        try:
            chapters_data = download_and_parse(result_data["chapter_summaries"][0])
            output.append("=" * 50)
            output.append("📚 【章节总结】")
            output.append("=" * 50)
            output.append("")

            for chapter in chapters_data:
                title = chapter.get('Title', '无标题')
                output.append(f"▶️ {title}")
                output.append("-" * 40)

                for item in chapter.get("Summary", []):
                    # 兼容不同大小写的字段
                    text = item.get("Text") or item.get("text")
                    if text:
                        output.append(f"  {text}")
                        output.append("")
                    
                    img = item.get("Image") or item.get("image")
                    if img:
                        output.append(f"  🖼️ 图片：{img.get('ImagePath', '未知路径')}")
                        output.append("")

            output.append("")
        except Exception as e:
            output.append(f"⚠️  获取章节总结失败：{e}")
            output.append("")

    # 4. 问题导读
    if "guiding_questions" in result_data and result_data["guiding_questions"]:
        try:
            qa_data = download_and_parse(result_data["guiding_questions"][0])
            output.append("=" * 50)
            output.append("❓ 【问题导读】")
            output.append("=" * 50)
            output.append("")

            for i, qa in enumerate(qa_data, 1):
                output.append(f"Q{i}: {qa.get('Question', '无问题')}")
                output.append(f"A{i}: {qa.get('Answer', '无答案')}")
                output.append("")
        except Exception as e:
            output.append(f"⚠️  获取问题导读失败：{e}")
            output.append("")

    # 5. 论文专有字段 (可选)
    for field_name, field_label in [
        ("method_description", "方法介绍"),
        ("experiment_description", "实验介绍"),
        ("conclusion_description", "结论介绍")
    ]:
        if field_name in result_data and result_data[field_name]:
            try:
                desc_data = download_and_parse(result_data[field_name][0])
                output.append("=" * 50)
                output.append(f"📝 【{field_label}】")
                output.append("=" * 50)
                output.append("")

                description = desc_data.get("Description", [])
                for item in description:
                    text = item.get("text")
                    if text:
                        output.append(text)
                        output.append("")
                    
                    img = item.get("image")
                    if img:
                        output.append(f"🖼️ 图片：{img.get('ImagePath', '未知路径')}")
                        output.append("")
            except Exception as e:
                output.append(f"⚠️  获取{field_label}失败：{e}")
                output.append("")

    # 6. 图片列表 (如果有额外图片)
    if "images" in result_data and result_data["images"]:
        output.append("=" * 50)
        output.append("🖼️ 【图片列表】")
        output.append("=" * 50)
        output.append("")
        
        for img_path, img_info in result_data["images"].items():
            output.append(f"📎 {img_path}")
            if "url" in img_info:
                output.append(f"   URL: {img_info['url']}")
            if "thumbnail" in img_info:
                output.append(f"   缩略图：{img_info['thumbnail']}")
            output.append("")

    # 输出结果
    formatted_output = "\n".join(output)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        print(f"✅ 格式化结果已保存到：{output_file}")
    else:
        print(formatted_output)

    return formatted_output


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='PDS 文档精读结果格式化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 格式化已有的 JSON 结果文件
  python doc_analysis_formatter.py result.json
  python doc_analysis_formatter.py result.json -o formatted_output.txt
        """
    )
    
    parser.add_argument(
        'input_file',
        help='精读 API 返回的 JSON 结果文件路径'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='格式化输出文件路径 (默认输出到控制台)'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ 文件不存在：{args.input_file}")
        return 1
    
    try:
        format_document_analysis(args.input_file, args.output)
        return 0
    except Exception as e:
        print(f"❌ 处理失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
