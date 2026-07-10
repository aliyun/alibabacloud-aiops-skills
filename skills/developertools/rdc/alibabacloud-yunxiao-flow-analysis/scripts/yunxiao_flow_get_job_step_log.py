#!/usr/bin/env python3
"""
Yunxiao Flow Pipeline Job Step Log Query Tool

Usage:
 python yunxiao_flow_get_job_step_log.py --org-id <Organization ID> --pipeline-id <Pipeline ID> --pipeline-runid <Run ID> --job-id <Job ID> --step-index <Step Index> [--domain <Domain>] [--offset <Start Position>] [--limit <Log Length>] [--build-id <Build ID>]

Note: Token must be set via environment variable YUNXIAO_ACCESS_TOKEN

API Documentation: https://help.aliyun.com/zh/yunxiao/developer-reference/getpipelinejobsteplog
"""
import os
import platform
if platform.system() == 'Darwin':
    os.environ['SSL_CERT_DIR'] = '/private/etc/ssl/certs'   # Certificate directory
    os.environ['SSL_CERT_FILE'] = '/private/etc/ssl/cert.pem'   # Certificate file
    
import argparse
import json
import urllib.request
import urllib.error
from urllib.parse import urlencode


def mask_token(token):
    """Mask token for display, showing first 6 and last 6 characters with ******* in between"""
    if not token or len(token) <= 12:
        return '***'
    return f"{token[:6]}*******{token[-6:]}"


def validate_token_format(token):
    """Validate token format before transmission to prevent accidental credential leakage.
    Security: Only tokens matching the expected PAT format (pt- prefix) are accepted.
    """
    if not token or not isinstance(token, str):
        return False, 'Token is empty or not a string'
    if not token.startswith('pt-'):
        return False, 'Token must start with "pt-" prefix (Yunxiao Personal Access Token format)'
    if len(token) < 10:
        return False, 'Token is too short to be a valid PAT'
    return True, None


def get_job_step_log(org_id, pipeline_id, pipeline_runid, job_id, step_index, token, domain, offset=1, limit=100,
                     build_id=None):
    """
    Get pipeline job step log

    Args:
        org_id: Organization ID (required for central edition)
        pipeline_id: Pipeline ID
        pipeline_runid: Pipeline run ID
        job_id: Job ID
        step_index: Step index
        token: Personal access token
        domain: Domain name
        offset: Log start position (default 1)
        limit: Log length (default 100)
        build_id: Build ID (optional)

    Returns:
        dict: Response containing last, logs, more fields
    """
    # Build URL
    if "openapi-rdc.aliyuncs.com" == domain:
        # Central edition
        base_url = f"https://{domain}/oapi/v1/flow/organizations/{org_id}/pipelines/{pipeline_id}/pipelineRuns/{pipeline_runid}/jobs/{job_id}/step/log"
    else:
        # Region edition
        base_url = f"https://{domain}/oapi/v1/flow/pipelines/{pipeline_id}/pipelineRuns/{pipeline_runid}/jobs/{job_id}/step/log"

    # Build query parameters
    query_params = {
        'stepIndex': step_index,
        'offset': offset,
        'limit': limit
    }

    if build_id is not None:
        query_params['buildId'] = build_id

    url = f"{base_url}?{urlencode(query_params)}"

    # Create request
    req = urllib.request.Request(url)
    req.add_header('x-yunxiao-token', token)
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp = json.loads(response.read().decode('utf-8'))
            return resp

    except urllib.error.HTTPError as e:
        error_body = None
        if e.fp:
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                pass
        return {
            "error": f"HTTP {e.code}: {e.reason}",
            "body": error_body,
            "status_code": e.code
        }
    except urllib.error.URLError as e:
        return {"error": f"URL Error: {str(e)}"}
    except Exception as e:
        return {"error": f"Exception: {str(e)}"}


def get_full_step_log(org_id, pipeline_id, pipeline_runid, job_id, step_index, token, domain, build_id=None,
                      chunk_size=1000):
    """
    Get complete step log (auto-paginated)

    Args:
        org_id: Organization ID
        pipeline_id: Pipeline ID
        pipeline_runid: Pipeline run ID
        job_id: Job ID
        step_index: Step index
        token: Personal access token
        domain: Domain name
        build_id: Build ID (optional)
        chunk_size: Log lines per request (default 1000)

    Returns:
        dict: Containing complete_logs, last (last position), more (whether more available) fields
    """
    all_logs = []
    offset = 1
    has_more = True

    while has_more:
        resp = get_job_step_log(
            org_id=org_id,
            pipeline_id=pipeline_id,
            pipeline_runid=pipeline_runid,
            job_id=job_id,
            step_index=step_index,
            token=token,
            domain=domain,
            offset=offset,
            limit=chunk_size,
            build_id=build_id
        )

        if 'error' in resp:
            return {
                "error": resp['error'],
                "partial_logs": ''.join(all_logs),
                "last_offset": offset
            }

        logs = resp.get('logs', '')
        if logs:
            all_logs.append(logs)

        last = resp.get('last', offset)
        has_more = resp.get('more', False)

        if has_more:
            offset = last + 1

    return {
        "complete_logs": ''.join(all_logs),
        "last": last,
        "more": False
    }


