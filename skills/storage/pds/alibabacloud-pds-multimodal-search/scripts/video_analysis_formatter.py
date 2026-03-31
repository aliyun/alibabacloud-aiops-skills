#!/usr/bin/env python3
"""
PDS 音视频精读结果格式化脚本

功能:
- 下载并解析签名文件
- 格式化输出音视频分析结果
- 支持视频总结、对话转录、章节总结、PPT 详情等

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


def ms_to_timestamp(ms):
    """毫秒转时间戳格式"""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_video_analysis(result, output_file=None):
    """
    格式化音视频分析结果
    
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

    # 1. 视频总结
    if "summary" in result_data and result_data["summary"]:
        try:
            summary_data = download_and_parse(result_data["summary"][0])
            output.append("=" * 50)
            output.append("🎥 【视频总结】")
            output.append("=" * 50)
            output.append("")

            for item in summary_data:
                if "Text" in item:
                    output.append(item["Text"])
                    output.append("")
        except Exception as e:
            output.append(f"⚠️  获取视频总结失败：{e}")
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

    # 3. 对话转录
    if "transcript" in result_data and result_data["transcript"]:
        try:
            transcript_data = download_and_parse(result_data["transcript"][0])
            output.append("=" * 50)
            output.append("🎬 【对话转录】")
            output.append("=" * 50)
            output.append("")

            for item in transcript_data:
                start_time = ms_to_timestamp(item["TimeRange"][0])
                end_time = ms_to_timestamp(item["TimeRange"][1])
                speaker_id = item.get("SpeakerId", "unknown")
                # 提取发言人简短标识
                speaker_short = speaker_id.split("-")[-1][:8] if "-" in speaker_id else speaker_id[:8]
                
                output.append(f"[{start_time} - {end_time}] 发言人 {speaker_short}:")
                output.append(item.get("Content", ""))
                output.append("")
        except Exception as e:
            output.append(f"⚠️  获取对话转录失败：{e}")
            output.append("")

    # 4. 对话总结
    if "transcript_summaries" in result_data and result_data["transcript_summaries"]:
        try:
            transcript_summary_data = download_and_parse(result_data["transcript_summaries"][0])
            output.append("=" * 50)
            output.append("💬 【对话总结】")
            output.append("=" * 50)
            output.append("")

            for item in transcript_summary_data:
                text = item.get("Text", "")
                if text:
                    output.append(text)
                    output.append("")
        except Exception as e:
            output.append(f"⚠️  获取对话总结失败：{e}")
            output.append("")

    # 5. 章节总结 (含时间范围)
    if "chapter_summaries" in result_data and result_data["chapter_summaries"]:
        try:
            chapters_data = download_and_parse(result_data["chapter_summaries"][0])
            output.append("=" * 50)
            output.append("📚 【章节总结】")
            output.append("=" * 50)
            output.append("")

            for chapter in chapters_data:
                title = chapter.get('Title', '无标题')
                time_range = chapter.get('TimeRange', [0, 0])
                start_time = ms_to_timestamp(time_range[0])
                end_time = ms_to_timestamp(time_range[1])
                
                output.append(f"▶️ {title} [{start_time} - {end_time}]")
                output.append("-" * 40)

                for item in chapter.get("Summary", []):
                    text = item.get("Text")
                    if text:
                        output.append(f"  {text}")
                        output.append("")
                    
                    img = item.get("Image")
                    if img:
                        output.append(f"  🖼️ 图片：{img.get('ImagePath', '未知路径')}")
                        output.append("")

                output.append("")
        except Exception as e:
            output.append(f"⚠️  获取章节总结失败：{e}")
            output.append("")

    # 6. 对话章节总结
    if "transcript_chapter_summaries" in result_data and result_data["transcript_chapter_summaries"]:
        try:
            transcript_chapters_data = download_and_parse(result_data["transcript_chapter_summaries"][0])
            output.append("=" * 50)
            output.append("📖 【对话章节总结】")
            output.append("=" * 50)
            output.append("")

            for chapter in transcript_chapters_data:
                title = chapter.get('Title', '无标题')
                time_range = chapter.get('TimeRange', [0, 0])
                start_time = ms_to_timestamp(time_range[0])
                end_time = ms_to_timestamp(time_range[1])
                
                output.append(f"▶️ {title} [{start_time} - {end_time}]")
                output.append("-" * 40)

                for item in chapter.get("Summary", []):
                    text = item.get("Text")
                    if text:
                        output.append(f"  {text}")
                        output.append("")

                output.append("")
        except Exception as e:
            output.append(f"⚠️  获取对话章节总结失败：{e}")
            output.append("")

    # 7. PPT 详情
    if "ppt_details" in result_data and result_data["ppt_details"]:
        try:
            ppt_data = download_and_parse(result_data["ppt_details"][0])
            output.append("=" * 50)
            output.append("📊 【PPT 提取】")
            output.append("=" * 50)
            output.append("")

            for i, ppt in enumerate(ppt_data, 1):
                page_num = ppt.get("PPTShotIndex", i - 1) + 1
                start_time = ms_to_timestamp(ppt.get("StartTime", 0))
                image_path = ppt.get("ImagePath", "未知路径")
                
                output.append(f"第 {page_num} 页 (出现时间：{start_time})")
                output.append(f"图片路径：{image_path}")
                output.append("")
        except Exception as e:
            output.append(f"⚠️  获取 PPT 详情失败：{e}")
            output.append("")

    # 8. 问题导读
    if "questions" in result_data and result_data["questions"]:
        try:
            qa_data = download_and_parse(result_data["questions"][0])
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

    # 9. 图片列表 (如果有额外图片)
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
        description='PDS 音视频精读结果格式化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 格式化已有的 JSON 结果文件
  python video_analysis_formatter.py result.json
  python video_analysis_formatter.py result.json -o formatted_output.txt
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
        format_video_analysis(args.input_file, args.output)
        return 0
    except Exception as e:
        print(f"❌ 处理失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
