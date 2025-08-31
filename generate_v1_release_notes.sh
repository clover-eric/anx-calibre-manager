#!/bin/bash

# Get repository URL
REPO_URL="https://github.com/ptbsare/anx-calibre-manager"

echo "# Release Notes for v1.0.0"
echo ""

# Function to add section if commits exist
add_section() {
    local title="$1"
    local emoji="$2"
    local pattern="$3"
    local commits=$(git log --pretty=format:"- %s ([%h]($REPO_URL/commit/%H))" 40495ce..8b85754 --grep="$pattern" 2>/dev/null)
    
    if [ -n "$commits" ]; then
        echo "## ${emoji} ${title}"
        echo "$commits"
        echo ""
    fi
}

# Add sections for different commit types
add_section "新功能 (Features)" "🚀" "^feat"
add_section "修复 (Bug Fixes)" "🐛" "^fix"
add_section "文档 (Documentation)" "📚" "^docs"
add_section "性能优化 (Performance)" "⚡" "^perf"
add_section "样式 (Styles)" "💄" "^style"
add_section "重构 (Refactoring)" "♻️" "^refactor"
add_section "测试 (Tests)" "🧪" "^test"
add_section "构建系统 (Build System)" "🔧" "^build"
add_section "持续集成 (CI)" "👷" "^ci"
add_section "维护 (Maintenance)" "🔨" "^chore"

# Add other changes (commits that don't match conventional patterns)
OTHER_COMMITS=$(git log --pretty=format:"- %s ([%h]($REPO_URL/commit/%H))" 40495ce..8b85754 --invert-grep --grep="^feat\|^fix\|^docs\|^perf\|^style\|^refactor\|^test\|^build\|^ci\|^chore" 2>/dev/null)
if [ -n "$OTHER_COMMITS" ]; then
    echo "## 📦 其他变更 (Other Changes)"
    echo "$OTHER_COMMITS"
    echo ""
fi

# Add footer
echo "---"
echo "**完整变更日志**: $REPO_URL/compare/40495ce...v1.0.0"