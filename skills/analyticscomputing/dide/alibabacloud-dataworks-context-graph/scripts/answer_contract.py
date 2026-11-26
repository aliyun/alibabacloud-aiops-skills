"""Check answers against a pre-retrieval field contract, repair twice at most, and render every field."""

import argparse
import copy
import datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import re
import sys

from evidence_tables import (EvidenceError, MAX_OUTPUT_BYTES, build_evidence, fields,
                             json_size, load_job, require, select_rows, string)

RESULT_SCHEMA = 'context-graph-answer-report-v1'


def _value(value, kind):
    """Normalize exact decimal/fraction comparisons only; preserve original IDs, text, and dates."""
    require(isinstance(value, str) and len(value) <= 1024 * 1024)
    if not value.strip():
        raise ValueError
    if kind == 'number':
        if re.fullmatch(r'[+-]?[0-9]+/[1-9][0-9]*', value) and len(value) <= 256:
            return Fraction(value)
        if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)', value) or len(value) > 256:
            raise ValueError
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise ValueError from None
        if not number.is_finite():
            raise ValueError
        return Fraction(number)
    if kind == 'date':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            raise ValueError
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise ValueError from None
    return value


def _expected(slot, binding, evidence, source_limit):
    unknown, values, sources, calculation = [], [], [], None
    complete, coverage_declarations = False, []
    source_bytes = 0

    def add_sources(records):
        nonlocal source_bytes
        for record in records:
            source_bytes += json_size(record, source_limit - source_bytes)
            sources.append(record)

    if 'calculation' in binding:
        fields(binding, {'calculation'})
        identifier = string(binding['calculation'])
        require(identifier in evidence['calculations'], 'MissingCalculation')
        result = evidence['calculations'][identifier]
        values = result['values']
        add_sources(result['sources'])
        complete = result['complete']
        coverage_declarations = result['coverage_declarations']
        # Keep sources only in slots; calculation does not duplicate them, and expected already contains groups.
        calculation = {key: result[key] for key in ('formula', 'numerator', 'denominator', 'exact_decimal') if key in result}
        calculation['kind'] = 'group' if 'groups' in result else 'ratio' if 'denominator' in result else 'count'
        if slot['cardinality'] == 'one':
            if not values:
                unknown.append('no_rows')
            elif len(values) > 1:
                unknown.append('ambiguous_groups')
                values = []
    else:
        fields(binding, {'table', 'column'}, {'where'})
        require(isinstance(binding['table'], str) and isinstance(binding['column'], str))
        where = binding.get('where', {})
        require(isinstance(where, dict) and len(where) <= 128)
        require(all(isinstance(value, str) for value in where.values()))
        require(binding['table'] in evidence['tables'], 'MissingTable')
        table = evidence['tables'][binding['table']]
        complete = table['complete']
        coverage_declarations = table['coverage_declarations']
        if binding['column'] not in table['columns']:
            unknown.append('missing_column')
        else:
            # A missing filter column is an evidence gap, not proof of no matching rows.
            if not set(where) <= set(table['columns']):
                unknown.append('missing_filter_column')
                rows = []
            else:
                rows = select_rows(table, where)
            if not rows and not unknown:
                if slot['cardinality'] == 'set' and complete:
                    add_sources([{'table': table['name'], 'pk': [], 'cells': {'$table': table['table_sources']}}])
                else:
                    unknown.append('no_rows')
            elif slot['cardinality'] == 'one' and len(rows) != 1:
                unknown.append('ambiguous_rows')
                add_sources({'table': table['name'], 'pk': row['pk'],
                             'cells': {binding['column']: row['sources'][binding['column']]}} for row in rows)
            else:
                for row in rows:
                    value = row['values'][binding['column']]
                    if not value.strip():
                        unknown.append('empty_value')
                    else:
                        values.append(value)
                    add_sources([{'table': table['name'], 'pk': row['pk'],
                                  'cells': {binding['column']: row['sources'][binding['column']]}}])
        if not sources:
            add_sources([{'table': table['name'], 'pk': [], 'cells': {'$table': table['table_sources']}}])
    valid, seen = [], set()
    for value in values:
        try:
            key = _value(value, slot['format'])
        except ValueError:
            unknown.append('invalid_evidence_format')
            continue
        if key not in seen:
            seen.add(key)
            valid.append(value)
    if evidence['context']['snapshot'] is None and slot['completeness'] == 'complete':
        unknown.append('unknown_snapshot')
    if slot['completeness'] == 'complete' and not complete:
        unknown.append('incomplete_evidence')
    return {'expected': valid, 'sources': sources, 'unknown': sorted(set(unknown)),
            'evidence_complete': complete, 'calculation': calculation,
            'coverage_declarations': coverage_declarations}


