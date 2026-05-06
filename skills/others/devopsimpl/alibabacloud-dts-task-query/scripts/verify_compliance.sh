#!/bin/bash
# 验证 .qoder/specs/agent-skills-spec 合规性

echo "=== .qoder/specs/agent-skills-spec 合规性检查 ==="
echo ""

errors=0

# 检查 1: AI-Mode 声明
echo "1. 检查 AI-Mode 声明..."
if ! grep -q "aliyun config set --mode AI-Mode" SKILL.md; then
    echo "   ❌ 缺少 AI-Mode enable 命令"
    errors=$((errors + 1))
else
    echo "   ✅ AI-Mode enable"
fi

if ! grep -q "aliyun config set --set-user-agent" SKILL.md; then
    echo "   ❌ 缺少 set-user-agent 命令"
    errors=$((errors + 1))
else
    echo "   ✅ set-user-agent"
fi

if ! grep -q "aliyun config set --mode Disabled" SKILL.md; then
    echo "   ❌ 缺少 AI-Mode disable 命令"
    errors=$((errors + 1))
else
    echo "   ✅ AI-Mode disable"
fi

if ! grep -q "aliyun plugin update" SKILL.md; then
    echo "   ❌ 缺少 plugin update 命令"
    errors=$((errors + 1))
else
    echo "   ✅ plugin update"
fi

# 检查 2: 插件模式格式
echo ""
echo "2. 检查插件模式格式..."
if grep -q "DescribeDtsJobs" references/ram-policies.md && ! grep -q "NOT PascalCase" references/ram-policies.md; then
    echo "   ❌ 使用了 PascalCase 但未标注"
    errors=$((errors + 1))
else
    echo "   ✅ 插件模式格式正确"
fi

if grep -q "describe-dts-jobs" references/ram-policies.md; then
    echo "   ✅ 使用了 plugin mode (describe-dts-jobs)"
else
    echo "   ⚠️  未找到 plugin mode 格式 (但可能在其他位置)"
fi

# 检查 3: Description 触发语境
echo ""
echo "3. 检查 Description 触发语境..."
if grep -q "Use this skill when:" SKILL.md; then
    echo "   ✅ 有 'Use this skill when:' 触发语境"
else
    echo "   ❌ 缺少触发语境"
    errors=$((errors + 1))
fi

echo ""
if [ $errors -eq 0 ]; then
    echo "=== ✅ 所有检查通过 ==="
    exit 0
else
    echo "=== ❌ 有 $errors 项未通过 ==="
    exit 1
fi
