#!/usr/bin/env python3
"""
replay JSON filequalitytool

 CMH trafficreplay JSON Lines formatfilemerge.jsonCloudLensSLS JSON 
auto sqla/WCRParser Supports check-only mode and repair mode

Supported file formats:
  -  JSON Lines file (.json)
  - zip archive (.json.zip / .zip)
  - gzip compressed (.json.gz)

Issues repaired:
  1. schema fieldcorruptedillegal charsKV format data
  2. OUT/IN OUT parameter bind value lost
  3. SQL binary
  4.  mojibake → ,
  5. PL/SQL valuevalue
  6. startTime anomalynormaltimerange
  7. execTime anomalytimeduration

Usage:
  # check onlyno modificationfile
  python3 fix_replay_json.py --input /path/to/replay.json --check-only

  # 
  python3 fix_replay_json.py --input /path/to/replay.json

  # outputpathdefault schema
  python3 fix_replay_json.py --input /path/to/merge.json.zip --output /path/to/fixed.json.zip --default-schema MY_SCHEMA

  # customthreshold
  python3 fix_replay_json.py --input replay.json --start-time-year 2025 --exec-time-max-hours 2
"""

import argparse
import json
import re
import os
import sys
import time
import gzip
import zipfile
from collections import Counter
from contextlib import contextmanager


# ============================================================
# rule
# ============================================================

# Schema : Oracle/PG 
VALID_SCHEMA_PATTERN = re.compile(r'^[A-Za-z0-9_$]+$')

# OUT parameterempty value: => 
OUT_PARAM_PATTERN = re.compile(r'(=>\s*)(\s*[,\)])')

# binarythreshold: ratiovalue
BINARY_GARBAGE_RATIO = 0.2

# Mojibake: sqla/WCRParser  GBK encodingcorrupted=stringexternal
#    (U+951B)          =  '' corrupted           → ','
#    (U+9286)          =  FROM emptycorrupted    → ' '
#    (U+951B U+5869) = query+ → ') c' col_aol_a_n  col_a) col_a_n
# mojibakemojibakereplace  rule ','
MOJIBAKE_CHARS = ('\u951b', '\u9286', '\u5869')          #   
MOJIBAKE_COMPOUND = (('\u951b\u5869', ') c'),)           #  -> ) c
MOJIBAKE_SINGLE = (('\u9286', ' '), ('\u951b', ','))     # ->empty, ->
MOJIBAKE_COMMA = '\u951b'                                # compatible

# PL/SQL valuevalue
ORPHAN_ASSIGN_PATTERN = re.compile(r"(?:BEGIN|;)\s*:=\s*\w+", re.IGNORECASE)
EMPTY_STR_ASSIGN_PATTERN = re.compile(r"''\s*:=\s*\w+")

# SQL fieldcompatibleformat JSON field
SQL_TEXT_FIELDS = ['convertSqlText', 'sql_text', 'sqlText', 'query', 'sql']
SCHEMA_FIELDS = ['schema', 'schemaName', 'db_name', 'database']
START_TIME_FIELDS = ['startTime', 'start_time', 'timestamp', 'ts']
EXEC_TIME_FIELDS = ['execTime', 'exec_time', 'duration', 'rt']


# ============================================================
# function
# ============================================================

def get_field(obj, field_names, default=None):
    """ JSON objectfieldvalue"""
    for f in field_names:
        if f in obj:
            return f, obj[f]
    return field_names[0], default


def is_binary_garbage(text):
    """binary
     ord<32  \\t\\n\\r 0x0E/0x14/0x16  ord<9 """
    if not text or len(text) == 0:
        return False  # empty SQL  session event
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\t\n\r')
    return control_chars / len(text) > BINARY_GARBAGE_RATIO


def fix_mojibake_comma(sql_text):
    """ GBK mojibake//→ stringexternalreplace
    mojibakemojibake/"""
    if not any(m in sql_text for m in MOJIBAKE_CHARS):
        return sql_text, False
    parts = sql_text.split("'")
    for i in range(0, len(parts), 2):  # index = 
        seg = parts[i]
        for bad, good in MOJIBAKE_COMPOUND:
            seg = seg.replace(bad, good)
        for bad, good in MOJIBAKE_SINGLE:
            seg = seg.replace(bad, good)
        parts[i] = seg
    fixed = "'".join(parts)
    return fixed, (fixed != sql_text)