def format_log_output(log_data, step_info=None):
    """
    Format log output

    Args:
        log_data: Log data
        step_info: Step information (optional)
    """
    output = []

    if step_info:
        output.append("=" * 60)
        output.append(f"Step: {step_info.get('stepName', 'Unknown')}")
        output.append(f"Status: {step_info.get('status', 'Unknown')}")
        output.append("=" * 60)

    if 'error' in log_data:
        output.append(f"❌ Failed to get log: {log_data['error']}")
        if log_data.get('body'):
            output.append(f"Response body: {log_data['body']}")
    else:
        output.append(f"✅ Log retrieved successfully")
        output.append(f"Last position: {log_data.get('last', 'N/A')}")
        output.append(f"Has more: {log_data.get('more', False)}")
        output.append("-" * 60)
        output.append("Log content:")
        output.append("-" * 60)
        output.append(log_data.get('logs', log_data.get('complete_logs', '(No log content)')))

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Yunxiao Flow Pipeline Job Step Log Query Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query single step log
  python yunxiao_flow_get_job_step_log.py --org-id 64c1c73fa4a9f6530c595e17 --pipeline-id 3734309 --pipeline-runid 109 --job-id 1 --step-index 1 --domain openapi-rdc.aliyuncs.com

  # Query complete log (auto-paginated)
  python yunxiao_flow_get_job_step_log.py --org-id xxx --pipeline-id xxx --pipeline-runid xxx --job-id xxx --step-index 1 --full-log

  # Region edition
  python yunxiao_flow_get_job_step_log.py --org-id xxx --pipeline-id xxx --pipeline-runid xxx --job-id xxx --step-index 1 --domain region-org.devops.aliyuncs.com
        """
    )

    parser.add_argument('--org-id', required=True, help='Organization ID (24 chars=central org, 32 chars=regional org)')
    parser.add_argument('--pipeline-id', required=True, help='Pipeline ID')
    parser.add_argument('--pipeline-runid', required=True, help='Pipeline run ID')
    parser.add_argument('--job-id', required=True, help='Job ID')
    parser.add_argument('--step-index', required=True, type=int, help='Step index')
    parser.add_argument('--domain', required=False, default=None, help='API domain (auto-inferred from org-id if not provided: 24 chars→openapi-rdc.aliyuncs.com; 32 chars must be explicitly specified)')
    parser.add_argument('--offset', type=int, default=1, help='Log start position (default: 1)')
    parser.add_argument('--limit', type=int, default=100, help='Log length (default: 100)')
    parser.add_argument('--build-id', type=int, help='Build ID (optional, obtained from GetPipelineJobSteps)')
    parser.add_argument('--full-log', action='store_true', help='Get complete log (auto-paginated)')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')

    args = parser.parse_args()

    # Security: Token is read exclusively from the environment variable to avoid
    # exposure in process listings (ps/top), shell history, and /proc/*/cmdline.
    # The token is transmitted over HTTPS only, via the x-yunxiao-token header.
    args.token = os.environ.get('YUNXIAO_ACCESS_TOKEN')  # nosec: intentional credential read
    if not args.token:
        parser.error('Environment variable YUNXIAO_ACCESS_TOKEN is not set. '
                     'Please set it before running this script: export YUNXIAO_ACCESS_TOKEN="pt-xxx"')

    # Security: Validate token format before any network transmission
    valid, err_msg = validate_token_format(args.token)
    if not valid:
        parser.error(f'Invalid token format: {err_msg}')

    # Auto-infer domain based on org-id length
    if not args.domain:
        if len(args.org_id) == 24:
            args.domain = 'openapi-rdc.aliyuncs.com'
        elif len(args.org_id) == 32:
            parser.error('Regional org (32-char org-id) must explicitly specify API domain via --domain')
        else:
            parser.error(f'Cannot infer domain from org-id length ({len(args.org_id)} chars), please specify --domain explicitly')

    print(f"🔍 Fetching log for pipeline {args.pipeline_id} run {args.pipeline_runid} job {args.job_id} step {args.step_index}... (token: {mask_token(args.token)})\n")

    if args.full_log:
        # Get complete log
        log_data = get_full_step_log(
            org_id=args.org_id,
            pipeline_id=args.pipeline_id,
            pipeline_runid=args.pipeline_runid,
            job_id=args.job_id,
            step_index=args.step_index,
            token=args.token,
            domain=args.domain,
            build_id=args.build_id
        )
    else:
        # Get single log
        log_data = get_job_step_log(
            org_id=args.org_id,
            pipeline_id=args.pipeline_id,
            pipeline_runid=args.pipeline_runid,
            job_id=args.job_id,
            step_index=args.step_index,
            token=args.token,
            domain=args.domain,
            offset=args.offset,
            limit=args.limit,
            build_id=args.build_id
        )

    if args.json:
        print(json.dumps(log_data, indent=2, ensure_ascii=False))
    else:
        print(format_log_output(log_data))

    return 0 if 'error' not in log_data else 1


if __name__ == '__main__':
    exit(main())