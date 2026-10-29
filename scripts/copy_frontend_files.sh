#!/usr/bin/env bash
# scripts/copy_frontend_files.sh
# 从老 frontend 目录拷贝不需要拆分的文件到新 frontend
set -e
cd "$(dirname "$0")/.."

OLD_DIR="${1:-frontend.bak}"     # 默认备份目录名
NEW_DIR="frontend"

if [ ! -d "$OLD_DIR" ]; then
    echo "❌ 未找到老目录: $OLD_DIR"
    echo "   用法: bash scripts/copy_frontend_files.sh <老目录>"
    echo "   例如: bash scripts/copy_frontend_files.sh frontend.bak"
    exit 1
fi

if [ ! -d "$NEW_DIR" ]; then
    echo "❌ 未找到新目录: $NEW_DIR"
    exit 1
fi

echo "========================================="
echo " 从 $OLD_DIR/ 拷贝文件到 $NEW_DIR/"
echo "========================================="
echo ""

# 拷贝单个文件（目标存在就覆盖）
copy_file() {
    local rel="$1"
    local src="$OLD_DIR/$rel"
    local dst="$NEW_DIR/$rel"
    if [ -f "$src" ]; then
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        echo "   ✅ $rel"
    else
        echo "   ⏭  $rel （老目录没有，跳过）"
    fi
}

# ==================== 逐个拷贝 ====================
echo "📄 核心文件："
copy_file "src/main.js"
copy_file "src/App.vue"
copy_file "src/style.css"
copy_file "src/api.js"
copy_file "src/stores/auth.js"

echo ""
echo "📄 页面和通用组件："
copy_file "src/views/AuthView.vue"
copy_file "src/components/Sidebar.vue"
copy_file "src/components/UserBadge.vue"
copy_file "src/components/ConfirmDialog.vue"
copy_file "src/components/FileManager.vue"

# ==================== 拷贝 assets ====================
echo ""
echo "🖼  assets："
if [ -d "$OLD_DIR/src/assets" ]; then
    mkdir -p "$NEW_DIR/src/assets"
    # 排除 vite.svg / vue.svg 等脚手架自带的（避免污染）
    for f in "$OLD_DIR/src/assets"/*; do
        base=$(basename "$f")
        if [ "$base" != "vite.svg" ] && [ "$base" != "vue.svg" ]; then
            cp -r "$f" "$NEW_DIR/src/assets/"
            echo "   ✅ src/assets/$base"
        fi
    done
else
    echo "   ⏭  老目录没有 src/assets/"
fi

# ==================== 拷贝 public ====================
echo ""
echo "🌐  public："
if [ -d "$OLD_DIR/public" ]; then
    for f in "$OLD_DIR/public"/*; do
        base=$(basename "$f")
        if [ -f "$f" ]; then
            cp "$f" "$NEW_DIR/public/"
            echo "   ✅ public/$base"
        fi
    done
else
    echo "   ⏭  老目录没有 public/"
fi

# ==================== 不拷贝的文件提醒 ====================
echo ""
echo "⏭  以下文件【不拷贝】，等你手动拆分："
echo "   src/components/Workspace.vue  → 拆到 src/components/workspace/ 下"

echo ""
echo "========================================="
echo " ✅ 拷贝完成"
echo "========================================="
echo ""
echo "下一步："
echo "  1. 检查 $NEW_DIR/src/App.vue 里的 import 路径是否需要调整"
echo "  2. cd $NEW_DIR && npm run dev  测试能否启动"
echo ""