# parameteremptyvalue:  (, / ,, / ,)
_EMPTY_SLOT_OPEN = re.compile(r'\(\s*,')
_EMPTY_SLOT_MID = re.compile(r',\s*,')
_EMPTY_SLOT_CLOSE = re.compile(r',\s*\)')


def has_empty_slot_outside(sql_text):
    """stringexternalemptyparameter"""
    parts = sql_text.split("'")
    for i in range(0, len(parts), 2):  # index = 
        seg = parts[i]
        if _EMPTY_SLOT_OPEN.search(seg) or _EMPTY_SLOT_MID.search(seg) or _EMPTY_SLOT_CLOSE.search(seg):
            return True
    return False


def fill_empty_slots(sql_text):
    """emptyparameter NULL DQLfunctionsecurity NULL"""
    parts = sql_text.split("'")
    for i in range(0, len(parts), 2):
        seg = parts[i]
        prev = None
        while prev != seg:  # empty ,,,
            prev = seg
            seg = _EMPTY_SLOT_OPEN.sub('(NULL,', seg)
            seg = _EMPTY_SLOT_CLOSE.sub(',NULL)', seg)
            seg = _EMPTY_SLOT_MID.sub(',NULL,', seg)
        parts[i] = seg
    return "'".join(parts)


def is_dql_stmt(sql_text):
    """ DQLSELECT/WITHfunction NULL security DQLCALL/BEGIN/DML OUT skipped"""
    s = sql_text.lstrip().lower()
    return s.startswith('select') or s.startswith('with')


def calc_start_time_threshold(year):
    """ startTime thresholdmicroseconds Unix time"""
    import calendar
    import datetime
    #  11 
    dt = datetime.datetime(year, 1, 1)
    ts_seconds = calendar.timegm(dt.timetuple())
    return ts_seconds * 1_000_000  # microseconds


# ============================================================
# file IO 
# ============================================================

@contextmanager
def open_input(input_path):
    """openformatinputfile (file_object, json_filename)"""
    if input_path.endswith('.gz'):
        f = gzip.open(input_path, 'rb')
        yield f, os.path.basename(input_path).replace('.gz', '')
        f.close()
    elif input_path.endswith('.zip') or '.json.zip' in input_path:
        zf = zipfile.ZipFile(input_path, 'r')
        json_files = [n for n in zf.namelist() if n.endswith('.json')]
        if not json_files:
            json_files = [n for n in zf.namelist() if not n.endswith('/')]
        if not json_files:
            raise FileNotFoundError(f"zip  JSON file: {input_path}")
        json_path = json_files[0]
        f = zf.open(json_path)
        yield f, json_path
        f.close()
        zf.close()
    else:
        f = open(input_path, 'rb')
        yield f, os.path.basename(input_path)
        f.close()


def write_output(output_path, json_filename, tmp_file):
    """filewriteoutputformat"""
    if output_path.endswith('.gz'):
        with open(tmp_file, 'rb') as fin, gzip.open(output_path, 'wb') as fout:
            while True:
                chunk = fin.read(10 * 1024 * 1024)
                if not chunk:
                    break
                fout.write(chunk)
    elif output_path.endswith('.zip') or '.json.zip' in output_path:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_file, json_filename)
    else:
        os.rename(tmp_file, output_path)
        return  # rename  tmp
    # Only remove our own controlled temp file (output_path + '.tmp'); never follow symlinks
    if tmp_file.endswith('.tmp') and os.path.isfile(tmp_file) and not os.path.islink(tmp_file):
        os.remove(tmp_file)


# ============================================================
# core
# ============================================================

def auto_detect_schema(input_path, sample_size=5*1024*1024):
    """fileautovalid schema """
    schemas = Counter()
    with open_input(input_path) as (fin, _):
        data = fin.read(sample_size)
    lines = data.decode('utf-8', errors='replace').split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            _, schema = get_field(obj, SCHEMA_FIELDS, '')
            if schema and VALID_SCHEMA_PATTERN.match(str(schema)):
                schemas[schema] += 1
        except:
            continue
    if schemas:
        return schemas.most_common(1)[0][0]
    return None


def pre_scan_starttime(input_path, threshold):
    """itemsvalid startTime"""
    with open_input(input_path) as (fin, _):
        data = fin.read(5 * 1024 * 1024)
    lines = data.decode('utf-8', errors='replace').split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            _, st_val = get_field(obj, START_TIME_FIELDS, 0)
            if isinstance(st_val, str):
                st_val = int(st_val) if st_val.isdigit() else 0
            if st_val and int(st_val) >= threshold:
                return int(st_val)
        except:
            continue
    return None


