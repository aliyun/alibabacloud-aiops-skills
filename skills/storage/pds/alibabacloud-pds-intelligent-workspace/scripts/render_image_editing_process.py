#!/usr/bin/env python3
"""
Image Editing Parameter Generation Script
Used to generate x-pds-process parameters for PDS image editing
"""

import argparse
import base64
from typing import Optional, List


def url_safe_base64_encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).rstrip(b'=').decode()


def build_pds_schema(domain_id: str, drive_id: str, file_id: str, revision_id: str = "") -> str:
    """Build pds_schema format"""
    return f"pds://domains/{domain_id}/drives/{drive_id}/files/{file_id}/revisions/{revision_id}"


def build_oss_process(action: str, params: List[str] = None) -> str:
    """Build OSS image processing parameters
    
    Args:
        action: Operation type, such as resize, rotate, crop, etc.
        params: Parameter list, such as ['w_100', 'h_100']
    
    Returns:
        OSS processing parameter string
    """
    if params:
        return f"{action},{','.join(params)}"
    return action


def build_segment_process(segment_type: str, params: dict = None) -> str:
    """Build segmentation parameters
    
    Args:
        segment_type: Segmentation type
            - 'auto': Auto recognition
            - 'point': Point-based segmentation, requires x, y coordinates
            - 'box': Rectangle segmentation, requires x, y, w, h parameters
            - 'text': Text-based segmentation, requires prompt parameter
        params: Corresponding parameters
    
    Returns:
        Segmentation parameter string
    """
    if segment_type == 'auto':
        return "image/segment"
    elif segment_type == 'point':
        x = params.get('x')
        y = params.get('y')
        return f"image/segment,points_(x_{x},y_{y})"
    elif segment_type == 'box':
        x = params.get('x')
        y = params.get('y')
        w = params.get('w')
        h = params.get('h')
        return f"image/segment,boxes_(x_{x},y_{y},w_{w},h_{h})"
    elif segment_type == 'text':
        prompt = params.get('prompt')
        prompt_base64 = url_safe_base64_encode(prompt)
        return f"image/segment,prompt_{prompt_base64}"
    else:
        raise ValueError(f"Unsupported segmentation type: {segment_type}")


def build_remove_process(remove_type: str, params: dict) -> str:
    """Build image removal parameters
    
    Args:
        remove_type: Removal type
            - 'point': Point-based removal, requires x, y coordinates
            - 'box': Rectangle removal, requires x, y, w, h parameters
        params: Corresponding parameters
    
    Returns:
        Removal parameter string
    """
    if remove_type == 'point':
        x = params.get('x')
        y = params.get('y')
        return f"image/remove,points_(x_{x},y_{y})"
    elif remove_type == 'box':
        x = params.get('x')
        y = params.get('y')
        w = params.get('w')
        h = params.get('h')
        return f"image/remove,boxes_(x_{x},y_{y},w_{w},h_{h})"
    else:
        raise ValueError(f"Unsupported removal type: {remove_type}")


def build_watermark_process(watermark_image_schema: str, params: dict = None) -> str:
    """Build watermark parameters
    
    Args:
        watermark_image_schema: Watermark image pds_schema (before base64 encoding)
        params: Watermark parameters (position, transparency, etc.)
    
    Returns:
        Watermark parameter string
    """
    watermark_base64 = url_safe_base64_encode(watermark_image_schema)
    
    # Basic watermark parameters
    watermark_str = f"image/watermark,image_{watermark_base64}"
    
    # Add other watermark parameters
    if params:
        for key, value in params.items():
            watermark_str += f",{key}_{value}"
    
    
    return watermark_str


def build_saveas_process(target_schema: str, file_name: str) -> str:
    """Build save-as parameters
    
    Args:
        target_schema: Target location pds_schema
        file_name: Saved file name
    
    Returns:
        Save-as parameter string
    """
    schema_base64 = url_safe_base64_encode(target_schema)
    name_base64 = url_safe_base64_encode(file_name)
    return f"sys/saveas,f_{schema_base64},name_{name_base64}"


def generate_x_pds_process(operations: List[str], saveas: dict = None) -> str:
    """Generate complete x-pds-process parameter
    
    Args:
        operations: Image editing operation list, executed in order. The first operation needs 'image/' prefix,
                    subsequent operations do not need 'image/' prefix (e.g., ['image/segment', 'resize,p_200'])
        saveas: Save-as parameters, including target_domain_id, target_drive_id, target_file_id, 
                target_revision_id, file_name
    
    Returns:
        Complete x-pds-process parameter string
    """
    # Process operation list: ensure only the first operation has image/ prefix
    processed_operations = []
    for i, op in enumerate(operations):
        if i == 0:
            # First operation, ensure it has image/ prefix
            if not op.startswith('image/'):
                processed_operations.append(f'image/{op}')
            else:
                processed_operations.append(op)
        else:
            # Subsequent operations, remove image/ prefix
            if op.startswith('image/'):
                processed_operations.append(op[6:])  # Remove 'image/' prefix
            else:
                processed_operations.append(op)
    
    # Combine all operations
    x_pds_process = "/".join(processed_operations)
    
    # Add save-as parameters
    if saveas:
        target_schema = build_pds_schema(
            saveas['target_domain_id'],
            saveas['target_drive_id'],
            saveas['target_file_id'],
            saveas.get('target_revision_id', '')
        )
        saveas_str = build_saveas_process(target_schema, saveas['file_name'])
        x_pds_process = f"{x_pds_process}|{saveas_str}"
    
    return x_pds_process


def main():
    parser = argparse.ArgumentParser(description='Generate image editing request parameter x-pds-process')
    
    # Basic parameters
    parser.add_argument('--operations', required=True, nargs='+', 
                       help='Image editing operation list, multiple operations separated by spaces')
    
    # Save-as parameters (optional)
    parser.add_argument('--saveas', action='store_true', help='Whether to save-as the edited image')
    parser.add_argument('--target-domain-id', help='Target domain_id for save-as')
    parser.add_argument('--target-drive-id', help='Target drive_id for save-as')
    parser.add_argument('--target-file-id', help='Target file_id for save-as (parent_file_id when creating new file)')
    parser.add_argument('--target-revision-id', help='Target revision_id for save-as (empty when creating new file)')
    parser.add_argument('--file-name', help='File name for save-as')
    
    args = parser.parse_args()
    
    # Build save-as parameters
    saveas = None
    if args.saveas:
        if not all([args.target_domain_id, args.target_drive_id, args.target_file_id, args.file_name]):
            raise ValueError("Save-as requires target-domain-id, target-drive-id, target-file-id and file-name")
        saveas = {
            'target_domain_id': args.target_domain_id,
            'target_drive_id': args.target_drive_id,
            'target_file_id': args.target_file_id,
            'target_revision_id': args.target_revision_id or '',
            'file_name': args.file_name
        }
    
    # Generate x-pds-process
    x_pds_process = generate_x_pds_process(args.operations, saveas)
    print(x_pds_process)


if __name__ == '__main__':
    main()
