#!/usr/bin/env python3
"""
Yunxiao Flow Pipeline VM Deploy Order Details Query Tool

Usage:
 python yunxiao_flow_get_vm_deploy_order.py --org-id <Organization ID> --pipeline-id <Pipeline ID> --deploy-order-id <Deploy Order ID> [--domain <Domain>]

Note: Token must be set via environment variable YUNXIAO_ACCESS_TOKEN

API Documentation: https://help.aliyun.com/zh/yunxiao/developer-reference/getvmdeployorder
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


def get_vm_deploy_order(org_id, pipeline_id, deploy_order_id, token, domain):
    """
    Get VM deploy order details
    
    Args:
        org_id: Organization ID (required for central edition)
        pipeline_id: Pipeline ID
        deploy_order_id: Deploy order ID
        token: Personal access token
        domain: Domain name
    
    Returns:
        dict: Deploy order details
    """
    # Build URL
    if "openapi-rdc.aliyuncs.com" == domain:
        # Central edition
        url = f"https://{domain}/oapi/v1/flow/organizations/{org_id}/pipelines/{pipeline_id}/deploy/{deploy_order_id}"
    else:
        # Region edition
        url = f"https://{domain}/oapi/v1/flow/pipelines/{pipeline_id}/deploy/{deploy_order_id}"
    
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


def format_deploy_order_output(deploy_order):
    """
    Format deploy order details output
    
    Args:
        deploy_order: Deploy order details data
    """
    output = []
    
    if 'error' in deploy_order:
        output.append(f"❌ Failed to get deploy order details: {deploy_order['error']}")
        if deploy_order.get('body'):
            output.append(f"Response body: {deploy_order['body']}")
        return '\n'.join(output)
    
    # Basic information
    output.append("=" * 60)
    output.append("📋 Deploy Order Details")
    output.append("=" * 60)
    
    # Status information
    status = deploy_order.get('status', 'Unknown')
    status_emoji = {
        'Waiting': '⏸️ Paused',
        'Running': '🔄 Deploying',
        'Cancelled': '❌ Cancelled',
        'Success': '✅ Success'
    }.get(status, status)
    
    output.append(f"Deploy Order ID: {deploy_order.get('deployOrderId', 'N/A')}")
    output.append(f"Deploy status: {status_emoji}")
    output.append(f"Current batch: {deploy_order.get('currentBatch', 'N/A')}")
    output.append(f"Total batches: {deploy_order.get('totalBatch', 'N/A')}")
    
    # Time information
    create_time = deploy_order.get('createTime')
    update_time = deploy_order.get('updateTime')
    if create_time:
        from datetime import datetime
        create_dt = datetime.fromtimestamp(create_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        output.append(f"Create time: {create_dt}")
    if update_time:
        update_dt = datetime.fromtimestamp(update_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        output.append(f"Update time: {update_dt}")
    
    output.append(f"Creator: {deploy_order.get('creator', 'N/A')}")
    
    if deploy_order.get('exceptionCode'):
        output.append(f"Error code: {deploy_order.get('exceptionCode')}")
    
    # Executable operations
    actions = deploy_order.get('actions', [])
    if actions:
        output.append("-" * 60)
        output.append("🔧 Available operations:")
        for action in actions:
            action_type = action.get('type', 'Unknown')
            action_name = {
                'StopVMDeployOrder': 'Cancel deploy order',
                'ResumeVMDeployOrder': 'Resume deploy order'
            }.get(action_type, action_type)
            disabled = action.get('disable', False)
            status_str = '❌ No permission' if disabled else '✅ Available'
            output.append(f"  • {action_name}: {status_str}")
    
    # Deploy machine information
    deploy_machine_info = deploy_order.get('deployMachineInfo', {})
    if deploy_machine_info:
        output.append("-" * 60)
        output.append(f"🖥️ Host group ID: {deploy_machine_info.get('hostGroupId', 'N/A')}")
        output.append(f"Deploy batch: {deploy_machine_info.get('batchNum', 'N/A')}")
        
        deploy_machines = deploy_machine_info.get('deployMachines', [])
        if deploy_machines:
            output.append("-" * 60)
            output.append("📡 Deploy machine list:")
            output.append("-" * 60)
            
            # Table header
            output.append(f"{'IP':<20} {'Status':<12} {'Batch':<8} {'Machine SN':<20} {'Client Status':<10}")
            output.append("-" * 70)
            
            for machine in deploy_machines:
                ip = machine.get('ip', 'N/A')
                machine_status = machine.get('status', 'Unknown')
                batch_num = machine.get('batchNum', 'N/A')
                machine_sn = machine.get('machineSn', 'N/A')
                client_status = machine.get('clientStatus', 'N/A')
                
                # Status mapping
                status_map = {
                    'Success': '✅ Success',
                    'Pending': '⏳ Pending',
                    'Running': '🔄 Deploying',
                    'Cancelled': '❌ Cancelled',
                    'Queued': '⏸️ Queued',
                    'Failed': '❌ Failed',
                    'Skipped': '⏭️ Skipped'
                }
                machine_status_str = status_map.get(machine_status, machine_status)
                
                output.append(f"{ip:<20} {machine_status_str:<12} {batch_num:<8} {machine_sn:<20} {client_status:<10}")
            
            # Machine operations
            output.append("-" * 60)
            output.append("🔧 Machine available operations:")
            for machine in deploy_machines:
                ip = machine.get('ip', 'N/A')
                machine_actions = machine.get('actions', [])
                if machine_actions:
                    action_strs = []
                    for ma in machine_actions:
                        ma_type = ma.get('type', 'Unknown')
                        ma_name = {
                            'RetryVMDeployMachine': 'Retry',
                            'SkipVMDeployMachine': 'Skip',
                            'LogVMDeployMachine': 'View Log'
                        }.get(ma_type, ma_type)
                        disabled = ma.get('disable', False)
                        status_str = '❌' if disabled else '✅'
                        action_strs.append(f"{ma_name}({status_str})")
                    output.append(f"  {ip}: {', '.join(action_strs)}")
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Yunxiao Flow Pipeline VM Deploy Order Details Query Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Central edition: query deploy order details
  python yunxiao_flow_get_vm_deploy_order.py --org-id 5ebbc0228123212b59xxxxx --pipeline-id 123 --deploy-order-id 1111 --domain openapi-rdc.aliyuncs.com

  # Region edition: query deploy order details (org-id not required)
  python yunxiao_flow_get_vm_deploy_order.py --pipeline-id 123 --deploy-order-id 1111 --domain region-org.devops.aliyuncs.com

Status descriptions:
  Deploy status: Waiting(Paused), Running(Deploying), Cancelled(Cancelled), Success(Success)
  Machine status: Success(Success), Pending(Pending), Running(Deploying), Cancelled(Cancelled), Queued(Queued), Failed(Failed), Skipped(Skipped)
  Client status: ok(Normal), error(Connection failed)
        """
    )
    
    parser.add_argument('--org-id', required=True, help='Organization ID (24 chars=central org, 32 chars=regional org)')
    parser.add_argument('--pipeline-id', required=True, help='Pipeline ID')
    parser.add_argument('--deploy-order-id', required=True, help='Deploy order ID')
    parser.add_argument('--domain', required=False, default=None, help='API domain (auto-inferred from org-id if not provided: 24 chars→openapi-rdc.aliyuncs.com; 32 chars must be explicitly specified)')
    
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
    
    print(f"🔍 Fetching deploy order {args.deploy_order_id} details for pipeline {args.pipeline_id}... (token: {mask_token(args.token)})\n")
    
    deploy_order = get_vm_deploy_order(
        org_id=args.org_id,
        pipeline_id=args.pipeline_id,
        deploy_order_id=args.deploy_order_id,
        token=args.token,
        domain=args.domain
    )

    print(json.dumps(deploy_order, indent=2, ensure_ascii=False))

    
    return 0 if 'error' not in deploy_order else 1


if __name__ == '__main__':
    exit(main())