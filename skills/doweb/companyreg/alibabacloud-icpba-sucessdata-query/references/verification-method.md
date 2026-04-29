# Verification Method for ICP Filing Success Query

## Overview

This document describes the methods to verify that the ICP filing success data query operation completed successfully.

## Verification Steps

### Step 1: Check API Response Status

Verify the API call returned successfully:

```python
result = query_success_icp_data(caller='skill')

# Check if Success field is true
assert result.get('Success') == True, "Query failed: Success is not True"
print("✓ API call successful")
```

### Step 2: Verify Response Structure

Check that the response contains the expected data structure:

```python
# Check RequestId exists
assert 'RequestId' in result, "Missing RequestId in response"
print(f"✓ Request ID: {result['RequestId']}")

# Check BaSuccessDataWithRiskList exists
assert 'BaSuccessDataWithRiskList' in result, "Missing BaSuccessDataWithRiskList"
ba_list = result['BaSuccessDataWithRiskList']
print(f"✓ Found {len(ba_list)} filing record(s)")
```

### Step 3: Validate Filing Record Data

For each filing record, verify the required fields:

```python
for idx, ba_data in enumerate(ba_list, 1):
    print(f"\nVerifying Filing Record {idx}...")

    # Check ICP Number
    assert 'IcpNumber' in ba_data and ba_data['IcpNumber'], \
        f"Missing or empty IcpNumber in record {idx}"
    print(f"  ✓ ICP Number: {ba_data['IcpNumber']}")

    # Check Entity Name
    assert 'OrganizersName' in ba_data and ba_data['OrganizersName'], \
        f"Missing or empty OrganizersName in record {idx}"
    print(f"  ✓ Entity Name: {ba_data['OrganizersName']}")

    # Check Entity Type
    assert 'OrganizersNature' in ba_data and ba_data['OrganizersNature'], \
        f"Missing or empty OrganizersNature in record {idx}"
    print(f"  ✓ Entity Type: {ba_data['OrganizersNature']}")

    # Check Responsible Person
    assert 'ResponsiblePersonName' in ba_data and ba_data['ResponsiblePersonName'], \
        f"Missing or empty ResponsiblePersonName in record {idx}"
    print(f"  ✓ Responsible Person: {ba_data['ResponsiblePersonName']}")
```

### Step 4: Validate Website Data

Verify website information is present and valid:

```python
    # Check WebsiteList exists
    assert 'WebsiteList' in ba_data, f"Missing WebsiteList in record {idx}"
    websites = ba_data['WebsiteList']
    print(f"  ✓ Websites: {len(websites)}")

    for site_idx, site in enumerate(websites, 1):
        # Check required website fields
        assert 'SiteRecordNum' in site, f"Missing SiteRecordNum in website {site_idx}"
        assert 'SiteName' in site, f"Missing SiteName in website {site_idx}"
        assert 'DomainList' in site, f"Missing DomainList in website {site_idx}"
        assert 'ResponsiblePersonName' in site, f"Missing ResponsiblePersonName in website {site_idx}"

        # Verify DomainList is not empty
        assert len(site['DomainList']) > 0, f"Empty DomainList in website {site_idx}"

        print(f"    ✓ Website {site_idx}: {site['SiteName']} ({site['SiteRecordNum']})")
        print(f"      Domains: {', '.join(site['DomainList'])}")
```

### Step 5: Validate APP Data (if present)

Check APP information if available:

```python
    # Check AppList exists
    assert 'AppList' in ba_data, f"Missing AppList in record {idx}"
    apps = ba_data['AppList']

    if len(apps) > 0:
        print(f"  ✓ APPs: {len(apps)}")

        for app_idx, app in enumerate(apps, 1):
            # Check required app fields
            assert 'AppRecordNum' in app, f"Missing AppRecordNum in app {app_idx}"
            assert 'AppName' in app, f"Missing AppName in app {app_idx}"
            assert 'DomainList' in app, f"Missing DomainList in app {app_idx}"
            assert 'ResponsiblePersonName' in app, f"Missing ResponsiblePersonName in app {app_idx}"

            print(f"    ✓ APP {app_idx}: {app['AppName']} ({app['AppRecordNum']})")
            print(f"      Domains: {', '.join(app['DomainList'])}")
    else:
        print(f"  ℹ No APPs in this filing record")
```

