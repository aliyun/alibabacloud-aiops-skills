"""Convert already-read successful content into bounded traceable evidence tables using only the standard library."""

import csv
import hashlib
import io
import json
import os
import re
import stat
from decimal import Decimal, localcontext
from fractions import Fraction

from context_graph_contract import (SkillError, normalize_endpoint, parse_json,
                                    safe_output, validate_request, validate_response)

SCHEMA = 'context-graph-answer-job-v1'
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 10000
MAX_BLOCKS = 128
MAX_OPERATIONS = 50
MAX_OUTPUT_BYTES = 16 * 1024 * 1024


class EvidenceError(Exception):
    """Expose fixed error codes without invalid input or raw exceptions."""

    def __init__(self, code='InvalidJob'):
        self.code = code
        super().__init__('The local answer job is invalid or exceeds safe limits.')


def require(condition, code='InvalidJob'):
    if not condition:
        raise EvidenceError(code)


def fields(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value)
            and not set(value) - set(required) - set(optional))


def string(value, limit=512):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit
            and not any(ord(c) < 32 for c in value))
    return value


def names(value, maximum=128, *, empty=False):
    require(isinstance(value, list) and (empty or bool(value)) and len(value) <= maximum)
    for item in value:
        string(item)
    require(len(set(value)) == len(value))
    return value


def json_size(value, limit, *, indent=None):
    """Count JSON bytes incrementally and stop at the limit without constructing huge temporary strings."""
    total = 0
    for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False, indent=indent).iterencode(value):
        total += len(chunk.encode('utf-8'))
        require(total <= limit, 'BudgetExceeded')
    return total


def bounded(value):
    """Bound object inputs too, preventing file-entry bypass through excessive nesting or structure size."""
    stack, count = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        require(depth <= 32 and count <= 300000, 'BudgetExceeded')
        if isinstance(item, dict):
            require(all(isinstance(key, str) for key in item))
            stack.extend((entry, depth + 1) for entry in item.values())
        elif isinstance(item, list):
            stack.extend((entry, depth + 1) for entry in item)
        elif isinstance(item, str):
            require(len(item) <= MAX_BYTES, 'BudgetExceeded')
        else:
            require(item is None or type(item) in (int, bool))
    try:
        require(len(json.dumps(value, ensure_ascii=False).encode('utf-8')) <= MAX_BYTES,
                'BudgetExceeded')
    except (ValueError, UnicodeError, RecursionError):
        raise EvidenceError() from None


def load_job(path):
    """Open nonblocking and require a regular file; reject FIFOs, symlinks, and oversized JSON."""
    descriptor = None
    try:
        nonblocking, nofollow = getattr(os, 'O_NONBLOCK', None), getattr(os, 'O_NOFOLLOW', None)
        require(type(nonblocking) is int and type(nofollow) is int, 'UnsupportedPlatform')
        descriptor = os.open(path, os.O_RDONLY | nonblocking | nofollow)
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, 'UnsafeInputFile')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            content = stream.read(MAX_BYTES + 1)
        require(len(content) <= MAX_BYTES, 'BudgetExceeded')
        result = parse_json(content.decode('utf-8'))
        require(isinstance(result, dict))
        bounded(result)
        return result
    except (OSError, UnicodeError, SkillError, ValueError, RecursionError):
        raise EvidenceError() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def validate_context(value):
    fields(value, {'batch_id', 'identity_scope', 'region', 'snapshot'}, {'endpoint', 'KnowledgeBaseIds'})
    for key in ('batch_id', 'identity_scope'):
        string(value[key], 256)
    if value['snapshot'] is not None:
        string(value['snapshot'], 256)
    try:
        endpoint = normalize_endpoint(value['region'], value.get('endpoint'))
        if 'KnowledgeBaseIds' in value:
            validate_request('RetrieveKnowledgePoints', {'Query': 'scope-validation',
                                                        'KnowledgeBaseIds': value['KnowledgeBaseIds']})
    except SkillError:
        raise EvidenceError('InvalidContext') from None
    return {**value, 'endpoint': endpoint, 'declaration': 'caller-declared; actual live identity is not verified'}


