<template>
  <aside class="sidebar">
    <!-- 顶部 Logo -->
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">📋</span>
        <span class="logo-text">PDF 工具箱</span>
      </div>
    </div>

    <!-- 搜索框 -->
    <div class="sidebar-search">
      <input
        v-model="searchText"
        type="text"
        class="search-input"
        placeholder="搜索功能..."
      />
      <button
        v-if="searchText"
        class="search-clear"
        @click="searchText = ''"
      >✕</button>
    </div>

    <!-- 分组菜单 -->
    <nav class="sidebar-nav">
      <template v-for="group in filteredGroups" :key="group.id">
        <!-- 分组头 -->
        <div
          class="group-header"
          @click="toggleGroup(group.id)"
        >
          <span class="group-icon">{{ group.icon }}</span>
          <span class="group-name">{{ group.name }}</span>
          <span class="group-count">{{ group.tools.length }}</span>
          <span class="group-chevron" :class="{ open: isGroupOpen(group.id) }">
            ▾
          </span>
        </div>

        <!-- 分组内容 -->
        <div
          v-show="isGroupOpen(group.id)"
          class="group-body"
        >
          <button
            v-for="tool in group.tools"
            :key="tool.id"
            :class="['nav-item', { active: activeTool?.id === tool.id }]"
            @click="$emit('select-tool', tool)"
          >
            <span class="nav-icon">{{ tool.icon }}</span>
            <span class="nav-label">{{ tool.label }}</span>
          </button>
        </div>
      </template>

      <!-- 无搜索结果 -->
      <div v-if="!filteredGroups.length" class="no-results">
        没有匹配的功能
      </div>
    </nav>

    <!-- 底部版本 -->
    <div class="sidebar-footer">
      <span class="version">v1.0.0</span>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  toolGroups: { type: Array, required: true },
  activeTool: { type: Object, default: null },
})
defineEmits(['select-tool'])

const STORAGE_KEY = 'sidebar_open_group'

const searchText = ref('')

// ⭐ 手风琴模式：只记录一个「当前打开的分组 id」
function loadOpenGroup() {
  try {
    return localStorage.getItem(STORAGE_KEY) || props.toolGroups[0]?.id || null
  } catch (e) {
    return props.toolGroups[0]?.id || null
  }
}

const openGroupId = ref(loadOpenGroup())

// 是否展开某组
function isGroupOpen(groupId) {
  // 搜索时强制全部展开（方便看结果）
  if (searchText.value.trim()) return true
  return openGroupId.value === groupId
}

// 点击分组头：手风琴
function toggleGroup(groupId) {
  if (searchText.value.trim()) return   // 搜索时不响应折叠

  if (openGroupId.value === groupId) {
    // 再点一次 → 收起
    openGroupId.value = null
  } else {
    // 打开新组 → 其他自动关闭
    openGroupId.value = groupId
  }
  try {
    if (openGroupId.value) {
      localStorage.setItem(STORAGE_KEY, openGroupId.value)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  } catch (e) { /* ignore */ }
}

// 搜索过滤
const filteredGroups = computed(() => {
  const kw = searchText.value.trim().toLowerCase()
  if (!kw) return props.toolGroups

  return props.toolGroups
    .map(g => ({
      ...g,
      tools: g.tools.filter(t =>
        t.label.toLowerCase().includes(kw) ||
        t.id.toLowerCase().includes(kw)
      ),
    }))
    .filter(g => g.tools.length > 0)
})

// 切换工具时，自动打开它所在的分组
watch(
  () => props.activeTool?.id,
  (newId) => {
    if (!newId) return
    for (const g of props.toolGroups) {
      if (g.tools.some(t => t.id === newId)) {
        if (openGroupId.value !== g.id) {
          openGroupId.value = g.id
          try {
            localStorage.setItem(STORAGE_KEY, g.id)
          } catch (e) { /* ignore */ }
        }
        break
      }
    }
  }
)
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.12);
}

/* ===== Logo 区 ===== */
.sidebar-header {
  padding: 20px 16px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-icon { font-size: 24px; }
.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.5px;
}

/* ===== 搜索框 ===== */
.sidebar-search {
  padding: 10px 12px;
  position: relative;
  flex-shrink: 0;
}
.search-input {
  width: 100%;
  padding: 8px 30px 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  font-size: 13px;
  color: #f1f5f9;
  outline: none;
  transition: all 0.15s;
  box-sizing: border-box;
}
.search-input::placeholder {
  color: rgba(241, 245, 249, 0.5);
}
.search-input:focus {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}
.search-clear {
  position: absolute;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: rgba(241, 245, 249, 0.6);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
}
.search-clear:hover { color: #fff; }

/* ===== 导航区 ===== */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 分组头 */
.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-top: 6px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  color: rgba(241, 245, 249, 0.85);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: background 0.15s;
}
.group-header:hover {
  background: rgba(255, 255, 255, 0.06);
}
.group-icon {
  font-size: 14px;
  width: 16px;
  text-align: center;
}
.group-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.group-count {
  font-size: 10px;
  padding: 1px 6px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  font-weight: 500;
}
.group-chevron {
  font-size: 10px;
  transition: transform 0.2s;
  color: rgba(241, 245, 249, 0.5);
}
.group-chevron.open {
  transform: rotate(0deg);
}
.group-chevron:not(.open) {
  transform: rotate(-90deg);
}

/* 分组内容 */
.group-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-left: 4px;
}

/* 菜单项 */
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  width: 100%;
  border: none;
  background: transparent;
  color: inherit;
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}
.nav-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-results {
  padding: 30px 16px;
  text-align: center;
  font-size: 13px;
  color: rgba(241, 245, 249, 0.5);
}

/* ===== 底部 ===== */
.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  flex-shrink: 0;
}
.version {
  color: #64748b;
  font-size: 12px;
}

/* ===== 滚动条美化 ===== */
.sidebar-nav::-webkit-scrollbar {
  width: 6px;
}
.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}
.sidebar-nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
}
.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}
</style>