<! 文件名：FileManager -->
<template>
  <div class="file-manager">
    <!-- 顶部操作栏 -->
    <div class="fm-header">
      <h3 class="fm-title">📂 本类操作的文件</h3>
      <div class="fm-actions">
        <span v-if="selectedSessions.size" class="fm-selected-count">
          已选 {{ selectedSessions.size }} 个会话
        </span>
        <button
          v-if="selectedSessions.size"
          class="btn-danger"
          @click="confirmDeleteSessions"
        >
          🗑️ 删除选中会话
        </button>
        <button class="btn-ghost" :disabled="loading" @click="refresh">
          🔄 刷新
        </button>
      </div>
    </div>

    <div v-if="loading && !sessions.length" class="fm-empty">加载中...</div>
    <div v-else-if="!sessions.length" class="fm-empty">
      还没有转换记录，处理一个文件后会显示在这里
    </div>

    <div v-else class="fm-list">
      <div
        v-for="s in sessions"
        :key="s.session_id"
        class="fm-session"
        :class="{ expanded: expandedId === s.session_id }"
      >
        <!-- 会话头 -->
        <div class="fm-session-head" @click="toggleExpand(s.session_id)">
          <input
            type="checkbox"
            class="fm-checkbox"
            :checked="selectedSessions.has(s.session_id)"
            @click.stop
            @change="toggleSelectSession(s.session_id)"
          />
          <span class="fm-tool-icon">{{ toolIcon(s.tool) }}</span>
          <div class="fm-session-info">
            <div class="fm-tool-label">{{ toolLabel(s.tool) }}</div>
            <div class="fm-session-meta">
              {{ formatTime(s.created_at) }} ·
              {{ s.input_count }} 入 / {{ s.output_count }} 出
            </div>
          </div>
          <button class="fm-toggle" @click.stop="toggleExpand(s.session_id)">
            {{ expandedId === s.session_id ? '▲' : '▼' }}
          </button>
        </div>

        <!-- 展开内容 -->
        <div v-if="expandedId === s.session_id" class="fm-session-body">
          <div v-if="detailLoading" class="fm-empty-small">加载中...</div>

          <template v-else-if="detail">
            <!-- 文件工具栏 -->
            <div class="fm-file-toolbar">
              <label class="fm-select-all">
                <input
                  type="checkbox"
                  :checked="allFilesSelected"
                  :indeterminate.prop="someFilesSelected && !allFilesSelected"
                  @change="toggleSelectAllFiles"
                />
                <span>全选（{{ totalFiles }} 个文件）</span>
              </label>
              <button
                v-if="selectedFiles.size"
                class="btn-danger-sm"
                @click="confirmDeleteSelectedFiles"
              >
                🗑️ 删除选中 ({{ selectedFiles.size }})
              </button>
            </div>

            <!-- 输入文件 -->
            <div v-if="detail.input.length" class="fm-group">
              <div class="fm-group-title">📥 输入</div>
              <div
                v-for="f in detail.input"
                :key="'in-' + f.name"
                class="fm-file"
                :class="{ selected: isFileSelected('input', f.name) }"
              >
                <input
                  type="checkbox"
                  class="fm-file-checkbox"
                  :checked="isFileSelected('input', f.name)"
                  @change="toggleFileSelection('input', f.name)"
                />
                <span class="fm-file-icon">📄</span>
                <span class="fm-file-name" :title="f.name">{{ f.name }}</span>
                <span class="fm-file-size">{{ formatSize(f.size) }}</span>
                <button
                  class="fm-file-btn"
                  title="下载"
                  @click="downloadFile(s.session_id, 'input', f.name)"
                >⬇️</button>
                <button
                  class="fm-file-btn danger"
                  title="删除"
                  @click="confirmDeleteFile(s.session_id, 'input', f.name)"
                >🗑️</button>
              </div>
            </div>

            <!-- 输出文件 -->
            <div v-if="detail.output.length" class="fm-group">
              <div class="fm-group-title">📤 输出</div>
              <div
                v-for="f in detail.output"
                :key="'out-' + f.name"
                class="fm-file"
                :class="{ selected: isFileSelected('output', f.name) }"
              >
                <input
                  type="checkbox"
                  class="fm-file-checkbox"
                  :checked="isFileSelected('output', f.name)"
                  @change="toggleFileSelection('output', f.name)"
                />
                <span class="fm-file-icon">{{ fileIcon(f.name) }}</span>
                <span class="fm-file-name" :title="f.name">{{ f.name }}</span>
                <span class="fm-file-size">{{ formatSize(f.size) }}</span>
                <button
                  class="fm-file-btn"
                  title="下载"
                  @click="downloadFile(s.session_id, 'output', f.name)"
                >⬇️</button>
                <button
                  class="fm-file-btn danger"
                  title="删除"
                  @click="confirmDeleteFile(s.session_id, 'output', f.name)"
                >🗑️</button>
              </div>
            </div>

            <!-- 会话整体操作 -->
            <div class="fm-session-actions">
              <button
                class="btn-ghost danger"
                @click="confirmDeleteSession(s.session_id)"
              >
                🗑️ 删除整个会话（含所有文件）
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 确认弹窗 -->
    <ConfirmDialog
      v-model:visible="confirmState.visible"
      :title="confirmState.title"
      :message="confirmState.message"
      :danger="true"
      confirm-text="确认删除"
      cancel-text="取消"
      @confirm="onConfirm"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'