def process_record(obj, config):
    """
    entriesrecords (processed_obj, issues_dict)  (None, issues_dict) tableskipped
    issues_dict recordstype
    """
    issues = {
        'schema_fixed': False,
        'out_param_skip': False,
        'binary_garbage': False,
        'mojibake_fixed': False,
        'orphan_assign': False,
        'starttime_bad': False,
        'exectime_bad': False,
        'empty_slot_filled': False,
        'empty_slot_skip': False,
    }

    sql_field, sql = get_field(obj, SQL_TEXT_FIELDS, '')
    schema_field, schema = get_field(obj, SCHEMA_FIELDS, '')
    st_field, st_val = get_field(obj, START_TIME_FIELDS, 0)
    et_field, et_val = get_field(obj, EXEC_TIME_FIELDS, 0)

    # transformation startTime 
    if isinstance(st_val, str):
        st_val = int(st_val) if st_val.isdigit() else 0

    # transformation execTime 
    if isinstance(et_val, str):
        et_val = int(et_val) if et_val.lstrip('-').isdigit() else 0

    # ---  3: binary ---
    if is_binary_garbage(sql):
        issues['binary_garbage'] = True
        return None, issues

    # ---  1: schema corrupted ---
    if schema and not VALID_SCHEMA_PATTERN.match(str(schema)):
        if config['default_schema']:
            obj[schema_field] = config['default_schema']
        issues['schema_fixed'] = True

    # ---  2: OUT parameterempty value ---
    if sql and '=>' in sql:
        if OUT_PARAM_PATTERN.search(sql):
            issues['out_param_skip'] = True
            return None, issues

    # ---  8: parameteremptyvalue: (, / ,, / ,)---
    #   DQL(SELECT): function NULLkeepreplay;  DQL(CALL/BEGIN/DML): OUT skipped
    if sql and has_empty_slot_outside(sql):
        if is_dql_stmt(sql):
            new_sql = fill_empty_slots(sql)
            if new_sql != sql:
                obj[sql_field] = new_sql
                sql = new_sql
                issues['empty_slot_filled'] = True
        else:
            issues['empty_slot_skip'] = True
            return None, issues

    # ---  4: // mojibake---
    if sql and any(m in sql for m in MOJIBAKE_CHARS):
        fixed_sql, was_fixed = fix_mojibake_comma(sql)
        if was_fixed:
            obj[sql_field] = fixed_sql
            issues['mojibake_fixed'] = True

    # ---  5: PL/SQL valuevalue ---
    if sql and ':=' in sql:
        if ORPHAN_ASSIGN_PATTERN.search(sql) or EMPTY_STR_ASSIGN_PATTERN.search(sql):
            issues['orphan_assign'] = True
            return None, issues

    # ---  6: startTime anomaly ---
    if st_val < config['start_time_threshold']:
        issues['starttime_bad'] = True

    # ---  7: execTime anomaly ---
    if et_val > config['exec_time_threshold']:
        issues['exectime_bad'] = True

    return obj, issues


def run_check_only(input_path, config):
    """check onlymode: reportno modificationfile"""
    print(f"\n{'='*60}")
    print(f"📋 replayfilequalitycheck only")
    print(f"{'='*60}")
    print(f"inputfile: {input_path}")
    print(f"File size: {os.path.getsize(input_path)/1024/1024:.1f} MB")
    print(f"\n...\n")

    counters = Counter()
    total = 0
    errors = 0
    start = time.time()

    with open_input(input_path) as (fin, json_name):
        print(f"JSON file: {json_name}")
        leftover = b""
        chunk_size = 100 * 1024 * 1024

        while True:
            raw = fin.read(chunk_size)
            if not raw:
                if leftover.strip():
                    line = leftover.decode('utf-8', errors='replace').strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            _, issues = process_record(obj, config)
                            total += 1
                            for k, v in issues.items():
                                if v:
                                    counters[k] += 1
                        except:
                            errors += 1
                break

            data = leftover + raw
            lines = data.split(b'\n')
            leftover = lines[-1]

            for line_bytes in lines[:-1]:
                line = line_bytes.decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    _, issues = process_record(obj, config)
                    total += 1
                    for k, v in issues.items():
                        if v:
                            counters[k] += 1
                except:
                    errors += 1

            if total > 0 and total % 1000000 == 0:
                print(f"   {total:,} entries...")

    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"📊 result")
    print(f"{'='*60}")
    print(f"  Total records:          {total:,}")
    print(f"  JSON parsefailed:     {errors:,}")
    print(f"")
    print(f"  ---  ---")
    print(f"  schema corrupted:       {counters['schema_fixed']:,}")
    print(f"  OUT parameterempty value:      {counters['out_param_skip']:,}")
    print(f"  binary:        {counters['binary_garbage']:,}")
    print(f"   mojibake:       {counters['mojibake_fixed']:,}")
    print(f"  valuevalue:      {counters['orphan_assign']:,}")
    print(f"  emptyNULL:    {counters['empty_slot_filled']:,}")
    print(f"  emptyskipped:      {counters['empty_slot_skip']:,}")
    print(f"  startTime anomaly:    {counters['starttime_bad']:,}")
    print(f"  execTime anomaly:     {counters['exectime_bad']:,}")
    print(f"")
    total_issues = sum(counters.values())
    print(f"  :          {total_issues:,}")
    print(f"  duration:              {elapsed:.1f}s")
    print(f"{'='*60}")

    if total_issues == 0:
        print("\n✅ filequalityreplay")
    else:
        print(f"\n⚠️   {total_issues:,} itemslines --check-only parameter")

    return total_issues


