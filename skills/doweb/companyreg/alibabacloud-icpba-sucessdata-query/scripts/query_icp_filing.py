#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ICP Filing Success Data Query Script

This script queries ICP filing success data including entity information,
website information, APP information, and risk information.

Usage:
    python3 query_icp_filing.py

Requirements:
    - alibabacloud-credentials
    - alibabacloud-tea-openapi

Installation:
    pip install -r scripts/requirements.txt
"""

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
import json
import sys


def create_client() -> OpenApiClient:
    """
    Create an OpenAPI client with credential authentication.

    Returns:
        OpenApiClient: Configured API client

    Raises:
        Exception: If credential configuration fails
    """
    try:
        credential = CredentialClient()

        config = open_api_models.Config(
            credential=credential,
            endpoint='companyreg.aliyuncs.com',
            region_id='cn-hangzhou',
            user_agent='AlibabaCloud-Agent-Skills/alibabacloud-icpba-sucessdata-query'
        )

        return OpenApiClient(config)
    except Exception as e:
        print(f"Error creating client: {str(e)}")
        print("\nPlease ensure your Alibaba Cloud credentials are configured.")
        print("You can configure credentials using one of these methods:")
        print("  1. Environment variables: ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        print("  2. Credentials file: ~/.alibabacloud/credentials")
        print("  3. ECS RAM role (when running on Alibaba Cloud ECS)")
        raise


_ALLOWED_CALLERS = frozenset({'skill'})


def query_success_icp_data(caller: str = 'skill') -> dict:
    """
    Query ICP filing success data including entity, website, app, and risk information.

    Args:
        caller: Caller identifier (fixed value: 'skill')

    Returns:
        dict: Filing success data response

    Raises:
        ValueError: If caller is not in the allowed whitelist
        Exception: If API call fails
    """
    if not isinstance(caller, str) or caller not in _ALLOWED_CALLERS:
        raise ValueError(
            f"Invalid caller: {caller!r}. Allowed values: {sorted(_ALLOWED_CALLERS)}"
        )

    client = create_client()

    params = open_api_models.Params(
        action='QuerySuccessIcpData',
        version='2026-04-23',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='formData',
        body_type='json'
    )

    queries = {
        'Caller': caller
    }

    request = open_api_models.OpenApiRequest(
        query=queries
    )

    runtime = util_models.RuntimeOptions(
        connect_timeout=5000,
        read_timeout=10000
    )

    try:
        response = client.call_api(params, request, runtime)
        return response.get('body', {})
    except Exception as e:
        error_msg = str(e)

        # Provide helpful error messages
        if 'InvalidAccessKeyId' in error_msg:
            print("Error: Invalid Access Key ID")
            print("Please verify your credentials are correct")
        elif 'Forbidden' in error_msg:
            print("Error: Permission Denied")
            print("Please ensure you have the required RAM permission: beian:QuerySuccessIcpData")
            print("See references/ram-policies.md for more details")
        elif 'InvalidParameter' in error_msg:
            print("Error: Invalid Parameter")
            print(f"Please check the parameter values. Caller must be 'skill'")
        else:
            print(f"Error querying ICP filing data: {error_msg}")

        raise


def print_entity_info(ba_data: dict):
    """
    Print entity information.

    Args:
        ba_data: Filing data object
    """
    print(f"ICP Number: {ba_data.get('IcpNumber')}")
    print(f"Entity Name: {ba_data.get('OrganizersName')}")
    print(f"Entity Type: {ba_data.get('OrganizersNature')}")
    print(f"Responsible Person: {ba_data.get('ResponsiblePersonName')}")


def print_website_info(ba_data: dict):
    """
    Print website information.

    Args:
        ba_data: Filing data object
    """
    websites = ba_data.get('WebsiteList', [])
    print(f"\nWebsites: {len(websites)}")

    for idx, site in enumerate(websites, 1):
        print(f"\n  Website {idx}:")
        print(f"    Name: {site.get('SiteName')}")
        print(f"    Record Number: {site.get('SiteRecordNum')}")
        print(f"    Domains: {', '.join(site.get('DomainList', []))}")
        print(f"    Responsible Person: {site.get('ResponsiblePersonName')}")


def print_app_info(ba_data: dict):
    """
    Print APP information.

    Args:
        ba_data: Filing data object
    """
    apps = ba_data.get('AppList', [])

    if apps:
        print(f"\nAPPs: {len(apps)}")

        for idx, app in enumerate(apps, 1):
            print(f"\n  APP {idx}:")
            print(f"    Name: {app.get('AppName')}")
            print(f"    Record Number: {app.get('AppRecordNum')}")
            print(f"    Domains: {', '.join(app.get('DomainList', []))}")
            print(f"    Responsible Person: {app.get('ResponsiblePersonName')}")
    else:
        print("\nAPPs: No APPs registered")


def print_risk_info(ba_data: dict):
    """
    Print risk information.

    Args:
        ba_data: Filing data object
    """
    risks = ba_data.get('RiskList', [])

    if risks:
        print(f"\n⚠️  RISKS DETECTED: {len(risks)} risk(s)")

        for idx, risk in enumerate(risks, 1):
            print(f"\n  Risk {idx}:")
            print(f"    Deadline: {risk.get('DeadLine')}")

            for detail_idx, detail in enumerate(risk.get('RiskDetailList', []), 1):
                print(f"\n    Risk Detail {detail_idx}:")
                print(f"      Source: {detail.get('RiskSource')}")

                suggestions = detail.get('rectifySuggest', [])
                if suggestions:
                    print(f"      Rectification Suggestions:")
                    for suggest in suggestions:
                        # Remove HTML tags for cleaner display
                        import re
                        clean_suggest = re.sub('<[^<]+?>', '', suggest)
                        print(f"        - {clean_suggest}")
    else:
        print("\n✓ No risks detected")


def main():
    """
    Main function to query and display ICP filing success data.
    """
    print("=" * 70)
    print("ICP Filing Success Data Query")
    print("=" * 70)

    try:
        # Query filing data
        print("\nQuerying ICP filing data...")
        result = query_success_icp_data(caller='skill')

        # Check if query was successful
        if not result.get('Success'):
            print("\n✗ Query failed or returned no data")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return 1

        print(f"✓ Query successful (RequestId: {result.get('RequestId')})")

        # Get filing records
        ba_list = result.get('BaSuccessDataWithRiskList', [])

        if not ba_list:
            print("\nNo filing records found.")
            return 0

        print(f"\n{'=' * 70}")
        print(f"Total Filing Records: {len(ba_list)}")
        print('=' * 70)

        # Process each filing record
        for idx, ba_data in enumerate(ba_list, 1):
            print(f"\n{'=' * 70}")
            print(f"Filing Record {idx}")
            print('=' * 70)

            # Print entity information
            print_entity_info(ba_data)

            # Print website information
            print_website_info(ba_data)

            # Print APP information
            print_app_info(ba_data)

            # Print risk information
            print_risk_info(ba_data)

        print(f"\n{'=' * 70}")
        print("Query completed successfully!")
        print('=' * 70)

        return 0

    except KeyboardInterrupt:
        print("\n\nQuery interrupted by user")
        return 130

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
