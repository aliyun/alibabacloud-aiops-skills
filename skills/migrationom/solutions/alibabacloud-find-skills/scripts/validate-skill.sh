#!/bin/bash

# Validation script for alibabacloud-find-skills

set -e

echo "========================================"
echo "  Skill Validation Script"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Aliyun CLI version
echo "Check 1: Aliyun CLI Version"
CLI_VERSION=$(aliyun version 2>/dev/null || echo "0.0.0")
REQUIRED_VERSION="3.3.1"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$CLI_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Aliyun CLI version: $CLI_VERSION (>= $REQUIRED_VERSION)"
else
    echo -e "${RED}❌ FAIL${NC} - Aliyun CLI version: $CLI_VERSION (< $REQUIRED_VERSION required)"
    exit 1
fi
echo ""

# Check 2: Plugin installation
echo "Check 2: agentexplorer Plugin"
if aliyun plugin list 2>/dev/null | grep -q "agentexplorer"; then
    PLUGIN_VERSION=$(aliyun plugin list 2>/dev/null | grep agentexplorer | awk '{print $2}')
    echo -e "${GREEN}✅ PASS${NC} - agentexplorer plugin installed (version: $PLUGIN_VERSION)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - agentexplorer plugin not installed"
    echo "Run: aliyun plugin install --names aliyun-cli-agentexplorer"
fi
echo ""

# Check 3: Skill structure
echo "Check 3: Skill File Structure"
FILES=(
    "SKILL.md"
    "references/ram-policies.md"
    "references/related-commands.md"
    "references/verification-method.md"
    "references/cli-installation-guide.md"
    "references/acceptance-criteria.md"
    "references/category-examples.md"
)

ALL_FILES_EXIST=true
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (missing)"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = true ]; then
    echo -e "${GREEN}✅ PASS${NC} - All required files present"
else
    echo -e "${RED}❌ FAIL${NC} - Some files missing"
    exit 1
fi
echo ""

# Check 4: SKILL.md frontmatter
echo "Check 4: SKILL.md Frontmatter"
if grep -q "^name: alibabacloud-find-skills" SKILL.md; then
    echo -e "${GREEN}✅${NC} name field present"
else
    echo -e "${RED}❌${NC} name field missing or incorrect"
    exit 1
fi

if grep -q "^description:" SKILL.md; then
    echo -e "${GREEN}✅${NC} description field present"
else
    echo -e "${RED}❌${NC} description field missing"
    exit 1
fi

echo -e "${GREEN}✅ PASS${NC} - SKILL.md frontmatter valid"
echo ""

# Check 5: Required sections
echo "Check 5: Required Sections in SKILL.md"
REQUIRED_SECTIONS=(
    "Scenario Description"
    "Installation"
    "Authentication"
    "RAM Policy"
    "Parameter Confirmation"
    "Core Workflow"
    "Success Verification"
    "Cleanup"
    "Best Practices"
    "Reference Documentation"
)

ALL_SECTIONS_PRESENT=true
for section in "${REQUIRED_SECTIONS[@]}"; do
    if grep -q "## $section" SKILL.md; then
        echo -e "${GREEN}✅${NC} $section"
    else
        echo -e "${RED}❌${NC} $section (missing)"
        ALL_SECTIONS_PRESENT=false
    fi
done

if [ "$ALL_SECTIONS_PRESENT" = true ]; then
    echo -e "${GREEN}✅ PASS${NC} - All required sections present"
else
    echo -e "${RED}❌ FAIL${NC} - Some sections missing"
    exit 1
fi
echo ""

# Check 6: CLI command validation
echo "Check 6: CLI Command Syntax"
CLI_COMMANDS=(
    "list-categories"
    "search-skills"
    "get-skill-content"
)

ALL_COMMANDS_VALID=true
for cmd in "${CLI_COMMANDS[@]}"; do
    if aliyun agentexplorer "$cmd" --help --user-agent AlibabaCloud-Agent-Skills >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} agentexplorer $cmd"
    else
        echo -e "${RED}❌${NC} agentexplorer $cmd (command not found or invalid)"
        ALL_COMMANDS_VALID=false
    fi
done

if [ "$ALL_COMMANDS_VALID" = true ]; then
    echo -e "${GREEN}✅ PASS${NC} - All CLI commands valid"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Some CLI commands may be invalid (plugin issue?)"
fi
echo ""

# Check 7: User-agent flag presence
echo "Check 7: User-Agent Flag in Commands"
USER_AGENT_COUNT=$(grep -o "user-agent AlibabaCloud-Agent-Skills" SKILL.md | wc -l)
if [ "$USER_AGENT_COUNT" -gt 20 ]; then
    echo -e "${GREEN}✅ PASS${NC} - Found $USER_AGENT_COUNT instances of user-agent flag"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Only found $USER_AGENT_COUNT instances of user-agent flag"
fi
echo ""

# Check 8: Permission failure handling block
echo "Check 8: Permission Failure Handling Block"
if grep -q "Permission Failure Handling" SKILL.md; then
    echo -e "${GREEN}✅ PASS${NC} - Permission failure handling block present in SKILL.md"
else
    echo -e "${RED}❌ FAIL${NC} - Permission failure handling block missing"
    exit 1
fi

if grep -q "Permission Failure Handling" references/ram-policies.md; then
    echo -e "${GREEN}✅ PASS${NC} - Permission failure handling instructions in ram-policies.md"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Permission failure handling may be incomplete in ram-policies.md"
fi
echo ""

# Summary
echo "========================================"
echo -e "${GREEN}  All Validations Passed!${NC}"
echo "========================================"
echo ""
echo "The skill is ready for use. To test:"
echo "  1. Configure credentials: aliyun configure"
echo "  2. Test commands manually or run references/verification-method.md tests"
echo ""
