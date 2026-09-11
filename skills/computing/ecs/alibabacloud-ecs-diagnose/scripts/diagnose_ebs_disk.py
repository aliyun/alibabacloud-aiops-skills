#!/usr/bin/env python3
"""
EBS Disk Performance Diagnosis Script (ECS Diagnostics Skill) — Python SDK FALLBACK

Implements the Disk Performance / IO Bottleneck workflow described in
references/ebs-disk-performance-diagnose-design.md using the Alibaba Cloud
Python Common SDK (popCode: ebs, version: 2021-07-30).

NOTE: The primary path for this scenario is the `aliyun` CLI (`aliyun ebs
create-diagnose-report` / `describe-diagnose-report` / `describe-lens-monitor-disks`,
provided by the aliyun-cli-ebs plugin). Use this script only when the plugin cannot
be installed. Unlike the CLI, the SDK does NOT read the aliyun CLI profile
(~/.aliyun/config.json); it needs env vars, ~/.alibabacloud/credentials, or an ECS
RAM role.

Usage:
    # Diagnose a disk
    python3 diagnose_ebs_disk.py --region cn-hangzhou --disk-id d-bp1xxxxxxxxxxxxx --yes

    # List disks (optionally filtered by the instance located in Phase 0)
    python3 diagnose_ebs_disk.py --region cn-hangzhou --list-disks --instance-id i-bp1xxxxxxxxxxxxx

Optional:
    --start-time 2026-08-20T00:00:00Z
    --end-time 2026-08-21T00:00:00Z
    --session-id <32-char lowercase hex>   (or env SKILL_SESSION_ID; auto-generated if absent)
    --yes                                  (skip interactive confirmation)

User-Agent:
    Every API call carries the unified skill User-Agent (injected via Config.user_agent):
    AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}

    The skill version is read from references/manifest.json. The caller MUST pass the
    same session-id already generated for the SKILL.md session (via --session-id or the
    SKILL_SESSION_ID environment variable) so that CLI and SDK calls share a consistent
    User-Agent. Random generation is only a last-resort fallback when no session-id is
    provided.
"""

import argparse
import json
import os
import time
import uuid
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredentialClient
from Tea.exceptions import TeaException

USER_AGENT_TEMPLATE = 'AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session_id} skill-version/{skill_version}'
SESSION_ID_ENV = 'SKILL_SESSION_ID'


def resolve_session_id(cli_value=None):
    """Resolve the session ID: CLI arg > environment variable > random 32-char hex."""
    session_id = cli_value or os.environ.get(SESSION_ID_ENV)
    if not session_id:
        session_id = uuid.uuid4().hex  # random 32-char lowercase hex
    return session_id


def resolve_skill_version():
    """Read the skill version from references/manifest.json."""
    manifest_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'references', 'manifest.json'
    )
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            return manifest.get('version', '1.0.0')
    except Exception:
        return '1.0.0'