### Step 6: Validate Risk Data (if present)

Check risk information and warnings:

```python
    # Check RiskList exists
    assert 'RiskList' in ba_data, f"Missing RiskList in record {idx}"
    risks = ba_data['RiskList']

    if len(risks) > 0:
        print(f"  ⚠️ Risks: {len(risks)}")

        for risk_idx, risk in enumerate(risks, 1):
            # Check required risk fields
            assert 'DeadLine' in risk, f"Missing DeadLine in risk {risk_idx}"
            assert 'RiskDetailList' in risk, f"Missing RiskDetailList in risk {risk_idx}"

            print(f"    ⚠️ Risk {risk_idx}:")
            print(f"      Deadline: {risk['DeadLine']}")

            for detail_idx, detail in enumerate(risk['RiskDetailList'], 1):
                assert 'RiskSource' in detail, f"Missing RiskSource in risk detail {detail_idx}"
                assert 'rectifySuggest' in detail, f"Missing rectifySuggest in risk detail {detail_idx}"

                print(f"      Source: {detail['RiskSource']}")
                print(f"      Suggestions: {len(detail['rectifySuggest'])} item(s)")
    else:
        print(f"  ✓ No risks detected")
```

## Complete Verification Script

Here's a complete verification script you can use:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from query_icp_filing import query_success_icp_data