import ConfirmDialog from './ConfirmDialog.vue'

const props = defineProps({
  toolId: { type: String, default: null },
})

const TOOL_META = {
  'pdf-to-image':     { icon: '🖼️', label: 'PDF 转图片' },
  'image-to-pdf':     { icon: '📄', label: '图片转 PDF' },
  'pdf-split':        { icon: '✂️', label: 'PDF 拆分' },
  'pdf-merge':        { icon: '🔗', label: 'PDF 合并' },
  'pdf-compress':     { icon: '🗜️', label: 'PDF 压缩' },
  'pdf-encrypt':      { icon: '🔒', label: 'PDF 加密' },
  'pdf-decrypt':      { icon: '🔓', label: 'PDF 解密' },
  'text-replace':     { icon: '🔤', label: '文字替换' },
  'perforated-stamp': { icon: '📑', label: '骑缝章处理' },
  'stamp-operation':  { icon: '🔖', label: '印章处理' },
  'text-redact':      { icon: '⬛', label: '文字遮掩' },
}

const sessions         = ref([])
const loading          = ref(false)
const selectedSessions = ref(new Set())
const expandedId       = ref(null)
const detail           = ref(null)
const detailLoading    = ref(false)
const selectedFiles    = ref(new Set())   // 形如 "input:xxx.pdf" / "output:xxx.png"

const confirmState = reactive({
  visible: false,
  title: '',
  message: '',
  action: null,
})

/* ============ 工具函数 ============ */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c])
}

function toolIcon(id) { return TOOL_META[id]?.icon || '📁' }
function toolLabel(id) { return TOOL_META[id]?.label || id || '未知' }

function fileIcon(name) {
  const ext = (name.split('.').pop() || '').toLowerCase()
  if (['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'].includes(ext)) return '🖼️'
  if (ext === 'pdf') return '📕'
  if (ext === 'zip') return '🗜️'
  return '📄'
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1)
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i]
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/* ============ 弹窗 ============ */
function showConfirm(title, message, action) {
  confirmState.title = title
  confirmState.message = message
  confirmState.action = action
  confirmState.visible = true
}
function onConfirm() {
  const act = confirmState.action
  confirmState.action = null
  if (typeof act === 'function') act()
}

/* ============ 列表加载 ============ */
async function refresh() {
  loading.value = true
  try {
    const res = await api.get('/sessions')
    const list = res.data.sessions || []
    const detailed = await Promise.all(
      list.filter((s) => !props.toolId || s.tool === props.toolId)
	  .map(async (s) => {
        try {
          const d = await api.get(`/sessions/${s.session_id}`)
          return {
            ...s,
            input_count: d.data.input.length,
            output_count: d.data.output.length,
          }
        } catch {
          return { ...s, input_count: 0, output_count: 0 }
        }
      })
    )
    sessions.value = detailed

    const validIds = new Set(detailed.map((s) => s.session_id))
    selectedSessions.value = new Set(
      [...selectedSessions.value].filter((id) => validIds.has(id))
    )

    // 展开的 session 被删掉了
    if (expandedId.value && !validIds.has(expandedId.value)) {
      expandedId.value = null
      detail.value = null
      selectedFiles.value = new Set()
    } else if (expandedId.value) {
      // 刷新当前展开的详情
      try {
        const d = await api.get(`/sessions/${expandedId.value}`)
        detail.value = d.data
        // 清理已删除文件的勾选
        const validFiles = new Set()
        d.data.input.forEach((f) => validFiles.add(fileKey('input', f.name)))
        d.data.output.forEach((f) => validFiles.add(fileKey('output', f.name)))
        selectedFiles.value = new Set(
          [...selectedFiles.value].filter((k) => validFiles.has(k))
        )
      } catch {
        expandedId.value = null
        detail.value = null
      }
    }
  } catch (e) {
    console.error('加载会话列表失败', e)
  } finally {
    loading.value = false
  }
}

