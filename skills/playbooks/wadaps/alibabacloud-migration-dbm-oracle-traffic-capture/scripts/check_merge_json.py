#!/usr/bin/env python3
"""
replay SQL filescript

Functions:
1. replay SQL fileformat(JSON Lines,one record per line)
2. statistics SQL countFile size
3.  SQL typedistribution(DQL/DML)
4.  Schema distribution
5. Provide replay recommendations

Supported formats: merge.json(sqla parse output)CloudLens formatSLS Json/CSVTShark format JSON Lines format

Usage:
python scripts/check_merge_json.py --input /path/to/your-replay-file.json
"""

import argparse
import json
import os
import sys
from collections import Counter


def parse_args():
    parser = argparse.ArgumentParser(description='Check replay SQL file (JSON Lines format)')
    parser.add_argument('--input', required=True,
                        help='Path to replay SQL file (e.g. merge.json, capture_xxx.json)')
    return parser.parse_args()


def check_file_exists(file_path):
    """Check if file exists and is not empty"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print(f"❌ fileempty: {file_path}")
        sys.exit(1)
    
    print(f"✅ file: {file_path}")
    print(f"📦 File size: {file_size / 1024 / 1024:.2f} MB")
    return file_size


def parse_merge_json(file_path):
    """Parse merge.json and extract statistics"""
    sql_count = 0
    sql_types = Counter()
    schemas = Counter()
    error_lines = []
    
    print("\n🔍 parsereplay SQL file...")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                sql_data = json.loads(line)
                sql_count += 1
                
                # Count SQL types
                sql_text = sql_data.get('convertSqlText', '').upper()
                if sql_text.startswith('SELECT'):
                    sql_types['DQL'] += 1
                elif sql_text.startswith(('INSERT', 'UPDATE', 'DELETE')):
                    sql_types['DML'] += 1
                elif sql_text.startswith(('CREATE', 'ALTER', 'DROP')):
                    sql_types['DDL'] += 1
                else:
                    sql_types['OTHER'] += 1
                
                # Count schemas
                schema = sql_data.get('schema', 'UNKNOWN')
                schemas[schema] += 1
                
            except json.JSONDecodeError as e:
                error_lines.append((line_num, str(e)))
                continue
    
    return sql_count, sql_types, schemas, error_lines


def analyze_and_report(sql_count, sql_types, schemas, error_lines, file_size):
    """Generate analysis report"""
    print("\n" + "="*60)
    print("📊 replay SQL filereport")
    print("="*60)
    
    # Basic statistics
    print(f"\n✅ SQL : {sql_count:,} entries")
    print(f"📝 formaterrorlines: {len(error_lines)} lines")
    
    if len(error_lines) > 0:
        print("\n⚠️  formaterror( 5 lines):")
        for line_num, error in error_lines[:5]:
            print(f"  lines {line_num}: {error}")
    
    # SQL type distribution
    if sql_count > 0:
        print(f"\n📈 SQL typedistribution:")
        print(f"  - DQL(query): {sql_types['DQL']:,} entries ({sql_types['DQL']/sql_count*100:.1f}%)")
        print(f"  - DML(operation): {sql_types['DML']:,} entries ({sql_types['DML']/sql_count*100:.1f}%)")
        print(f"  - DDL(): {sql_types['DDL']:,} entries ({sql_types['DDL']/sql_count*100:.1f}%)")
        print(f"  - : {sql_types['OTHER']:,} entries ({sql_types['OTHER']/sql_count*100:.1f}%)")
    
    # Schema distribution
    print(f"\n🏢 Schema distribution( 10):")
    for schema, count in schemas.most_common(10):
        percentage = count / sql_count * 100 if sql_count > 0 else 0
        print(f"  - {schema}: {count:,} entries ({percentage:.1f}%)")
    
    # Recommendations
    print("\n" + "="*60)
    print("💡 replay")
    print("="*60)
    
    # File size check
    file_size_mb = file_size / 1024 / 1024
    if file_size_mb < 1:
        print("\n⚠️  file(<1MB)")
        print("  : collectionfailedcollectiontime")
        print("  : collectiontraffic,collection( 5-10 minutes)")
    elif file_size_mb > 500:
        print("\n️  file(>500MB)")
        print("  : replay,timesreplaytime")
        print("  command: split -l 10000 replay-file.json replay_part_")
    else:
        print(f"\n✅ File size({file_size_mb:.2f} MB)")
    
    # SQL count check
    if sql_count < 100:
        print("\n⚠️  SQL count(<100)")
        print("  : collectiontraffic")
        print("  : collection")
    elif sql_count < 1000:
        print(f"\n⚠️  SQL count({sql_count:,} entries)")
        print("  : collection,period")
    else:
        print(f"\n✅ SQL count({sql_count:,} entries)")
    
    # SQL type recommendations
    if sql_types['DML'] > 0:
        print(f"\n⚠️   DML ({sql_types['DML']:,} entries)")
        print("  timesreplay:")
        print("  - replay SQL type:  DQL(security)")
        print("  -  commit: ()")
    
    # Schema recommendations
    if len(schemas) > 1:
        print(f"\n📋  {len(schemas)} items Schema")
        print("  :")
        print("  - replay Schema, Schema filterparameter")
        print("  - mapping Schema, Schema mappingparameter")
    
    # Error lines check
    if len(error_lines) > 0:
        error_rate = len(error_lines) / (sql_count + len(error_lines)) * 100
        if error_rate > 5:
            print(f"\n❌ formaterror({error_rate:.1f}%)")
            print("  : replay SQL fileformat")
            print("  : lines sqla parsefile")
        elif error_rate > 0:
            print(f"\n⚠️  formaterror({error_rate:.1f}%)")
            print("  ,replay")
    
    print("\n" + "="*60)
    
    # Overall assessment
    if sql_count >= 1000 and file_size_mb >= 1 and file_size_mb <= 500 and len(error_lines) == 0:
        print("✅ filestatus: ,replay")
    elif sql_count >= 100 and file_size_mb < 500:
        print("✅ filestatus: ,replay")
    else:
        print("⚠️  filestatus: optimization,")
    
    print("="*60)


def main():
    args = parse_args()
    
    # Check file
    file_size = check_file_exists(args.input)
    
    # Parse merge.json
    sql_count, sql_types, schemas, error_lines = parse_merge_json(args.input)
    
    # Generate report
    analyze_and_report(sql_count, sql_types, schemas, error_lines, file_size)


if __name__ == '__main__':
    main()