def verify_filing_query():
    """
    Comprehensive verification of ICP filing query results.
    """
    print("Starting ICP Filing Query Verification...")
    print("=" * 60)

    try:
        # Step 1: Execute query
        print("\n[Step 1] Executing query...")
        result = query_success_icp_data(caller='skill')

        # Step 2: Check API response status
        print("\n[Step 2] Verifying API response status...")
        assert result.get('Success') == True, "Query failed: Success is not True"
        print("✓ API call successful")

        # Step 3: Verify response structure
        print("\n[Step 3] Verifying response structure...")
        assert 'RequestId' in result, "Missing RequestId in response"
        print(f"✓ Request ID: {result['RequestId']}")

        assert 'BaSuccessDataWithRiskList' in result, "Missing BaSuccessDataWithRiskList"
        ba_list = result['BaSuccessDataWithRiskList']
        print(f"✓ Found {len(ba_list)} filing record(s)")

        # Step 4-6: Validate each filing record
        for idx, ba_data in enumerate(ba_list, 1):
            print(f"\n[Step 4-6] Verifying Filing Record {idx}...")

            # Validate entity information
            assert 'IcpNumber' in ba_data and ba_data['IcpNumber'], \
                f"Missing or empty IcpNumber in record {idx}"
            print(f"  ✓ ICP Number: {ba_data['IcpNumber']}")

            assert 'OrganizersName' in ba_data and ba_data['OrganizersName'], \
                f"Missing or empty OrganizersName in record {idx}"
            print(f"  ✓ Entity Name: {ba_data['OrganizersName']}")

            assert 'OrganizersNature' in ba_data and ba_data['OrganizersNature'], \
                f"Missing or empty OrganizersNature in record {idx}"
            print(f"  ✓ Entity Type: {ba_data['OrganizersNature']}")

            assert 'ResponsiblePersonName' in ba_data and ba_data['ResponsiblePersonName'], \
                f"Missing or empty ResponsiblePersonName in record {idx}"
            print(f"  ✓ Responsible Person: {ba_data['ResponsiblePersonName']}")

            # Validate website data
            assert 'WebsiteList' in ba_data, f"Missing WebsiteList in record {idx}"
            websites = ba_data['WebsiteList']
            print(f"  ✓ Websites: {len(websites)}")

            for site_idx, site in enumerate(websites, 1):
                assert all(k in site for k in ['SiteRecordNum', 'SiteName', 'DomainList', 'ResponsiblePersonName']), \
                    f"Missing required fields in website {site_idx}"
                assert len(site['DomainList']) > 0, f"Empty DomainList in website {site_idx}"
                print(f"    ✓ Website {site_idx}: {site['SiteName']} ({site['SiteRecordNum']})")

            # Validate APP data
            assert 'AppList' in ba_data, f"Missing AppList in record {idx}"
            apps = ba_data['AppList']

            if len(apps) > 0:
                print(f"  ✓ APPs: {len(apps)}")
                for app_idx, app in enumerate(apps, 1):
                    assert all(k in app for k in ['AppRecordNum', 'AppName', 'DomainList', 'ResponsiblePersonName']), \
                        f"Missing required fields in app {app_idx}"
                    print(f"    ✓ APP {app_idx}: {app['AppName']} ({app['AppRecordNum']})")
            else:
                print(f"  ℹ No APPs in this filing record")

            # Validate risk data
            assert 'RiskList' in ba_data, f"Missing RiskList in record {idx}"
            risks = ba_data['RiskList']

            if len(risks) > 0:
                print(f"  ⚠️ Risks: {len(risks)}")
                for risk_idx, risk in enumerate(risks, 1):
                    assert all(k in risk for k in ['DeadLine', 'RiskDetailList']), \
                        f"Missing required fields in risk {risk_idx}"
                    print(f"    ⚠️ Risk {risk_idx}: Deadline {risk['DeadLine']}")
            else:
                print(f"  ✓ No risks detected")

        print("\n" + "=" * 60)
        print("✓ All verification checks passed!")
        return True

    except AssertionError as e:
        print(f"\n✗ Verification failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        return False

if __name__ == '__main__':
    success = verify_filing_query()
    sys.exit(0 if success else 1)
```

## Expected Output

A successful verification should produce output similar to:

```
Starting ICP Filing Query Verification...
============================================================

[Step 1] Executing query...

[Step 2] Verifying API response status...
✓ API call successful

[Step 3] Verifying response structure...
✓ Request ID: 79732597-AB14-1341-9131-D94F48D1AFD7
✓ Found 1 filing record(s)

[Step 4-6] Verifying Filing Record 1...
  ✓ ICP Number: 粤ICP测50000001号
  ✓ Entity Name: 深圳市星澜美容有限公司变更
  ✓ Entity Type: 企业
  ✓ Responsible Person: 于婷
  ✓ Websites: 2
    ✓ Website 1: 于婷广东 (粤ICP测50000001号-1)
    ✓ Website 2: 920企业变更网站001 (津ICP备2023010907号-1)
  ℹ No APPs in this filing record
  ⚠️ Risks: 1
    ⚠️ Risk 1: Deadline 2026年04月28日0点

============================================================
✓ All verification checks passed!
```

## Common Verification Failures

### Failure 1: Success is False

**Symptom**: `Success` field in response is `false`

**Possible Causes**:
- Invalid caller parameter
- API service error
- Account issues

**Solution**: Check the error message in the response and verify account status

### Failure 2: Empty BaSuccessDataWithRiskList

**Symptom**: `BaSuccessDataWithRiskList` is empty array

**Possible Causes**:
- No filing records exist for this account
- Filings are not in "success" state

**Solution**: Verify filing status in Beian console

### Failure 3: Missing Required Fields

**Symptom**: AssertionError about missing fields

**Possible Causes**:
- API response format changed
- Partial data in response

**Solution**: Review the API documentation and update verification logic

### Failure 4: Permission Error

**Symptom**: Exception about unauthorized access

**Possible Causes**:
- Missing RAM permissions
- Invalid credentials

**Solution**: Check RAM policies and credential configuration

## Automated Testing

You can integrate this verification into your CI/CD pipeline:

```bash
#!/bin/bash
# run_verification.sh

echo "Running ICP Filing Query Verification..."

python3 verify_filing_query.py

if [ $? -eq 0 ]; then
    echo "Verification PASSED"
    exit 0
else
    echo "Verification FAILED"
    exit 1
fi
```

## Monitoring and Alerts

For production systems, consider setting up monitoring:

1. **Success Rate Monitoring**: Track the percentage of successful queries
2. **Response Time**: Monitor API response latency
3. **Risk Alerts**: Set up alerts when new risks are detected
4. **Data Completeness**: Verify all expected fields are present

## Related Documentation

- [API Response Codes](https://www.alibabacloud.com/help/doc-detail/error-codes)
- [Beian Service Status](https://status.alibabacloud.com/)
- RAM Permission Troubleshooting: references/ram-policies.md
