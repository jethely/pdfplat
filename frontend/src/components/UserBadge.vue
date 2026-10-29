<template>
  <div class="user-badge" ref="rootRef">
    <!-- 触发按钮 -->
    <button
      class="user-trigger"
      :class="{ open }"
      @click="open = !open"
    >
      <span class="avatar">{{ initials }}</span>
      <span class="username">{{ user?.username }}</span>
      <span class="chev" :class="{ open }">▾</span>
    </button>

    <!-- 下拉菜单 -->
    <transition name="menu">
      <div v-if="open" class="user-menu">
        <div class="menu-header">
          <div class="menu-avatar">{{ initials }}</div>
          <div class="menu-info">
            <div class="menu-name">{{ user?.username }}</div>
            <div class="menu-id">ID: {{ user?.id }}</div>
          </div>
        </div>

        <div class="menu-divider"></div>

        <button class="menu-item" @click="handleReload">
          <span class="menu-icon">🔄</span>
          <span>刷新用户信息</span>
        </button>

        <button class="menu-item danger" @click="handleLogout">
          <span class="menu-icon">🚪</span>
          <span>退出登录</span>
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useAuth } from '../stores/auth'

const emit = defineEmits(['logout'])
const { user, logout } = useAuth()

const open = ref(false)
const rootRef = ref(null)

// 用户名首字母（大写）；中文名取第一个字
const initials = computed(() => {
  const n = user.value?.username || '?'
  return n.slice(0, 1).toUpperCase()
})

function handleLogout() {
  open.value = false
  if (!confirm('确定要退出登录吗？')) return
  logout()
  emit('logout')
}

function handleReload() {
  open.value = false
  location.reload()
}

// 点击外部关闭
function onClickOutside(e) {
  if (open.value && rootRef.value && !rootRef.value.contains(e.target)) {
    open.value = false
  }
}

// ESC 关闭
function onKeydown(e) {
  if (e.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.user-badge {
  position: relative;
  z-index: 200;
  font-family: inherit;
}

/* ===== 触发按钮 ===== */
.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px 5px 5px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
  color: #111827;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.user-trigger:hover,
.user-trigger.open {
  border-color: #c7d2fe;
  box-shadow: 0 2px 10px rgba(79, 70, 229, 0.12);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  font-weight: 700;
  font-size: 12px;
  flex-shrink: 0;
}

.username {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.chev {
  font-size: 10px;
  color: #9ca3af;
  transition: transform 0.2s;
}
.chev.open {
  transform: rotate(180deg);
}

/* ===== 下拉菜单 ===== */
.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  overflow: hidden;
  padding: 4px;
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.menu-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  font-weight: 700;
  font-size: 15px;
  flex-shrink: 0;
}

.menu-info {
  min-width: 0;
  flex: 1;
}

.menu-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-id {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.menu-divider {
  height: 1px;
  background: #f3f4f6;
  margin: 4px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #374151;
  text-align: left;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s, color 0.15s;
}

.menu-item:hover {
  background: #f9fafb;
}

.menu-item.danger {
  color: #dc2626;
}
.menu-item.danger:hover {
  background: #fef2f2;
}

.menu-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
}

/* ===== 动画 ===== */
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>