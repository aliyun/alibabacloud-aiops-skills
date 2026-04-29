#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Validation Script

This script validates that the ICP Filing Success Query skill is properly configured.
"""

import os
import sys


def check_file_exists(filepath: str) -> bool:
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {filepath}")
    return exists


def validate_skill_structure():
    """Validate the skill directory structure."""
    print("\n" + "=" * 60)
    print("Validating Skill Structure")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    required_files = [
        'SKILL.md',
        'scripts/query_icp_filing.py',
        'references/ram-policies.md',
        'references/related-commands.md',
        'references/verification-method.md',
        'references/cli-installation-guide.md',
        'references/common-sdk-usage.md',
        'references/error-handling.md',
        'references/acceptance-criteria.md'
    ]

    all_exist = True
    for file in required_files:
        filepath = os.path.join(base_dir, file)
        if not check_file_exists(filepath):
            all_exist = False

    return all_exist


def validate_imports():
    """Validate that required Python modules can be imported."""
    print("\n" + "=" * 60)
    print("Validating Python Dependencies")
    print("=" * 60)

    required_modules = [
        'alibabacloud_credentials',
        'alibabacloud_tea_openapi',
        'alibabacloud_tea_util'
    ]

    all_imported = True
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module} (not installed)")
            all_imported = False

    if not all_imported:
        print("\nTo install missing dependencies:")
        print("  pip install -r scripts/requirements.txt")

    return all_imported


def validate_skill_metadata():
    """Validate SKILL.md metadata."""
    print("\n" + "=" * 60)
    print("Validating SKILL.md Metadata")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_file = os.path.join(base_dir, 'SKILL.md')

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for frontmatter
        if content.startswith('---'):
            print("  ✓ YAML frontmatter present")

            # Check for required fields
            has_name = 'name:' in content[:500]
            has_description = 'description:' in content[:500]

            print(f"  {'✓' if has_name else '✗'} name field")
            print(f"  {'✓' if has_description else '✗'} description field")

            return has_name and has_description
        else:
            print("  ✗ Missing YAML frontmatter")
            return False

    except Exception as e:
        print(f"  ✗ Error reading SKILL.md: {e}")
        return False


def validate_credentials():
    """Validate that credentials can be loaded."""
    print("\n" + "=" * 60)
    print("Validating Credentials Configuration")
    print("=" * 60)

    try:
        from alibabacloud_credentials.client import Client as CredentialClient

        # Try to create credential client
        credential = CredentialClient()
        print("  ✓ CredentialClient created successfully")
        print("  ✓ Credentials are configured")
        return True

    except ImportError:
        print("  ✗ Cannot import CredentialClient")
        print("    Install: pip install -r scripts/requirements.txt")
        return False

    except Exception as e:
        print("  ⚠ Credentials may not be configured")
        print(f"    Error: {str(e)}")
        print("\n  Configure credentials using one of these methods:")
        print("    1. Environment variables: ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        print("    2. Credentials file: ~/.alibabacloud/credentials")
        print("    3. ECS RAM role (when running on ECS)")
        return False


def main():
    """Main validation function."""
    print("=" * 60)
    print("ICP Filing Success Query Skill Validation")
    print("=" * 60)

    results = []

    # Validate skill structure
    results.append(("Skill Structure", validate_skill_structure()))

    # Validate Python dependencies
    results.append(("Python Dependencies", validate_imports()))

    # Validate SKILL.md metadata
    results.append(("SKILL.md Metadata", validate_skill_metadata()))

    # Validate credentials (optional, may not be configured in dev)
    results.append(("Credentials", validate_credentials()))

    # Print summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {name}: {status}")
        if result:
            passed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n✓ All validation checks passed!")
        print("  The skill is ready to use.")
        return 0
    else:
        print("\n⚠ Some validation checks failed.")
        print("  Please address the issues above before using the skill.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