async function toggleExpand(sid) {
  if (expandedId.value === sid) {
    expandedId.value = null
    detail.value = null
    selectedFiles.value = new Set()
    return
  }
  expandedId.value = sid
  detail.value = null
  selectedFiles.value = new Set()
  detailLoading.value = true
  try {
    const res = await api.get(`/sessions/${sid}`)
    detail.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    detailLoading.value = false
  }
}

/* ============ 会话勾选 ============ */
function toggleSelectSession(sid) {
  const s = new Set(selectedSessions.value)
  s.has(sid) ? s.delete(sid) : s.add(sid)
  selectedSessions.value = s
}

/* ============ 文件勾选 ============ */
function fileKey(subdir, name) { return `${subdir}:${name}` }
function isFileSelected(subdir, name) {
  return selectedFiles.value.has(fileKey(subdir, name))
}
function toggleFileSelection(subdir, name) {
  const s = new Set(selectedFiles.value)
  const k = fileKey(subdir, name)
  s.has(k) ? s.delete(k) : s.add(k)
  selectedFiles.value = s
}

const totalFiles = computed(() => {
  if (!detail.value) return 0
  return detail.value.input.length + detail.value.output.length
})
const allFilesSelected = computed(() => {
  return totalFiles.value > 0 && selectedFiles.value.size === totalFiles.value
})
const someFilesSelected = computed(() => selectedFiles.value.size > 0)

function toggleSelectAllFiles() {
  if (allFilesSelected.value) {
    selectedFiles.value = new Set()
  } else {
    const s = new Set()
    if (detail.value) {
      detail.value.input.forEach((f) => s.add(fileKey('input', f.name)))
      detail.value.output.forEach((f) => s.add(fileKey('output', f.name)))
    }
    selectedFiles.value = s
  }
}