def run_fix(input_path, output_path, config):
    """mode: outputfile"""
    print(f"\n{'='*60}")
    print(f"🔧 replayfilequality")
    print(f"{'='*60}")
    print(f"input: {input_path}")
    print(f"output: {output_path}")
    print(f"default schema: {config['default_schema'] or '(,keepvalue)'}")
    print(f"startTime threshold: {config['start_time_threshold']:,}")
    print(f"execTime threshold: {config['exec_time_threshold']:,} μs")

    # itemsvalid startTime
    last_valid_starttime = pre_scan_starttime(input_path, config['start_time_threshold'])
    print(f"itemsvalidtime: {last_valid_starttime}")
    print(f"\n...\n")

    # statistics
    total = 0
    fixed_schema = 0
    skipped_out = 0
    skipped_garbage = 0
    fixed_mojibake = 0
    skipped_orphan = 0
    filled_slot = 0
    skipped_slot = 0
    fixed_starttime = 0
    fixed_exectime = 0
    errors = 0
    start = time.time()

    # output JSON file
    with open_input(input_path) as (_, json_name):
        pass

    tmp_file = output_path + '.tmp'

    with open_input(input_path) as (fin, json_name):
        with open(tmp_file, 'wb') as fout:
            leftover = b""
            chunk_size = 100 * 1024 * 1024

            while True:
                raw = fin.read(chunk_size)
                if not raw:
                    if leftover.strip():
                        line = leftover.decode('utf-8', errors='replace').strip()
                        if line:
                            result = _process_and_write(
                                line, fout, config, last_valid_starttime)
                            if result is not None:
                                total, fixed_schema, skipped_out, skipped_garbage, \
                                    fixed_mojibake, skipped_orphan, fixed_starttime, \
                                    fixed_exectime, last_valid_starttime, errors = result
                    break

                data = leftover + raw
                lines = data.split(b'\n')
                leftover = lines[-1]

                for line_bytes in lines[:-1]:
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                    except:
                        errors += 1
                        continue

                    processed, issues = process_record(obj, config)

                    if issues['binary_garbage']:
                        skipped_garbage += 1
                        continue
                    if issues['out_param_skip']:
                        skipped_out += 1
                        continue
                    if issues['orphan_assign']:
                        skipped_orphan += 1
                        continue
                    if issues['empty_slot_skip']:
                        skipped_slot += 1
                        continue

                    # startTime 
                    if issues['starttime_bad'] and last_valid_starttime:
                        st_field, _ = get_field(processed, START_TIME_FIELDS, 0)
                        processed[st_field] = last_valid_starttime
                        fixed_starttime += 1
                    elif not issues['starttime_bad']:
                        _, st_val = get_field(processed, START_TIME_FIELDS, 0)
                        if isinstance(st_val, str):
                            st_val = int(st_val) if st_val.isdigit() else 0
                        if st_val >= config['start_time_threshold']:
                            last_valid_starttime = int(st_val)

                    # execTime 
                    if issues['exectime_bad']:
                        et_field, _ = get_field(processed, EXEC_TIME_FIELDS, 0)
                        processed[et_field] = config['default_exec_time']
                        fixed_exectime += 1

                    # 
                    if issues['schema_fixed']:
                        fixed_schema += 1
                    if issues['mojibake_fixed']:
                        fixed_mojibake += 1
                    if issues['empty_slot_filled']:
                        filled_slot += 1

                    total += 1
                    fout.write(json.dumps(processed, ensure_ascii=False).encode('utf-8'))
                    fout.write(b'\n')

                # 
                if total > 0 and total % 500000 == 0:
                    elapsed = time.time() - start
                    print(f"  processed {total:,} entries, duration {elapsed:.0f}s")

    # writeoutputformat
    print(f"\nwriteoutputfile...")
    write_output(output_path, json_name, tmp_file)

    elapsed = time.time() - start
    output_size = os.path.getsize(output_path)

    print(f"\n{'='*60}")
    print(f"✅ Repair complete!")
    print(f"{'='*60}")
    print(f"  Total records:          {total:,}")
    print(f"  schema :       {fixed_schema:,}")
    print(f"  OUT parameterskipped:      {skipped_out:,}")
    print(f"  binaryskipped:    {skipped_garbage:,}")
    print(f"  →:       {fixed_mojibake:,}")
    print(f"  valuevalueskipped:  {skipped_orphan:,}")
    print(f"  emptyNULL:    {filled_slot:,}")
    print(f"  emptyskipped:      {skipped_slot:,}")
    print(f"  startTime :    {fixed_starttime:,}")
    print(f"  execTime :     {fixed_exectime:,}")
    print(f"  JSON parsefailed:     {errors:,}")
    print(f"  duration:              {elapsed:.1f}s")
    print(f"  outputfile:          {output_path} ({output_size/1024/1024:.1f} MB)")
    print(f"{'='*60}")