def _domain(source_unit):
    """Derive domains only from source units and primary-key semantics, not logical aliases or filters."""
    canonical = json.dumps(source_unit, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _tsv_blocks(content):
    """Locate fences in one pass; reject nesting and unclosed blocks to avoid repeated suffix scans."""
    blocks, current, offset = [], None, 0
    for line_number, raw in enumerate(io.StringIO(content, newline=''), 1):
        line = raw.rstrip('\r\n')
        if line.startswith('```'):
            closing = re.fullmatch(r'```[ \t]*', line) is not None
            if current is not None:
                require(closing, 'InvalidTsv')
                if current['tsv']:
                    require(len(blocks) < MAX_BLOCKS, 'BudgetExceeded')
                    blocks.append({**current, 'end': offset})
                current = None
            else:
                current = {'tsv': re.fullmatch(r'```tsv[ \t]*', line) is not None,
                           'start': offset + len(raw), 'line_offset': line_number}
        offset += len(raw)
    require(current is None, 'InvalidTsv')
    return blocks


def _extract_table(specification, context):
    fields(specification, {'name', 'response', 'primary_key'}, {'block', 'coverage'})
    name = string(specification['name'])
    primary_key = names(specification['primary_key'])
    response = specification['response']
    require(isinstance(response, dict) and response.get('Action', 'GetKnowledgePoint') == 'GetKnowledgePoint')
    data = response.get('Data')
    require(isinstance(data, dict))
    identity = {key: data.get(key) for key in ('KnowledgeBaseId', 'Type', 'Id')}
    try:
        request = validate_request('GetKnowledgePoint', identity)
        validate_response('GetKnowledgePoint', request, response)
    except SkillError:
        raise EvidenceError('InvalidResponse') from None
    require(identity['Type'] in ('WIKI', 'KNOWLEDGE_CONTENT'))
    require('KnowledgeBaseIds' not in context or identity['KnowledgeBaseId'] in context['KnowledgeBaseIds'],
            'OutOfScope')
    body_item = data['Wiki' if identity['Type'] == 'WIKI' else 'KnowledgeContent']
    content, title = body_item['Content'], body_item['Title']
    require(len(content.encode('utf-8')) <= MAX_BYTES, 'BudgetExceeded')
    blocks = _tsv_blocks(content)
    if blocks:
        require('block' in specification or len(blocks) == 1, 'AmbiguousBlock')
        block = specification.get('block', 0)
        require(type(block) is int and 0 <= block < len(blocks))
        selected = blocks[block]
        body = content[selected['start']:selected['end']]
        line_offset = selected['line_offset']
        selected_range = {'format': 'tsv-block', 'block': block, 'start': selected['start'], 'end': selected['end']}
    else:
        require('block' not in specification and '```' not in content, 'InvalidTsv')
        body, line_offset = content, 0
        selected_range = {'format': 'plain-tsv', 'start': 0, 'end': len(content)}
    reader = csv.reader(io.StringIO(body, newline=''), delimiter='\t', strict=True)
    try:
        header = next(reader)
        names(header)
        require(set(primary_key) <= set(header), 'MissingPrimaryKey')
        rows, indexed, source_bytes, raw_count = [], {}, 0, 0
        previous_line = reader.line_num
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        for cells in reader:
            require(len(cells) == len(header), 'InvalidTsv')
            raw_count += 1
            require(raw_count <= MAX_ROWS, 'BudgetExceeded')
            values = dict(zip(header, cells))
            pk = tuple(values[column] for column in primary_key)
            require(all(value.strip() for value in pk), 'EmptyPrimaryKey')
            start = line_offset + previous_line + 1
            previous_line = reader.line_num
            # Estimate repeated metadata before wide tables multiply long titles or composite keys.
            base = {**identity, 'RequestId': response['RequestId'], 'Title': title,
                    'content_sha256': digest, 'primary_key': list(pk)}
            base_bytes = len(json.dumps(base, ensure_ascii=False).encode('utf-8'))
            value_bytes = sum(len(json.dumps(value, ensure_ascii=False).encode('utf-8')) for value in cells)
            require(source_bytes + base_bytes * len(header) + value_bytes <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
            sources = {column: [{**base, 'line_start': start,
                                'line_end': line_offset + reader.line_num, 'column': column,
                                'column_index': position + 1}]
                       for position, column in enumerate(header)}
            source_bytes += len(json.dumps({'values': values, 'sources': sources}, ensure_ascii=False).encode('utf-8'))
            require(source_bytes <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
            if pk in indexed:
                previous = indexed[pk]
                require(previous['values'] == values, 'ConflictingPrimaryKey')
                for column in header:
                    previous['sources'][column].extend(sources[column])
            else:
                row = {'pk': list(pk), 'values': values, 'sources': sources}
                indexed[pk] = row
                rows.append(row)
    except (csv.Error, StopIteration):
        raise EvidenceError('InvalidTsv') from None
    coverage = specification.get('coverage')
    if coverage is not None:
        fields(coverage, {'dataset', 'snapshot', 'row_count', 'basis'})
        for key in ('dataset', 'snapshot', 'basis'):
            string(coverage[key], 4096)
        require(type(coverage['row_count']) is int and 0 <= coverage['row_count'] <= MAX_ROWS)
        require(coverage['row_count'] == len(rows) and coverage['basis'] in content, 'InvalidCoverage')
        require(context['snapshot'] is not None and coverage['snapshot'] == context['snapshot'], 'SnapshotMismatch')
        coverage = {**coverage, 'declaration': 'caller-declared/source-quoted; not proof of complete live scope'}
    warnings = safe_output(data['Warnings'])
    truncated = any(item['Code'] in ('CONTENT_TRUNCATED', 'RESULT_TRUNCATED') for item in warnings)
    source_unit = {'type': 'source', 'identity': identity, 'content_sha256': digest,
                   'selected_range': selected_range, 'primary_key': primary_key,
                   'dataset': coverage['dataset'] if coverage is not None else None,
                   'snapshot': context['snapshot']}
    return {'name': name, 'columns': header, 'primary_key': primary_key, 'rows': rows,
            'domain': _domain(source_unit), 'source_unit': source_unit,
            'complete': coverage is not None and not truncated, 'coverage': coverage,
            'warnings': warnings, 'snapshot': context['snapshot'], 'origin': [identity],
            'table_sources': [{**identity, 'Title': title, 'RequestId': response['RequestId'], 'content_sha256': digest}],
            'coverage_declarations': [coverage] if coverage is not None else []}


def select_rows(table, where):
    require(isinstance(where, dict) and len(where) <= 128)
    require(set(where) <= set(table['columns']), 'MissingColumn')
    require(all(isinstance(value, str) for value in where.values()))
    return [row for row in table['rows'] if all(row['values'][key] == value for key, value in where.items())]


def _complete(tables, operation):
    required = operation.get('require_complete', True)
    require(type(required) is bool)
    complete = all(table['complete'] for table in tables)
    require(not required or complete, 'IncompleteAggregation')
    return complete


def _all_sources(table):
    """Retain participating primary keys and cell sources; empty tables retain table-level provenance."""
    return ([{'table': table['name'], 'pk': row['pk'], 'cells': row['sources']} for row in table['rows']]
            or [{'table': table['name'], 'pk': [], 'cells': {'$table': table['table_sources']}}])


def _join(operation, left, right):
    require(left['snapshot'] is not None and left['snapshot'] == right['snapshot'], 'SnapshotMismatch')
    pairs = operation['on']
    require(isinstance(pairs, list) and 1 <= len(pairs) <= 16)
    for pair in pairs:
        fields(pair, {'left', 'right'})
        require(pair['left'] in left['columns'] and pair['right'] in right['columns'], 'MissingColumn')
    require(len({(pair['left'], pair['right']) for pair in pairs}) == len(pairs))
    index = {}
    for row in right['rows']:
        key = tuple(row['values'][pair['right']] for pair in pairs)
        require(all(value.strip() for value in key), 'EmptyJoinKey')
        index.setdefault(key, []).append(row)
    rows, output_bytes = [], 0
    for first in left['rows']:
        key = tuple(first['values'][pair['left']] for pair in pairs)
        require(all(value.strip() for value in key), 'EmptyJoinKey')
        for second in index.get(key, []):
            require(len(rows) < MAX_ROWS, 'BudgetExceeded')
            values, sources = {}, {}
            for prefix, row in (('left.', first), ('right.', second)):
                values.update((prefix + column, value) for column, value in row['values'].items())
                sources.update((prefix + column, value) for column, value in row['sources'].items())
            joined = {'pk': first['pk'] + second['pk'], 'values': values, 'sources': sources}
            output_bytes += len(json.dumps(joined, ensure_ascii=False).encode('utf-8'))
            require(output_bytes <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
            rows.append(joined)
    columns = ['left.' + column for column in left['columns']] + ['right.' + column for column in right['columns']]
    source_unit = {'type': operation['type'], 'left_domain': left['domain'], 'right_domain': right['domain'],
                   'on': sorted((pair['left'], pair['right']) for pair in pairs)}
    return {'name': operation['id'], 'columns': columns,
            'domain': _domain(source_unit), 'source_unit': source_unit,
            'primary_key': ['left.' + col for col in left['primary_key']] + ['right.' + col for col in right['primary_key']],
            'rows': rows, 'complete': left['complete'] and right['complete'],
            'coverage': {'declaration': 'caller-declared/source-quoted; explicit literal key matching requires semantic review of the business relationship'},
            'warnings': left['warnings'] + right['warnings'], 'snapshot': left['snapshot'],
            'origin': left['origin'] + right['origin'],
            'table_sources': left['table_sources'] + right['table_sources'],
            'coverage_declarations': left['coverage_declarations'] + right['coverage_declarations']}


def _union(operation, inputs, *, output_limit=None):
    """Union only explicitly supplied read fragments; deduplication creates no completeness declaration or API identity."""
    limit = MAX_OUTPUT_BYTES if output_limit is None else min(output_limit, MAX_OUTPUT_BYTES)
    first = inputs[0]
    require(all(table['columns'] == first['columns']
                and table['primary_key'] == first['primary_key'] for table in inputs),
            'IncompatibleUnion')
    require(all(table['snapshot'] == first['snapshot'] for table in inputs), 'SnapshotMismatch')
    unit = {'type': 'union', 'parent_domains': sorted({table['domain'] for table in inputs}),
            'columns': first['columns'], 'primary_key': first['primary_key'], 'snapshot': first['snapshot']}
    result = {'name': operation['id'], 'columns': list(first['columns']),
              'primary_key': list(first['primary_key']), 'rows': [],
              'domain': _domain(unit), 'source_unit': unit, 'complete': False, 'coverage': None,
              'warnings': [], 'snapshot': first['snapshot'], 'origin': [],
              'table_sources': [], 'coverage_declarations': []}
    used = json_size(result, limit)

    def reserve(value):
        nonlocal used
        # Reserve array separators and check the remaining cumulative budget before every append.
        addition = json_size(value, limit - used) + 2
        require(used + addition <= limit, 'BudgetExceeded')
        used += addition

    metadata_seen = {key: set() for key in ('warnings', 'origin', 'table_sources', 'coverage_declarations')}
    indexed, cell_seen = {}, {}
    for table in inputs:
        for key, seen in metadata_seen.items():
            for entry in table[key]:
                digest = _domain(entry)
                if digest not in seen:
                    reserve(entry)
                    result[key].append(entry)
                    seen.add(digest)
        for original in table['rows']:
            pk = tuple(original['pk'])
            if pk in indexed:
                row = indexed[pk]
                require(row['values'] == original['values'], 'ConflictingPrimaryKey')
            else:
                require(len(result['rows']) < MAX_ROWS, 'BudgetExceeded')
                skeleton = {'pk': original['pk'], 'values': original['values'],
                            'sources': {column: [] for column in first['columns']}}
                reserve(skeleton)
                row = {'pk': list(original['pk']), 'values': dict(original['values']),
                       'sources': skeleton['sources']}
                indexed[pk] = row
                cell_seen[pk] = {column: set() for column in first['columns']}
                result['rows'].append(row)
            for column in first['columns']:
                seen = cell_seen[pk][column]
                for source in original['sources'][column]:
                    digest = _domain(source)
                    if digest not in seen:
                        reserve(source)
                        row['sources'][column].append(source)
                        seen.add(digest)
    return result


def _calculation(operation, tables):
    kind = operation['type']
    if kind == 'ratio':
        fields(operation, {'id', 'type', 'numerator', 'denominator'}, {'require_complete'})
        require(operation['numerator'] in tables and operation['denominator'] in tables)
        numerator, denominator = tables[operation['numerator']], tables[operation['denominator']]
        require(numerator['domain'] == denominator['domain']
                and numerator['primary_key'] == denominator['primary_key'],
                'IncompatibleRatio')
        top = {tuple(row['pk']) for row in numerator['rows']}
        bottom = {tuple(row['pk']) for row in denominator['rows']}
        require(top <= bottom, 'IncompatibleRatio')
        complete = _complete([numerator, denominator], operation)
        require(bool(bottom), 'ZeroDenominator')
        with localcontext() as context:
            context.prec = 40
            ratio = Decimal(len(top)) / Decimal(len(bottom))
        # Claim exactness only for finite decimals; represent repeating values as explicit fractions.
        fraction = Fraction(len(top), len(bottom))
        divisor = fraction.denominator
        for factor in (2, 5):
            while divisor % factor == 0:
                divisor //= factor
        exact = divisor == 1
        values = [format(ratio, 'f') if exact else f'{fraction.numerator}/{fraction.denominator}']
        return {'values': values, 'complete': complete, 'numerator': str(len(top)), 'denominator': str(len(bottom)),
                'formula': f'count_distinct_pk({operation["numerator"]}) / count_distinct_pk({operation["denominator"]})',
                'exact_decimal': exact, 'sources': _all_sources(numerator) + _all_sources(denominator),
                'coverage_declarations': numerator['coverage_declarations'] + denominator['coverage_declarations']}
    fields(operation, {'id', 'type', 'table'} | ({'by', 'member_columns'} if kind == 'group' else set()),
           {'require_complete'})
    require(operation['table'] in tables)
    table = tables[operation['table']]
    complete = _complete([table], operation)
    common = {'complete': complete, 'sources': _all_sources(table),
              'coverage_declarations': table['coverage_declarations']}
    if kind == 'count':
        return {**common, 'values': [str(len(table['rows']))], 'formula': f'count_distinct_pk({table["name"]})'}
    by, members = names(operation['by']), names(operation['member_columns'])
    require(set(by + members) <= set(table['columns']), 'MissingColumn')
    groups = {}
    for row in table['rows']:
        key = tuple(row['values'][column] for column in by)
        require(all(value.strip() for value in key + tuple(row['values'][column] for column in members)), 'EmptyValue')
        groups.setdefault(key, []).append({'pk': row['pk'], 'values': {column: row['values'][column] for column in members}})
    result = [{'key': dict(zip(by, key)), 'members': rows, 'count': str(len(rows))} for key, rows in sorted(groups.items())]
    return {**common, 'values': [json.dumps(group, ensure_ascii=False, sort_keys=True) for group in result],
            'groups': result, 'formula': f'group_by({", ".join(by)}); members_distinct_pk({table["name"]}); count_distinct_pk'}


def _build_evidence(job):
    """Validate one batch job and execute explicit bounded operations without environment reads or requests."""
    bounded(job)
    fields(job, {'schema', 'context', 'tables', 'contract', 'bindings', 'draft'}, {'operations'})
    require(job['schema'] == SCHEMA)
    context = validate_context(job['context'])
    specifications = job['tables']
    require(isinstance(specifications, list) and 1 <= len(specifications) <= 32)
    tables, calculations, versions = {}, {}, {}
    for specification in specifications:
        table = _extract_table(specification, context)
        require(table['name'] not in tables, 'DuplicateName')
        source = table['table_sources'][0]
        identity = tuple(source[key] for key in ('KnowledgeBaseId', 'Type', 'Id'))
        digest = source['content_sha256']
        require(identity not in versions or versions[identity] == digest, 'ConflictingSourceVersion')
        versions[identity] = digest
        tables[table['name']] = table
        require(len(json.dumps(tables, ensure_ascii=False).encode('utf-8')) <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
    operations = job.get('operations', [])
    require(isinstance(operations, list) and len(operations) <= MAX_OPERATIONS, 'BudgetExceeded')
    for operation in operations:
        require(isinstance(operation, dict))
        identifier, kind = string(operation.get('id')), operation.get('type')
        require(identifier not in tables and identifier not in calculations, 'DuplicateName')
        require(kind in ('select', 'join', 'map_description', 'union', 'group', 'count', 'ratio'))
        if kind == 'select':
            fields(operation, {'id', 'type', 'table', 'where'})
            require(operation['table'] in tables)
            table = tables[operation['table']]
            tables[identifier] = {**table, 'name': identifier, 'rows': select_rows(table, operation['where'])}
        elif kind in ('join', 'map_description'):
            fields(operation, {'id', 'type', 'left', 'right', 'on'})
            require(operation['left'] in tables and operation['right'] in tables)
            tables[identifier] = _join(operation, tables[operation['left']], tables[operation['right']])
        elif kind == 'union':
            fields(operation, {'id', 'type', 'tables'})
            references = names(operation['tables'], maximum=32)
            require(len(references) >= 2 and all(name in tables for name in references))
            # Accumulated tables/calculations share the output budget; reserve new keys and separators.
            current = json_size({'context': context, 'tables': tables, 'calculations': calculations}, MAX_OUTPUT_BYTES)
            remaining = MAX_OUTPUT_BYTES - current - json_size(identifier, MAX_OUTPUT_BYTES) - 4
            tables[identifier] = _union(operation, [tables[name] for name in references], output_limit=remaining)
        else:
            calculations[identifier] = _calculation(operation, tables)
        # Check cumulative output with provenance each step to bound repeated joins and sources.
        require(len(json.dumps({'tables': tables, 'calculations': calculations}, ensure_ascii=False).encode('utf-8'))
                <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
    result = {'context': context, 'tables': tables, 'calculations': calculations}
    require(len(json.dumps(result, ensure_ascii=False).encode('utf-8')) <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
    return result


def build_evidence(job):
    """Strict public entry point: convert invalid structures into safe exceptions without echoing input."""
    try:
        return _build_evidence(job)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        raise EvidenceError() from None