class EBSDiskDiagnosis:
    """EBS Disk Performance Diagnosis Client"""

    def __init__(self, region_id, session_id):
        """Initialize the client with region and session ID."""
        self.region_id = region_id
        self.session_id = session_id

        # Initialize credential client (auto-discovers credentials)
        credential = CredentialClient()

        # Resolve skill version from manifest.json and build unified User-Agent.
        skill_version = resolve_skill_version()

        # Configure client; the unified skill User-Agent is injected here (MUST).
        # Note: RuntimeOptions does not accept a `headers` argument.
        config = open_api_models.Config(
            credential=credential,
            endpoint=f'ebs.{region_id}.aliyuncs.com',
            user_agent=USER_AGENT_TEMPLATE.format(
                session_id=session_id,
                skill_version=skill_version
            )
        )

        self.client = OpenApiClient(config)
        self.runtime_options = util_models.RuntimeOptions()

    def _call(self, action, queries):
        """Invoke an EBS RPC API. All query values MUST be strings."""
        params = open_api_models.Params(
            action=action,
            version='2021-07-30',
            protocol='HTTPS',
            method='POST',
            auth_type='AK',
            style='RPC'
        )
        request = open_api_models.OpenApiRequest(
            query={k: str(v) for k, v in queries.items() if v is not None}
        )
        response = self.client.call_api(params, request, self.runtime_options)
        return json.loads(response['body'].decode('utf-8'))

    def list_disks(self, max_results=20, instance_id=None):
        """List available disks in the region, optionally filtered by InstanceId."""
        try:
            result = self._call('DescribeLensMonitorDisks', {
                'RegionId': self.region_id,
                'MaxResults': max_results
            })
            disks = result.get('Data') or []

            # Filter by InstanceId when Phase 0 has already located the instance
            if instance_id:
                disks = [d for d in disks if d.get('InstanceId') == instance_id]

            return disks

        except TeaException as e:
            print(f"Error listing disks: {e.code} - {e.message}")
            return []

    def create_diagnosis(self, disk_id, start_time=None, end_time=None):
        """Create a performance diagnosis report."""
        queries = {
            'RegionId': self.region_id,
            'DiagnoseType': 'Performance',
            'ResourceType': 'Disk',
            'ResourceId': disk_id
        }

        # Add optional time range
        if start_time:
            queries['StartTime'] = start_time
        if end_time:
            queries['EndTime'] = end_time

        try:
            result = self._call('CreateDiagnoseReport', queries)
            return result.get('ReportId')

        except TeaException as e:
            print(f"Error creating diagnosis: {e.code} - {e.message}")
            if e.code in ('Forbidden.RAM', 'Forbidden.Unauthorized'):
                print("Permission denied. Follow the Permission Failure Handling process "
                      "in SKILL.md (references/ram-policies.md + ram-permission-diagnose skill).")
            elif e.code in ('InvalidDiskId.NotFound', 'NoSuchResource'):
                print(f"Disk {disk_id} does not exist in region {self.region_id}. "
                      "Verify it with: aliyun ecs describe-disks "
                      f"--biz-region-id {self.region_id} --disk-ids '[\"{disk_id}\"]'. "
                      "Do NOT substitute a different disk.")
            return None

    def get_diagnosis_result(self, report_id, max_wait=300):
        """Poll diagnosis status every 1 second until completion (5-minute timeout)."""
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < max_wait:
            poll_count += 1

            try:
                # List parameters use the flattened index form (ReportIds.1)
                result = self._call('DescribeDiagnoseReport', {
                    'RegionId': self.region_id,
                    'DiagnoseType': 'Performance',
                    'ReportIds.1': report_id
                })

                if result.get('Reports'):
                    report = result['Reports'][0]
                    status = report.get('Status')

                    print(f"[Poll #{poll_count}] Status: {status}")

                    if status == 'Success':
                        return report
                    elif status in ['Fail', 'TimeOut']:
                        print(f"Diagnosis failed with status: {status}")
                        return None

            except TeaException as e:
                print(f"Error polling diagnosis: {e.code} - {e.message}")
                return None

            time.sleep(1)

        print(f"Polling timeout after {max_wait} seconds. Check report later: ReportId={report_id}")
        return None

    def format_report(self, report):
        """Format diagnosis report for display."""
        output = f"""
{'='*80}
【Disk Performance Diagnostics】
{'='*80}

Disk ID:            {report.get('ResourceId', 'N/A')}
Report ID:          {report.get('ReportId', 'N/A')}
Diagnosis Type:     {report.get('DiagnoseType', 'N/A')}
Status:             ✅ Completed
Overall Assessment: {report.get('Severity', 'Unknown')}

"""

        events = report.get('Events', [])

        if not events:
            output += "✅ No performance issues detected. Disk is operating normally.\n"
        else:
            output += "Diagnosis Findings:\n"
            output += f"{'-'*80}\n"

            for idx, event in enumerate(events, 1):
                event_name = event.get('EventName', 'Unknown')
                severity = event.get('Severity', 'Unknown')
                description = event.get('Description', 'N/A')
                start_time = event.get('StartTime', 'N/A')

                output += f"\n[Issue {idx}] {event_name}\n"
                output += f"  Severity:     {severity}\n"
                output += f"  Description:  {description}\n"
                output += f"  First Seen:   {start_time}\n"

            output += f"\n{'-'*80}\n"
            output += "Recommendations:\n"
            output += f"{'-'*80}\n"

            for idx, event in enumerate(events, 1):
                event_name = event.get('EventName')
                recommend_action = event.get('RecommendAction', 'N/A')
                recommend_param = event.get('RecommendParam', '')

                output += f"\n{idx}. {event_name}\n"
                output += f"   Action: {recommend_action}\n"
                if recommend_param:
                    output += f"   Parameter: {recommend_param}\n"

        output += f"\n{'='*80}\n"
        return output


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='EBS Disk Performance Diagnosis Tool (ECS Diagnostics Skill)'
    )
    parser.add_argument(
        '--region',
        required=True,
        help='Region ID (e.g., cn-hangzhou)'
    )
    parser.add_argument(
        '--disk-id',
        help='Disk ID to diagnose (e.g., d-bp1xxxxxxxxxxxxx)'
    )
    parser.add_argument(
        '--instance-id',
        help='Filter disks by ECS instance ID in list mode (e.g., i-bp1xxxxxxxxxxxxx)'
    )
    parser.add_argument(
        '--start-time',
        help='Diagnosis start time in ISO 8601 format (e.g., 2026-08-20T00:00:00Z)'
    )
    parser.add_argument(
        '--end-time',
        help='Diagnosis end time in ISO 8601 format (e.g., 2026-08-21T00:00:00Z)'
    )
    parser.add_argument(
        '--list-disks',
        action='store_true',
        help='List available disks and exit'
    )
    parser.add_argument(
        '--session-id',
        help=f'Skill session ID (32-char lowercase hex); falls back to env {SESSION_ID_ENV}, '
             'then a randomly generated value'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip interactive confirmation (parameters must be confirmed with the user beforehand)'
    )

    args = parser.parse_args()

    session_id = resolve_session_id(args.session_id)

    # Initialize client
    print(f"Initializing EBS diagnosis client for region: {args.region}")
    diagnosis = EBSDiskDiagnosis(args.region, session_id)

    # List disks if requested
    if args.list_disks:
        if args.instance_id:
            print(f"\nQuerying disks attached to instance {args.instance_id}...")
        else:
            print("\nQuerying available disks...")
        disks = diagnosis.list_disks(instance_id=args.instance_id)

        if not disks:
            if args.instance_id:
                print(f"No disks found for instance {args.instance_id} in the region.")
            else:
                print("No disks found in the region.")
            return

        print(f"\nFound {len(disks)} disk(s):\n")
        print(f"{'DiskId':<25} {'Size (GB)':<12} {'Type':<20} {'Status':<12} {'Instance':<25}")
        print("-" * 100)

        for disk in disks:
            disk_id = disk.get('DiskId', 'N/A')
            disk_size = disk.get('DiskSize', 'N/A')
            disk_category = disk.get('DiskCategory', 'N/A')
            disk_status = disk.get('DiskStatus', 'N/A')
            disk_instance = disk.get('InstanceId', 'N/A')

            print(f"{disk_id:<25} {disk_size:<12} {disk_category:<20} {disk_status:<12} {disk_instance:<25}")

        return

    # Validate disk-id is provided
    if not args.disk_id:
        print("Error: --disk-id is required for diagnosis.")
        print("Use --list-disks (optionally with --instance-id) to see available disks.")
        return

    # Confirm parameters with user
    print("\n" + "="*80)
    print("Diagnosis Parameters:")
    print("="*80)
    print(f"  Region:     {args.region}")
    print(f"  Disk ID:    {args.disk_id}")
    print(f"  Start Time: {args.start_time or 'Last 12 hours (default)'}")
    print(f"  End Time:   {args.end_time or 'Now (default)'}")
    print("="*80)

    if not args.yes:
        response = input("\nProceed with diagnosis? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Diagnosis cancelled.")
            return

    # Create diagnosis
    print("\nStep 1: Creating diagnosis report...")
    report_id = diagnosis.create_diagnosis(
        args.disk_id,
        args.start_time,
        args.end_time
    )

    if not report_id:
        print("Failed to create diagnosis report.")
        return

    print(f"✅ Diagnosis created: {report_id}")

    # Poll for results
    print("\nStep 2: Waiting for diagnosis to complete...")
    report = diagnosis.get_diagnosis_result(report_id)

    if not report:
        print("Failed to retrieve diagnosis results.")
        return

    # Display results
    print("\nStep 3: Analysis complete!")
    print(diagnosis.format_report(report))


if __name__ == '__main__':
    main()