# ============================================================
# CLI 
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description='replay JSON filequalitytool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
:
  # check only
  python3 fix_replay_json.py --input merge.json.zip --check-only

  # output
  python3 fix_replay_json.py --input merge.json.zip --output merge_fixed.json.zip

  # default schema
  python3 fix_replay_json.py --input replay.json --default-schema MY_SCHEMA

  # time
  python3 fix_replay_json.py --input replay.json --start-time-year 2024
""")
    parser.add_argument('--input', '-i', required=True,
                        help='inputfilepath (.json / .json.zip / .json.gz)')
    parser.add_argument('--output', '-o',
                        help='outputfilepath (default: <input>_fixed.<ext>)')
    parser.add_argument('--check-only', '-c', action='store_true',
                        help='check onlyoutputqualityreport')
    parser.add_argument('--default-schema', '-s',
                        help='corrupted schema replacevalue (default: autofilevalid schema)')
    parser.add_argument('--start-time-year', type=int, default=2024,
                        help='startTime  (default: 2024, time >= 2024-01-01)')
    parser.add_argument('--exec-time-max-hours', type=float, default=1.0,
                        help='execTime threshold(hours), anomaly (default: 1.0)')
    parser.add_argument('--default-exec-time', type=int, default=50,
                        help='anomaly execTime replacevalue(microseconds) (default: 50,  P50)')
    return parser.parse_args()


def default_output_path(input_path):
    """defaultoutputpath"""
    base, ext = os.path.splitext(input_path)
    if input_path.endswith('.json.zip'):
        base = input_path[:-9]  # remove .json.zip
        return f"{base}_fixed.json.zip"
    elif input_path.endswith('.json.gz'):
        base = input_path[:-8]  # remove .json.gz
        return f"{base}_fixed.json.gz"
    elif input_path.endswith('.zip'):
        base = input_path[:-4]
        return f"{base}_fixed.zip"
    else:
        return f"{base}_fixed{ext}"


def main():
    args = parse_args()

    if not os.path.exists(args.input):
        print(f"❌ File not found: {args.input}")
        sys.exit(1)

    # buildconfig
    start_time_threshold = calc_start_time_threshold(args.start_time_year)
    exec_time_threshold = int(args.exec_time_max_hours * 3600 * 1_000_000)

    # autodefault schema
    default_schema = args.default_schema
    if not default_schema:
        print("🔍 auto schema...")
        default_schema = auto_detect_schema(args.input)
        if default_schema:
            print(f"    schema: {default_schema}")
        else:
            print("   ⚠️ valid schemacorrupted schema replace")

    config = {
        'default_schema': default_schema,
        'start_time_threshold': start_time_threshold,
        'exec_time_threshold': exec_time_threshold,
        'default_exec_time': args.default_exec_time,
    }

    if args.check_only:
        run_check_only(args.input, config)
    else:
        output_path = args.output or default_output_path(args.input)
        run_fix(args.input, output_path, config)


if __name__ == '__main__':
    main()
