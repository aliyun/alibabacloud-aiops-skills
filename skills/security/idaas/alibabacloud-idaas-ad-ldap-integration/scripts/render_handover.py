#!/usr/bin/env python3
"""Render an evidence-only handover summary; never calls a cloud or directory."""
import argparse
import datetime
import json
import re
import sys


def scrub(item):
    if isinstance(item, dict):
        return {key: '[REDACTED]' if re.search('Password|Secret|Token|EncryptKey', key, re.I)
                else scrub(value) for key, value in item.items()}
    if isinstance(item, list):
        return [scrub(value) for value in item]
    return item


def render(evidence):
    if not isinstance(evidence, dict):
        raise ValueError('Evidence must be a JSON object')
    mode = evidence.get('mode')
    if mode not in ('live', 'offline', 'simulated'):
        raise ValueError('mode must be live, offline, or simulated')
    generated_at = datetime.datetime.now(datetime.timezone.utc)
    def value(key):
        item = evidence.get(key)
        if item is None or item == '':
            return '\u672a\u9a8c\u8bc1'
        if key in ('service_bind_login', 'mfa_policy_change') and isinstance(item, bool):
            return '\u5df2\u6267\u884c' if item else '\u672a\u6267\u884c'
        if not isinstance(item, str):
            return json.dumps(scrub(item), ensure_ascii=False)
        return item.replace('\n', ' ').replace('\r', ' ')
    for key in ('observed_at', 'login_observed_at'):
        if evidence.get(key):
            try:
                observed = datetime.datetime.fromisoformat(evidence[key].replace('Z', '+00:00'))
            except (ValueError, TypeError, AttributeError):
                raise ValueError(key + ' must be an actual ISO timestamp or omitted') from None
            if observed.utcoffset() is None:
                raise ValueError(key + ' requires an explicit timezone; omit it if unverified')
            if observed > generated_at:
                raise ValueError(key + ' is later than report generation; verify the source clock or omit it')
    factor_key = evidence.get('password_factor') or 'unverified'
    portal_key = evidence.get('full_portal') or 'unverified'
    factors = {'accepted': '\u5df2\u63a5\u53d7', 'rejected': '\u5df2\u62d2\u7edd', 'unverified': '\u672a\u9a8c\u8bc1'}
    portals = {'complete': '\u5df2\u5b8c\u6210', 'pending_mfa': '\u5f85 MFA\uff0c\u5b8c\u6574\u95e8\u6237\u672a\u9a8c\u8bc1', 'unverified': '\u672a\u9a8c\u8bc1'}
    if factor_key not in factors or portal_key not in portals:
        raise ValueError('Use documented password_factor/full_portal outcome values')
    factor, portal = factors[factor_key], portals[portal_key]
    if mode != 'live':
        factor = portal = '\u672a\u9a8c\u8bc1\uff08\u6ca1\u6709\u672c\u6b21\u771f\u5b9e\u767b\u5f55\u8bc1\u636e\uff09'
    elif factor_key != 'unverified' or portal_key != 'unverified':
        if portal_key in ('complete', 'pending_mfa') and factor_key != 'accepted':
            raise ValueError('A completed portal or pending MFA requires an accepted directory factor')
        if not evidence.get('login_observed_at') or not evidence.get('login_evidence'):
            raise ValueError('Live login outcomes require observation time and evidence reference')
    generated = generated_at.isoformat()
    lines = [
        '\u4ea4\u63a5\u62a5\u544a' + ('\uff08SIMULATED\uff0c\u4ec5\u6a21\u62df\u89c2\u6d4b\uff09' if mode == 'simulated' else ''),
        '\u62a5\u544a\u751f\u6210\u65f6\u95f4\uff08UTC\uff09: ' + generated + '\uff1b\u89c2\u5bdf\u65f6\u95f4: ' + value('observed_at'),
        'IdentityProviderId: ' + value('identity_provider_id'),
        '\u7aef\u70b9: ' + value('endpoint'),
        '\u540c\u6b65\u72b6\u6001: ' + value('synchronization_status'),
        '\u6620\u5c04\u72b6\u6001: ' + value('mapping_status'),
        '\u8ba4\u8bc1\u72b6\u6001: AuthnStatus=' + value('authn_status') + '\uff1b\u76ee\u5f55\u5bc6\u7801\u56e0\u5b50=' + factor + '\uff1b\u5b8c\u6574\u95e8\u6237=' + portal,
        '\u540e\u7eed\u771f\u5b9e\u9a8c\u8bc1\u8def\u5f84: \u4f7f\u7528\u5df2\u7ecf\u540c\u6b65\u7684\u4e13\u7528\u6d4b\u8bd5\u8d26\u6237\u53ca\u5176\u73b0\u6709\u76ee\u5f55\u5bc6\u7801\uff0c\u4ece\u8be5\u8eab\u4efd\u6e90\u7684\u72ec\u7acb\u767b\u5f55\u5165\u53e3\u6d4b\u8bd5\uff0c'
        '\u4e0d\u4f7f\u7528\u672c\u5730\u5bc6\u7801\u4e3b\u8868\u5355\u6216\u540c\u6b65\u670d\u52a1\u7ed1\u5b9a\u8d26\u6237\u3002\u5230\u8fbe #/TwoFactor \u4ec5\u8bc1\u660e\u76ee\u5f55\u5bc6\u7801\u56e0\u5b50\u901a\u8fc7\uff1b'
        '\u5230\u8fbe\u7528\u6237\u95e8\u6237\u624d\u8bc1\u660e\u5b8c\u6574\u767b\u5f55\u6210\u529f\uff0cMFA \u672a\u5b8c\u6210\u65f6\u5b8c\u6574\u95e8\u6237\u4ecd\u672a\u9a8c\u8bc1\uff1b\u4e0d\u5f97\u66f4\u6539 MFA \u7b56\u7565\u4ee5\u5b8c\u6210\u6d4b\u8bd5\u3002',
        '\u670d\u52a1\u7ed1\u5b9a\u8d26\u6237\u767b\u5f55: ' + value('service_bind_login') + '\uff1bMFA \u7b56\u7565\u53d8\u66f4: ' + value('mfa_policy_change'),
        '\u5220\u9664\u4e0e\u5b58\u6d3b\u5bf9\u8c61: \u5220\u9664 IDP \u4e0d\u7ea7\u8054\u5220\u9664\u5df2\u540c\u6b65\u8d26\u53f7\u4e0e\u7ec4\u7ec7\uff0c\u4e0d\u6784\u6210\u540c\u6b65\u56de\u6eda\u3002'
        '\u5b58\u6d3b\u5bf9\u8c61\u53ca\u6e90\u6807\u8bc6\u7b26: ' + value('surviving_source_identifiers'),
        '\u8bc1\u636e\u53ca\u64cd\u4f5c\u65e5\u5fd7: ' + value('evidence_reference'),
    ]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence_json', help='Noncredential evidence ledger under task outputs/')
    args = parser.parse_args()
    try:
        with open(args.evidence_json, encoding='utf-8') as source:
            report = render(json.load(source))
    except (OSError, ValueError, TypeError) as error:
        print('Handover generation failed: ' + str(error), file=sys.stderr)
        return 2
    print(report, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