def _compare(slot, draft):
    expected = {_value(value, slot['format']): value for value in slot['expected']}
    actual, invalid = {}, []
    for value in draft:
        try:
            key = _value(value, slot['format'])
            actual.setdefault(key, value)
        except ValueError:
            invalid.append(value)
    missing = [value for key, value in expected.items() if key not in actual]
    extra = [value for key, value in actual.items() if key not in expected] + invalid
    if slot['cardinality'] == 'one' and len(draft) > 1:
        extra = list(dict.fromkeys(extra + draft[1:]))
    return {**slot, 'missing': missing, 'extra': extra, 'invalid_draft_values': invalid,
            'resolved': not slot['unknown'] and not missing and not extra}


def _issues(slots, extra_slots):
    return ([{'slot': slot['name'], 'missing': slot['missing'], 'extra': slot['extra'], 'unknown': slot['unknown']}
             for slot in slots if slot['missing'] or slot['extra'] or slot['unknown']]
            + [{'extra_slot': name} for name in extra_slots])


def evaluate_job(job, repair_rounds=0):
    """Public entry point: recompute the original job and return diagnostics; never trust a self-declared pass."""
    require(type(repair_rounds) is int and 0 <= repair_rounds <= 2)
    evidence = build_evidence(job)
    contract = job['contract']
    fields(contract, {'question_id', 'question_type', 'required_slots'})
    string(contract['question_id'])
    require(contract['question_type'] in ('basic', 'association', 'multihop', 'aggregate', 'boundary'))
    require(isinstance(contract['required_slots'], list) and 1 <= len(contract['required_slots']) <= 128)
    definitions, seen = [], set()
    for item in contract['required_slots']:
        fields(item, {'name', 'label', 'cardinality', 'format'}, {'completeness'})
        for key in ('name', 'label'):
            string(item[key])
        require(item['name'] not in seen, 'DuplicateSlot')
        seen.add(item['name'])
        require(item['cardinality'] in ('one', 'set') and item['format'] in ('text', 'id', 'date', 'number'))
        completeness = item.get('completeness', 'complete' if item['cardinality'] == 'set' else 'observed')
        require(completeness in ('complete', 'observed'))
        definitions.append({**item, 'completeness': completeness})
    bindings, draft = job['bindings'], copy.deepcopy(job['draft'])
    require(isinstance(bindings, dict) and set(bindings) == seen, 'InvalidBindings')
    require(isinstance(draft, dict) and len(draft) <= 256)
    for key, values in draft.items():
        string(key)
        require(isinstance(values, list) and len(values) <= 10000)
        require(all(isinstance(value, str) and len(value) <= 1024 * 1024 for value in values))
    for definition in definitions:
        draft.setdefault(definition['name'], [])
    extras = sorted(set(draft) - seen)
    base = {'schema': RESULT_SCHEMA, 'status': 'needs_repair', 'question_id': contract['question_id'],
            'question_type': contract['question_type'], 'scope': evidence['context'],
            'slot_count': len(definitions), 'addressed_count': len(definitions), 'resolved_count': len(definitions),
            'slots': [], 'draft': draft, 'extra_slots': extras, 'initial_issues': [], 'history': [],
            'warnings': [warning for table in evidence['tables'].values() for warning in table['warnings']],
            'limitation': 'Checks only supplied responses, actual-column bindings, and exact values; labels, business meaning, and natural-language correctness still require semantic review.'}
    used = json_size(base, MAX_OUTPUT_BYTES)
    slots, checked = [], []
    for definition in definitions:
        remaining = MAX_OUTPUT_BYTES - used
        slot = {**definition, **_expected(definition, bindings[definition['name']], evidence, remaining)}
        checked_slot = _compare(slot, draft[slot['name']])
        used += json_size(checked_slot, remaining) + 2
        require(used <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
        slots.append(slot)
        checked.append(checked_slot)
    initial_issues = _issues(checked, extras)
    # Charge all repeated sections to the same budget, including initial/history/draft.
    used += json_size(initial_issues, MAX_OUTPUT_BYTES - used) - 2
    history = []
    for current_round in range(1, repair_rounds + 1):
        before = copy.deepcopy(draft)
        # Use only definite traceable batch values; do not query, guess, or borrow evidence for unknowns.
        draft = {slot['name']: list(slot['expected']) for slot in slots}
        if draft == before:
            break
        checked = [_compare(slot, draft[slot['name']]) for slot in slots]
        entry = {'round': current_round, 'issues_before': _issues(
            [_compare(slot, before.get(slot['name'], [])) for slot in slots], sorted(set(before) - seen)),
            'issues_after': _issues(checked, [])}
        json_size({**base, 'slots': checked, 'draft': draft, 'extra_slots': [],
                   'initial_issues': initial_issues, 'history': history + [entry]}, MAX_OUTPUT_BYTES)
        history.append(entry)
    extras = sorted(set(draft) - seen)
    checked = [_compare(slot, draft[slot['name']]) for slot in slots]
    if any(slot['unknown'] for slot in checked):
        status = 'incomplete'
    elif extras or any(not slot['resolved'] for slot in checked):
        status = 'needs_repair'
    elif any(not slot['evidence_complete'] for slot in checked):
        status = 'observed'
    else:
        status = 'ready'
    result = {**base, 'status': status,
              'resolved_count': sum(slot['resolved'] for slot in checked),
              'slots': checked, 'draft': draft, 'extra_slots': extras,
              'initial_issues': initial_issues, 'history': history}
    json_size(result, MAX_OUTPUT_BYTES)
    return result


def _literal(value):
    """Escape all external fields as literal text so Markdown/HTML cannot become links or instructions."""
    original = str(value).replace('\r\n', '\n').replace('\r', '\n')
    escapes = {'&': '&amp;', '<': '&lt;', '>': '&gt;'}
    for char in '\\`*_[]()#!|~@':
        escapes[char] = '&#' + str(ord(char)) + ';'
    text = ''.join(escapes.get(char, '&#' + str(ord(char)) + ';' if ord(char) < 32 else char)
                   for char in original)
    if text.startswith(('-', '+')):
        text = '&#' + str(ord(text[0])) + ';' + text[1:]
    text = re.sub(r'(?i)\b(https?|ftp):', r'\1&#58;', text)
    text = re.sub(r'(?i)\bwww\.', 'www&#46;', text)
    return re.sub(r'^(\d+)\.(?= )', r'\1&#46;', text)


UNKNOWN_LABELS = {
    'missing_column': 'Required field was not returned', 'missing_filter_column': 'Filter field was not returned',
    'no_rows': 'No matching subject was returned', 'ambiguous_rows': 'Multiple subjects match; clarification is required',
    'ambiguous_groups': 'Multiple groups match; clarification is required', 'empty_value': 'Original field is empty',
    'invalid_evidence_format': 'Original value has an invalid format', 'unknown_snapshot': 'Evidence version is unknown',
    'incomplete_evidence': 'Current evidence cannot establish complete scope',
}


def _render_markdown(report, include_diagnostics=False):
    """Render business fields and concise sources by default; show full audit only in explicit diagnostics mode."""
    require(isinstance(report, dict) and report.get('schema') == RESULT_SCHEMA)
    require(type(include_diagnostics) is bool)
    status = {'ready': 'Field checks complete', 'needs_repair': 'Draft still needs repair',
              'incomplete': 'Evidence gaps remain', 'observed': 'Only the read scope is confirmed'}[report['status']]
    lines = ['# Answer', '', f'{status}. Addressed {report["addressed_count"]}/{report["slot_count"]} items; facts resolved {report["resolved_count"]}/{report["slot_count"]} items.', '',
             'Scope: evidence supplied in this batch. Completeness relies on source-supported caller declarations; live access and complete business reality are not verified.', '']
    if report['scope']['snapshot'] is None:
        lines.extend(['Version was not returned; only original values read in this batch are confirmed, not the current state.', ''])
    if include_diagnostics:
        lines.extend(['Audit scope: ' + _literal(json.dumps(report['scope'], ensure_ascii=False, sort_keys=True)), '',
                      'Completeness: caller-declared/source-quoted; SHA256 establishes consistency with supplied content only.', ''])
    for slot in report['slots']:
        label = slot['label'] + (' (' + slot['name'] + ')' if include_diagnostics else '')
        lines.extend(['## ' + _literal(label), '',
                      'Scope: ' + ('A complete set is required.' if slot['completeness'] == 'complete' else 'Read scope only.'), ''])
        if slot['expected']:
            groups = ([json.loads(value) for value in slot['expected']]
                      if (slot.get('calculation') or {}).get('kind') == 'group' else None)
            if groups is not None and len(groups) == len(slot['expected']):
                for group in groups:
                    label = '; '.join(column + '=' + value for column, value in group['key'].items())
                    lines.append('- Group: ' + _literal(label) + '; member count: ' + _literal(group['count']))
                    for member in group['members']:
                        values = '; '.join(column + '=' + value for column, value in member['values'].items())
                        lines.append('  - ' + _literal(values) + '; original primary key ' + _literal(json.dumps(member['pk'], ensure_ascii=False)))
            else:
                lines.extend('- ' + _literal(value) for value in slot['expected'])
        else:
            lines.append('- Empty set (declared complete scope).' if not slot['unknown'] and slot['cardinality'] == 'set'
                         else '- Unknown: no definite evidence value.')
        if slot['unknown']:
            lines.extend(['', 'Evidence gaps: ' + '; '.join(UNKNOWN_LABELS.get(code, 'Verification is still required') for code in slot['unknown']) + '.'])
        if slot['missing'] or slot['extra']:
            lines.extend(['', 'Draft gaps: missing ' + str(len(slot['missing'])) + ' items; unsupported values: ' + str(len(slot['extra'])) + ' items; repair is required.'])
        calculation = slot.get('calculation')
        if calculation:
            if 'denominator' in calculation:
                lines.extend(['', 'Numerator: ' + _literal(calculation['numerator']) + '; denominator: ' + _literal(calculation['denominator'])
                              + '; ratio = numerator / denominator.'])
            if include_diagnostics:
                lines.extend(['', 'Formula: ' + _literal(calculation['formula'])])
        if include_diagnostics and slot['coverage_declarations']:
            lines.extend(['', 'Source-supported caller completeness declarations:'])
            lines.extend('- ' + _literal(json.dumps(coverage, ensure_ascii=False, sort_keys=True)) for coverage in slot['coverage_declarations'])
        lines.extend(['', 'Sources:', ''])
        source_lines = set()
        for record in slot['sources']:
            for column, sources in record['cells'].items():
                for source in sources:
                    if include_diagnostics:
                        line = json.dumps({**source, 'table': record['table'], 'pk': record['pk']}, ensure_ascii=False, sort_keys=True)
                    else:
                        title = source.get('Title') or record['table']
                        if column == '$table':
                            line = title + '; table-level source'
                        else:
                            key = json.dumps(source.get('primary_key', record['pk']), ensure_ascii=False)
                            line = (title + '; original primary key ' + key + '; content line ' + str(source['line_start'])
                                    + '; column ' + source['column'])
                    if line not in source_lines:
                        source_lines.add(line)
                        lines.append('- ' + _literal(line))
        if not source_lines:
            lines.append('- No locatable source row was returned.')
        lines.append('')
    if report['warnings']:
        lines.extend(['Service warnings:', ''])
        for warning in report['warnings']:
            value = json.dumps(warning, ensure_ascii=False, sort_keys=True) if include_diagnostics else warning.get('Message', warning['Code'])
            lines.append('- ' + _literal(value))
        lines.append('')
    lines.append(report['limitation'])
    rendered = '\n'.join(lines) + '\n'
    require(len(rendered.encode('utf-8')) <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
    return rendered


def render_markdown(job, repair_rounds=0, include_diagnostics=False):
    """Accept only the original job, recompute before rendering, and reject invented pass reports."""
    return _render_markdown(evaluate_job(job, repair_rounds), include_diagnostics)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise EvidenceError('InvalidArguments')


def main(argv=None):
    parser = SafeParser(description='Validate and fully render a local answer job without API calls.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--repair-rounds', type=int, choices=(0, 1, 2), default=0)
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    parser.add_argument('--include-diagnostics', action='store_true', help='Explicitly include complete audit fields in Markdown.')
    try:
        arguments = parser.parse_args(argv)
        report = evaluate_job(load_job(arguments.input), arguments.repair_rounds)
        if arguments.format == 'json':
            json_size(report, MAX_OUTPUT_BYTES - 1, indent=2)
        output = _render_markdown(report, arguments.include_diagnostics) if arguments.format == 'markdown' else json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        require(len(output.encode('utf-8')) <= MAX_OUTPUT_BYTES, 'BudgetExceeded')
        sys.stdout.write(output)
        return {'ready': 0, 'needs_repair': 3, 'incomplete': 4, 'observed': 5}[report['status']]
    except (EvidenceError, OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        # reason_code is a fixed module enum; never echo exception contents or input.
        reason = error.code if isinstance(error, EvidenceError) else 'InvalidJob'
        message = {'ZeroDenominator': 'The denominator is zero; the ratio is undefined.',
                   'IncompleteAggregation': 'Evidence scope is incomplete; complete-scope calculation is unconfirmed.',
                   'SnapshotMismatch': 'The evidence snapshot is unknown or inconsistent.'}.get(reason, 'The job is invalid or exceeds safe limits.')
        sys.stdout.write(json.dumps({'schema': 'context-graph-answer-error-v1', 'error': 'InvalidOrUnsafeJob',
                                    'reason_code': reason, 'message': message}, ensure_ascii=False) + '\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())
