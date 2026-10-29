<template>
  <div class="tool-pdf-reorder">
    <div v-if="!pages.length" class="form-section">
      <label class="form-label">选择 PDF 文件</label>
      <DropZone
        ref="dropRef"
        accept=".pdf"
        icon="📁"
        text="拖拽 PDF 文件到此处，或点击选择"
        @files="onFiles"
      />
      <p v-if="preparing" class="form-hint">正在生成预览...</p>
    </div>

    <template v-else>
      <div class="area-toolbar">
        <div class="area-stats">
          共 <b>{{ pages.length }}</b> 页 · {{ file?.name }}
        </div>
        <div class="area-actions">
          <button class="btn-ghost" @click="reverseAll">🔄 全部反转</button>
          <button class="btn-ghost" @click="resetOrder">↩️ 恢复原序</button>
          <button class="btn-ghost" @click="resetAll">🔄 重新上传</button>
        </div>
      </div>

      <p class="form-hint">拖拽缩略图调整顺序，或点击 ← → 按钮移动。</p>

      <div class="pages-grid">
        <div
          v-for="(p, idx) in pages"
          :key="p.index"
          class="page-card"
          draggable="true"
          @dragstart="onDragStart(idx)"
          @dragover.prevent
          @drop="onDrop(idx)"
        >
          <div class="page-order">#{{ idx + 1 }}</div>
          <img
            :src="p.preview"
            :width="p.preview_width"
            :height="p.preview_height"
            class="page-thumb"
            draggable="false"
          />
          <div class="page-original">原第 {{ p.index + 1 }} 页</div>
          <div class="page-controls">
            <button :disabled="idx === 0" @click="moveUp(idx)">↑</button>
            <button :disabled="idx === pages.length - 1" @click="moveDown(idx)">↓</button>
          </div>
        </div>
      </div>

      <ActionBar
        :can-submit="pages.length > 0 && !applying"
        :loading="applying"
        @submit="apply"
        @reset="resetAll"
      />
      <ResultCard :result="result" />
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])
const dropRef = ref(null)
const file = ref(null)
const pages = ref([])
const sessionId = ref(null)
const originalOrder = ref([])
const preparing = ref(false)
const applying = ref(false)
const result = ref(null)
let dragFrom = -1

async function onFiles(files) {
  const f = files[0]
  if (!f) return
  preparing.value = true
  file.value = f
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/pdf-redact-area/prepare', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    sessionId.value = res.data.session_id
    pages.value = res.data.pages
    originalOrder.value = res.data.pages.map(p => ({ ...p }))
  } catch (err) {
    const d = err.response?.data?.detail
    alert(typeof d === 'string' ? d : err.message)
    file.value = null
  } finally {
    preparing.value = false
  }
}

function moveUp(idx) {
  if (idx <= 0) return
  const arr = [...pages.value]
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
  pages.value = arr
}

function moveDown(idx) {
  if (idx >= pages.value.length - 1) return
  const arr = [...pages.value]
  ;[arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]]
  pages.value = arr
}

function onDragStart(idx) { dragFrom = idx }

function onDrop(idx) {
  if (dragFrom < 0 || dragFrom === idx) return
  const arr = [...pages.value]
  const [item] = arr.splice(dragFrom, 1)
  arr.splice(idx, 0, item)
  pages.value = arr
  dragFrom = -1
}

function reverseAll() {
  pages.value = [...pages.value].reverse()
}

function resetOrder() {
  pages.value = originalOrder.value.map(p => ({ ...p }))
}

function resetAll() {
  if (pages.value.length && !confirm('确定重新上传吗？当前顺序会丢失。')) return
  pages.value = []
  sessionId.value = null
  file.value = null
  originalOrder.value = []
  result.value = null
  dropRef.value?.reset()
}

async function apply() {
  if (!sessionId.value || !pages.value.length) return
  applying.value = true
  result.value = null
  try {
    const order = pages.value.map(p => p.index + 1)   // 1-indexed
    const fd = new FormData()
    fd.append('session_id', sessionId.value)
    fd.append('order_json', JSON.stringify(order))
    fd.append('file', file.value)   // 后端要重新读文件
    const res = await api.post('/pdf-reorder', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = { success: true, message: res.data.message }
    emit('submitted')
  } catch (err) {
    const d = err.response?.data?.detail
    result.value = { success: false, message: typeof d === 'string' ? d : err.message }
  } finally {
    applying.value = false
  }
}
</script>

<style scoped>
.area-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: #eff6ff; border: 1px solid #bfdbfe;
  border-radius: 8px; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;
}
.area-stats { font-size: 14px; color: #1e3a8a; }
.area-stats b { color: #1e40af; }
.area-actions { display: flex; gap: 8px; }
.pages-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px; margin-top: 16px; max-height: 600px; overflow-y: auto;
  padding: 8px; background: #fafbfc; border-radius: 8px;
}
.page-card {
  position: relative; background: #fff; border: 2px solid #e5e7eb;
  border-radius: 6px; padding: 6px; text-align: center; cursor: grab;
  transition: all 0.15s;
}
.page-card:hover { border-color: #4f46e5; }
.page-card:active { cursor: grabbing; }
.page-order {
  position: absolute; top: 4px; left: 4px; background: #4f46e5; color: #fff;
  font-size: 11px; padding: 2px 6px; border-radius: 8px; font-weight: 700;
}
.page-thumb { max-width: 100%; display: block; }
.page-original { font-size: 11px; color: #6b7280; margin-top: 4px; }
.page-controls { display: flex; justify-content: center; gap: 4px; margin-top: 4px; }
.page-controls button {
  padding: 2px 8px; font-size: 12px; border: 1px solid #d1d5db;
  background: #fff; border-radius: 4px; cursor: pointer;
}
.page-controls button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>