/* ============ 下载 ============ */
function downloadFile(sid, subdir, filename) {
  const token = localStorage.getItem('token')
  if (!token) {
    alert('登录已失效，请重新登录')
    return
  }

  const url =
    `/api/sessions/${sid}/files/${subdir}/${encodeURIComponent(filename)}` +
    `?token=${encodeURIComponent(token)}`

  // 用原生 <a> 触发下载：浏览器接管，有进度条，不会预览
  const a = document.createElement('a')
  a.href = url
  a.download = filename       // 提示浏览器用这个名字保存
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

/* ============ 删除：单文件 ============ */
function confirmDeleteFile(sid, subdir, filename) {
  let extraMsg = ''
  let cascadeOutput = false

  // 删 input 时，若该 session 只有 1 个 input → 连带删所有 output
  if (subdir === 'input' && detail.value && expandedId.value === sid) {
    const inputCount = detail.value.input.length
    const outputCount = detail.value.output.length
    if (inputCount === 1 && outputCount > 0) {
      cascadeOutput = true
      extraMsg = `<br><br>⚠️ 同时会删除本次生成的 <b>${outputCount}</b> 个输出文件。`
    }
  }

  showConfirm(
    '删除文件',
    `确定要删除「<span class="strong">${escapeHtml(filename)}</span>」吗？${extraMsg}<br><br>此操作不可恢复。`,
    () => doDeleteFile(sid, subdir, filename, cascadeOutput)
  )
}

async function doDeleteFile(sid, subdir, filename, cascadeOutput = false) {
  try {
    // 1) 删自身
    await api.delete(
      `/sessions/${sid}/files/${subdir}/${encodeURIComponent(filename)}`
    )

    // 2) 连带删除所有 output
    if (cascadeOutput && detail.value && expandedId.value === sid) {
      const outputs = [...detail.value.output]
      await Promise.all(
        outputs.map(async (f) => {
          try {
            await api.delete(
              `/sessions/${sid}/files/output/${encodeURIComponent(f.name)}`
            )
          } catch (e) {
            console.warn('删除关联输出失败', f.name, e)
          }
        })
      )
    }

    // 3) 重新拉详情，刷新 UI
    if (detail.value && expandedId.value === sid) {
      const res = await api.get(`/sessions/${sid}`)
      detail.value = res.data
      selectedFiles.value = new Set()
      const s = sessions.value.find((x) => x.session_id === sid)
      if (s) {
        s.input_count = detail.value.input.length
        s.output_count = detail.value.output.length
      }
    }
  } catch (e) {
    alert('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

/* ============ 删除：批量文件 ============ */
function confirmDeleteSelectedFiles() {
  if (!selectedFiles.value.size) return
  showConfirm(
    '批量删除文件',
    `确定要删除选中的 <span class="strong">${selectedFiles.value.size}</span> 个文件吗？此操作不可恢复。`,
    doDeleteSelectedFiles
  )
}

async function doDeleteSelectedFiles() {
  if (!expandedId.value) return
  const sid = expandedId.value
  const keys = [...selectedFiles.value]
  const failed = []

  await Promise.all(
    keys.map(async (k) => {
      const idx = k.indexOf(':')
      const subdir = k.slice(0, idx)
      const filename = k.slice(idx + 1)
      try {
        await api.delete(
          `/sessions/${sid}/files/${subdir}/${encodeURIComponent(filename)}`
        )
      } catch {
        failed.push(filename)
      }
    })
  )

  // 重新拉详情
  try {
    const res = await api.get(`/sessions/${sid}`)
    detail.value = res.data
    selectedFiles.value = new Set()
    const s = sessions.value.find((x) => x.session_id === sid)
    if (s) {
      s.input_count = detail.value.input.length
      s.output_count = detail.value.output.length
    }
  } catch (e) {
    console.error(e)
  }

  if (failed.length) {
    alert(`有 ${failed.length} 个文件删除失败`)
  }
}

/* ============ 删除：整个会话 ============ */
function confirmDeleteSession(sid) {
  const s = sessions.value.find((x) => x.session_id === sid)
  const label = s ? toolLabel(s.tool) : '这个会话'
  showConfirm(
    '删除整个会话',
    `确定要删除「<span class="strong">${escapeHtml(label)}</span>」及其<b>所有关联文件</b>吗？此操作不可恢复。`,
    () => doDeleteSession(sid)
  )
}

async function doDeleteSession(sid) {
  try {
    await api.delete(`/sessions/${sid}`)
    sessions.value = sessions.value.filter((s) => s.session_id !== sid)
    selectedSessions.value.delete(sid)
    if (expandedId.value === sid) {
      expandedId.value = null
      detail.value = null
      selectedFiles.value = new Set()
    }
  } catch (e) {
    alert('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

/* ============ 删除：批量会话 ============ */
function confirmDeleteSessions() {
  if (!selectedSessions.value.size) return
  showConfirm(
    '批量删除会话',
    `确定要删除选中的 <span class="strong">${selectedSessions.value.size}</span> 个会话及其所有文件吗？此操作不可恢复。`,
    doDeleteSelectedSessions
  )
}

async function doDeleteSelectedSessions() {
  const ids = [...selectedSessions.value]
  try {
    await api.post('/sessions/delete-batch', { session_ids: ids })
    sessions.value = sessions.value.filter((s) => !selectedSessions.value.has(s.session_id))
    if (expandedId.value && selectedSessions.value.has(expandedId.value)) {
      expandedId.value = null
      detail.value = null
      selectedFiles.value = new Set()
    }
    selectedSessions.value = new Set()
  } catch (e) {
    alert('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(refresh)

defineExpose({ refresh })
</script>

<style scoped>
.file-manager {
  background: var(--card-bg, #fff);
  border-radius: var(--radius, 8px);
  border: 1px solid var(--border-color, #e5e7eb);
  padding: 20px 22px;
  margin-top: 20px;
}

.fm-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px; gap: 12px; flex-wrap: wrap;
}
.fm-title { font-size: 16px; font-weight: 700; color: var(--text-primary, #111827); margin: 0; }
.fm-actions { display: flex; align-items: center; gap: 10px; }
.fm-selected-count { font-size: 13px; color: var(--text-secondary, #6b7280); }

.btn-danger {
  padding: 6px 14px; border: 1px solid #fecaca; background: #fef2f2;
  color: #b91c1c; border-radius: 6px; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.btn-danger:hover { background: #fee2e2; border-color: #fca5a5; }

.btn-danger-sm {
  padding: 4px 10px; border: 1px solid #fecaca; background: #fef2f2;
  color: #b91c1c; border-radius: 6px; font-size: 12px; cursor: pointer;
}
.btn-danger-sm:hover { background: #fee2e2; border-color: #fca5a5; }

.btn-ghost {
  padding: 6px 14px; border: 1px solid var(--border-color, #e5e7eb);
  background: #fff; border-radius: 6px; font-size: 13px;
  color: var(--text-primary, #111827); cursor: pointer;
}
.btn-ghost:hover:not(:disabled) { background: #f9fafb; }
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost.danger { color: #dc2626; }
.btn-ghost.danger:hover { background: #fef2f2; border-color: #fca5a5; }

.fm-empty { padding: 40px 20px; text-align: center; font-size: 14px; color: var(--text-secondary, #6b7280); }
.fm-empty-small { padding: 12px; font-size: 13px; color: var(--text-secondary, #6b7280); }

.fm-list { display: flex; flex-direction: column; gap: 8px; }

.fm-session {
  border: 1px solid var(--border-color, #e5e7eb); border-radius: 8px;
  background: #fff; overflow: hidden; transition: border-color .15s, box-shadow .15s;
}
.fm-session:hover { border-color: #c7d2fe; }
.fm-session.expanded { border-color: #c7d2fe; box-shadow: 0 2px 10px rgba(79,70,229,.08); }

.fm-session-head {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; cursor: pointer; user-select: none;
}

.fm-checkbox {
  width: 16px; height: 16px; accent-color: var(--primary-color, #4f46e5);
  cursor: pointer; flex-shrink: 0;
}

.fm-tool-icon { font-size: 20px; flex-shrink: 0; }

.fm-session-info { flex: 1; min-width: 0; }
.fm-tool-label { font-size: 14px; font-weight: 600; color: var(--text-primary, #111827); }
.fm-session-meta { font-size: 12px; color: var(--text-secondary, #6b7280); margin-top: 2px; }

.fm-toggle {
  border: none; background: transparent; color: #9ca3af;
  cursor: pointer; font-size: 11px; padding: 6px; border-radius: 6px; flex-shrink: 0;
}
.fm-toggle:hover { background: #f3f4f6; color: #4f46e5; }

.fm-session-body {
  border-top: 1px solid var(--border-color, #e5e7eb);
  padding: 12px 16px 16px; background: #fafbfc;
}

/* 文件工具栏 */
.fm-file-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 8px 10px; margin-bottom: 10px;
  background: #fff; border-radius: 6px; border: 1px solid var(--border-color, #e5e7eb);
}
.fm-select-all {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--text-primary, #111827); cursor: pointer; user-select: none;
}
.fm-select-all input[type="checkbox"] {
  width: 16px; height: 16px; accent-color: var(--primary-color, #4f46e5); cursor: pointer;
}

.fm-group { margin-bottom: 14px; }
.fm-group:last-child { margin-bottom: 0; }
.fm-group-title {
  font-size: 12px; font-weight: 600; color: var(--text-secondary, #6b7280);
  text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px;
}

.fm-file {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 6px; transition: background .15s;
}
.fm-file:hover { background: #fff; }
.fm-file.selected { background: #eef2ff; }

.fm-file-checkbox {
  width: 16px; height: 16px; accent-color: var(--primary-color, #4f46e5);
  cursor: pointer; flex-shrink: 0;
}
.fm-file-icon { font-size: 16px; flex-shrink: 0; }
.fm-file-name {
  flex: 1; min-width: 0; font-size: 13px; color: var(--text-primary, #111827);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.fm-file-size { font-size: 12px; color: var(--text-secondary, #6b7280); flex-shrink: 0; }

.fm-file-btn {
  border: none; background: transparent; cursor: pointer;
  font-size: 14px; padding: 4px 6px; border-radius: 4px; transition: background .15s;
}
.fm-file-btn:hover { background: #eef2ff; }
.fm-file-btn.danger:hover { background: #fef2f2; }

.fm-session-actions {
  margin-top: 12px; padding-top: 12px;
  border-top: 1px dashed var(--border-color, #e5e7eb);
  display: flex; justify-content: flex-end;
}
</style>