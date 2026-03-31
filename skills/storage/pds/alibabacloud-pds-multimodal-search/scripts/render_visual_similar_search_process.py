import argparse
import base64
from typing import Optional


def url_safe_base64_encode(text):
    """将文本编码为 URL 安全的 base64 格式"""
    if not text:
        raise ValueError("输入文本不能为空")

    encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    url_safe = encoded.replace('+', '-').replace('/', '_').rstrip('=')
    return url_safe

def generate_x_pds_process_for_vss(source_domain_id: str, source_drive_id: str, source_file_id: str,
                                   source_revision_id: str, query: Optional[str] = None,
                                   limit: Optional[int] = None) -> str:
    """生成以图搜图的请求参数 x-pds-process"""
    if not source_drive_id or not source_file_id or not source_revision_id:
        raise ValueError("输入参数不能为空")

    pds_uri = f"pds://domains/{source_domain_id}/drives/{source_drive_id}/files/{source_file_id}/revisions/{source_revision_id}"
    x_pds_process = f"vision/similar-search,s_{url_safe_base64_encode(pds_uri)}"
    if query:
        real_query = "semantic_text = \"{query}\""
        x_pds_process += f",q_{url_safe_base64_encode(real_query)}"
    if limit:
        x_pds_process += f",l_{limit}"
    x_pds_process += ",/c,v_aW1hZ2U"
    return x_pds_process

def main():
    parser = argparse.ArgumentParser(description='生成以图搜图的请求参数 x-pds-process')
    parser.add_argument('--source_domain_id', required=True, help='要搜索的图片的 domain_id')
    parser.add_argument('--source_file_id', required=True, help='要搜索的图片的 file_id')
    parser.add_argument('--source_drive_id', required=True, help='要搜索的图片的 drive_id')
    parser.add_argument('--source_revision_id', required=True, help='要搜索的图片的 revision_id')
    parser.add_argument('--query', required=False, help='要搜索的语义文本')
    parser.add_argument('--limit', required=False, default=100, help='返回相似图片的最大数量')
    args = parser.parse_args()

    x_pds_process = generate_x_pds_process_for_vss(args.source_domain_id, args.source_drive_id, args.source_file_id, args.source_revision_id, args.query, args.limit)
    print(x_pds_process)

if __name__ == '__main__':
    main()