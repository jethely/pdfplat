<template>
  <!-- ① 启动校验中：显示 loading，避免闪屏 -->
  <div v-if="booting" class="boot-screen">
    <div class="boot-spinner"></div>
    <p class="boot-text">加载中...</p>
  </div>

  <!-- ② 未登录：登录/注册页 -->
  <AuthView v-else-if="!isLoggedIn" @success="onAuthSuccess" />

  <!-- ③ 已登录：主界面 -->
  <div v-else class="app-layout">
    <Sidebar
      :tool-groups="toolGroups"
      :active="activeTool"
      @select-tool="selectTool"
    />

    <div class="workspace-wrapper">
      <Workspace v-if="activeTool" :key="activeTool.id" :tool="activeTool" />
      <div v-else class="placeholder">
        <div class="placeholder-icon">👈</div>
        <p>请从左侧选择一个功能</p>
      </div>
    </div>

    <div class="user-badge-wrap">
      <UserBadge @logout="onLogout" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AuthView from './views/AuthView.vue'
import Sidebar from './components/Sidebar.vue'
import Workspace from './components/workspace/Workspace.vue'
import UserBadge from './components/UserBadge.vue'
import { useAuth } from './stores/auth'

const { isLoggedIn, booting, bootstrap } = useAuth()

const activeTool = ref(null)

// ==================== 工具分组 ====================
const toolGroups = [
  {
    id: 'convert',
    name: '格式转换',
    icon: '🔄',
    tools: [
      { id: 'pdf-to-image',      icon: '🖼️', label: 'PDF 转图片',   api: '/pdf-to-image' },
      { id: 'image-to-pdf',      icon: '📄', label: '图片转 PDF',   api: '/image-to-pdf' },
      { id: 'pdf-to-word',       icon: '📝', label: 'PDF 转 Word',  api: '/pdf-to-word' },
      { id: 'pdf-to-excel',      icon: '📊', label: 'PDF 转 Excel', api: '/pdf-to-excel' },
      { id: 'pdf-to-text',       icon: '📃', label: 'PDF 转文本',   api: '/pdf-to-text' },
      { id: 'extract-images',    icon: '🖼️', label: '提取图片',     api: '/extract-images' },
      { id: 'pdf-to-long-image', icon: '📜', label: '输出长图',     api: '/pdf-to-long-image' },
    ],
  },
  {
    id: 'pages',
    name: '页面操作',
    icon: '📄',
    tools: [
      { id: 'pdf-split',        icon: '✂️', label: 'PDF 拆分',     api: '/pdf-split' },
      { id: 'pdf-merge',        icon: '🔗', label: 'PDF 合并',     api: '/pdf-merge' },
      { id: 'pdf-compress',     icon: '🗜️', label: '压缩',         api: '/pdf-compress' },
      { id: 'pdf-delete-pages', icon: '🗑️', label: '删除页面',     api: '/pdf-delete-pages' },
      { id: 'pdf-rotate-pages', icon: '🔄', label: '旋转页面',     api: '/pdf-rotate-pages' },
      { id: 'pdf-reorder',      icon: '🔀', label: '页面重排',     api: '/pdf-reorder' },
      { id: 'pdf-nup',          icon: '🎴', label: 'N-up 拼版',    api: '/pdf-nup' },
      { id: 'pdf-unify-size',   icon: '📐', label: '尺寸统一',     api: '/pdf-unify-size' },
    ],
  },
  {
    id: 'security',
    name: '安全权限',
    icon: '🔒',
    tools: [
      { id: 'pdf-encrypt',      icon: '🔒', label: '加密',         api: '/pdf-encrypt' },
      { id: 'pdf-decrypt',      icon: '🔓', label: '解密',         api: '/pdf-decrypt' },
      { id: 'remove-watermark', icon: '🚫', label: '去水印',       api: '/remove-watermark' },
    ],
  },
  {
    id: 'edit',
    name: '内容编辑',
    icon: '✏️',
    tools: [
      { id: 'text-replace',    icon: '🔤', label: '文字替换',      api: '/text-replace' },
      { id: 'pdf-redact',      icon: '⬛', label: '文字/区域遮掩', api: '/pdf-redact' },
      { id: 'pdf-watermark',   icon: '💧', label: '加水印',        api: '/pdf-watermark' },
      { id: 'pdf-page-number', icon: '🔢', label: '加页码',        api: '/pdf-page-number' },
      { id: 'pdf-metadata',    icon: '🏷️', label: '元数据编辑',    api: '/pdf-metadata' },
      { id: 'pdf-bookmark',    icon: '🔖', label: '添加书签',      api: '/pdf-bookmark' },
    ],
  },
  {
    id: 'stamp',
    name: '印章处理',
    icon: '🔖',
    tools: [
      { id: 'perforated-stamp', icon: '📑', label: '骑缝章擦除', api: '/perforated-stamp' },
      { id: 'stamp-operation',  icon: '🔖', label: '印章擦除',       api: '/stamp-operation' },
    ],
  },
  {
    id: 'analyze',
    name: '分析对比',
    icon: '🔍',
    tools: [
      { id: 'pdf-compare', icon: '⚖️', label: 'PDF 对比', api: '/pdf-compare' },
    ],
  },
]

// ==================== 事件 ====================
function selectTool(tool) {
  activeTool.value = tool
}

function onAuthSuccess() {
  activeTool.value = null
}

function onLogout() {
  activeTool.value = null
}

// ==================== 启动 ====================
onMounted(() => bootstrap())
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
}

.workspace-wrapper {
  flex: 1;
  min-width: 0;
  position: relative;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  color: #9ca3af;
  font-size: 15px;
  gap: 12px;
}

.placeholder-icon {
  font-size: 48px;
}

.user-badge-wrap {
  position: fixed;
  top: 16px;
  right: 20px;
  z-index: 150;
}

/* 启动 loading 页 */
.boot-screen {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #f8fafc;
}

.boot-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e5e7eb;
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.boot-text {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>