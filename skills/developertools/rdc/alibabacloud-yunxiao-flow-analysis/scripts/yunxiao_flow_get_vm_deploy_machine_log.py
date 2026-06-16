#!/usr/bin/env python3
"""
Yunxiao Flow VM Deploy Machine Log Query Tool

Usage:
 python yunxiao_flow_get_vm_deploy_machine_log.py --org-id <Organization ID> --pipeline-id <Pipeline ID> --deploy-order-id <Deploy Order ID> --machine-sn <Machine SN> --token <Access Token> [--domain <Domain>]

API Documentation: https://help.aliyun.com/zh/yunxiao/developer-reference/getvmdeploymachinelog
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


def mask_token(token):
    """Mask token for display, showing first 6 and last 6 characters with ******* in between"""
    if not token or len(token) <= 12:
        return '***'
    return f"{token[:6]}*******{token[-6:]}"


def get_vm_deploy_machine_log(org_id, pipeline_id, deploy_order_id, machine_sn, token, domain):
    """
    Get VM deploy machine log
    
    Args:
        org_id: Organization ID (required for central edition)
        pipeline_id: Pipeline ID
        deploy_order_id: Deploy order ID
        machine_sn: Machine SN (serial number)
        token: Personal access token
        domain: Domain name
    
    Returns:
        dict: Containing deploy log, time, region and other information
    """
    # Build URL
    if "openapi-rdc.aliyuncs.com" == domain:
        # Central edition
        url = f"https://{domain}/oapi/v1/flow/organizations/{org_id}/pipelines/{pipeline_id}/deploy/{deploy_order_id}/machine/{machine_sn}/log"
    else:
        # Region edition
        url = f"https://{domain}/oapi/v1/flow/pipelines/{pipeline_id}/deploy/{deploy_order_id}/machine/{machine_sn}/log"
    
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


def format_machine_log_output(log_data, machine_sn=None):
    """
    Format machine deploy log output
    
    Args:
        log_data: Log data
        machine_sn: Machine SN (optional)
    """
    output = []
    
    if 'error' in log_data:
        output.append(f"❌ Failed to get machine deploy log: {log_data['error']}")
        if log_data.get('body'):
            output.append(f"Response body: {log_data['body']}")
        return '\n'.join(output)
    
    # Basic information
    output.append("=" * 60)
    output.append("📋 Machine Deploy Log")
    output.append("=" * 60)
    
    if machine_sn:
        output.append(f"Machine SN: {machine_sn}")
    
    # Deploy region
    output.append(f"Deploy region: {log_data.get('aliyunRegion', 'N/A')}")
    
    # Time information
    deploy_begin_time = log_data.get('deployBeginTime')
    deploy_end_time = log_data.get('deployEndTime')
    
    if deploy_begin_time:
        try:
            # Try to parse timestamp (may be milliseconds or seconds)
            begin_ts = int(deploy_begin_time)
            if begin_ts > 10000000000:  # Millisecond timestamp
                from datetime import datetime
                begin_dt = datetime.fromtimestamp(begin_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                output.append(f"Deploy start time: {begin_dt}")
            else:
                output.append(f"Deploy start time: {deploy_begin_time}")
        except Exception:
            output.append(f"Deploy start time: {deploy_begin_time}")
    
    if deploy_end_time:
        try:
            end_ts = int(deploy_end_time)
            if end_ts > 10000000000:
                from datetime import datetime
                end_dt = datetime.fromtimestamp(end_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                output.append(f"Deploy end time: {end_dt}")
            else:
                output.append(f"Deploy end time: {deploy_end_time}")
        except Exception:
            output.append(f"Deploy end time: {deploy_end_time}")
    
    # Log path
    log_path = log_data.get('deployLogPath')
    if log_path:
        output.append(f"Log path: {log_path}")
    
    # Deploy log
    deploy_log = log_data.get('deployLog')
    if deploy_log:
        output.append("-" * 60)
        output.append("📝 Deploy log content:")
        output.append("-" * 60)
        output.append(deploy_log)
    else:
        output.append("-" * 60)
        output.append("⚠️ No deploy log content")
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Yunxiao Flow VM Deploy Machine Log Query Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Central edition: query machine deploy log
  python yunxiao_flow_get_vm_deploy_machine_log.py --org-id 5ebbc0228123212b59xxxxx --pipeline-id 123 --deploy-order-id 1111 --machine-sn asssssssxsx --token pt-xxx --domain openapi-rdc.aliyuncs.com

  # Region edition: query machine deploy log (org-id not required)
  python yunxiao_flow_get_vm_deploy_machine_log.py --pipeline-id 123 --deploy-order-id 1111 --machine-sn asssssssxsx --token pt-xxx --domain region-org.devops.aliyuncs.com

Usage:
  1. First use yunxiao_flow_get_vm_deploy_order.py to get deploy order details
  2. Find the failed machine's machineSn from the returned results
  3. Use this tool to query the deploy log for that machine
        """
    )
    
    parser.add_argument('--org-id', required=True, help='Organization ID (24 chars=central org, 32 chars=regional org)')
    parser.add_argument('--pipeline-id', required=True, help='Pipeline ID')
    parser.add_argument('--deploy-order-id', required=True, help='Deploy order ID')
    parser.add_argument('--machine-sn', required=True, help='Machine SN (serial number, obtained from deploy order details)')
    parser.add_argument('--token', required=False, default=None, help='Personal access token (can also be set via environment variable YUNXIAO_ACCESS_TOKEN)')
    parser.add_argument('--domain', required=False, default=None, help='API domain (auto-inferred from org-id if not provided: 24 chars→openapi-rdc.aliyuncs.com; 32 chars must be explicitly specified)')
    
    args = parser.parse_args()
    
    # Get token: prioritize command line argument, then environment variable
    if not args.token:
        args.token = os.environ.get('YUNXIAO_ACCESS_TOKEN')
    if not args.token:
        parser.error('Must provide --token argument or set environment variable YUNXIAO_ACCESS_TOKEN')
    
    # Auto-infer domain based on org-id length
    if not args.domain:
        if len(args.org_id) == 24:
            args.domain = 'openapi-rdc.aliyuncs.com'
        elif len(args.org_id) == 32:
            parser.error('Regional org (32-char org-id) must explicitly specify API domain via --domain')
        else:
            parser.error(f'Cannot infer domain from org-id length ({len(args.org_id)} chars), please specify --domain explicitly')
    
    print(f"🔍 Fetching deploy log for pipeline {args.pipeline_id} deploy order {args.deploy_order_id} machine {args.machine_sn}... (token: {mask_token(args.token)})\n")
    
    log_data = get_vm_deploy_machine_log(
        org_id=args.org_id,
        pipeline_id=args.pipeline_id,
        deploy_order_id=args.deploy_order_id,
        machine_sn=args.machine_sn,
        token=args.token,
        domain=args.domain
    )

    print(json.dumps(log_data, indent=2, ensure_ascii=False))
    
    return 0 if 'error' not in log_data else 1


if __name__ == '__main__':
    exit(main())