<template>
  <div class="tool-pdf-redact">
    <!-- 模式切换 -->
    <div class="form-section">
      <label class="form-label">遮掩方式</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model="mode" value="text" :disabled="!!pages.length" />
          <span><b>按文字内容</b> — 输入文字自动匹配</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="mode" value="area" :disabled="!!uploadedFile" />
          <span><b>可视化框选</b> — 在预览图上拖框</span>
        </label>
      </div>
      <p v-if="pages.length || uploadedFile" class="form-hint">
        切换模式前请先重置。
      </p>
    </div>

    <!-- ==================== 模式 A：文字内容 ==================== -->
    <template v-if="mode === 'text'">
      <!-- 上传 -->
      <div class="form-section">
        <label class="form-label">选择 PDF 文件</label>
        <DropZone
          v-if="!uploadedFile"
          ref="textDropRef"
          accept=".pdf"
          icon="📁"
          text="拖拽 PDF 文件到此处，或点击选择"
          @files="onTextFiles"
        />
        <FileList
          :files="uploadedFile ? [uploadedFile] : []"
          icon="📄"
          @remove="onRemoveTextFile"
        />
      </div>

      <!-- 操作类型 -->
      <div class="form-section">
        <label class="form-label">遮掩操作</label>
        <div class="radio-group">
          <label class="radio-item">
            <input type="radio" v-model="fillMode" value="mask" />
            <span>文字遮掩（黑色）</span>
          </label>
          <label class="radio-item">
            <input type="radio" v-model="fillMode" value="erase" />
            <span>文字擦除（白色）</span>
          </label>
        </div>
      </div>

      <!-- 文字输入 -->
      <div class="form-section">
        <label class="form-label">需要遮掩/擦除的文字</label>
        <textarea
          v-model="textToRedact"
          class="form-textarea"
          placeholder="请输入需要遮掩或擦除的文字内容"
          rows="3"
        ></textarea>
        <p class="form-hint">精确匹配，区分大小写。</p>
      </div>

      <!-- 页码范围 -->
      <div class="form-section">
        <label class="form-label">搜索范围</label>
        <div class="radio-group radio-vertical">
          <label class="radio-item">
            <input type="radio" v-model="scope" value="all" />
            <span>全文（所有页面）</span>
          </label>
          <label class="radio-item">
            <input type="radio" v-model="scope" value="pages" />
            <span>指定页面</span>
          </label>
        </div>
        <div v-if="scope === 'pages'" style="margin-top: 12px;">
          <input
            v-model="pagesText"
            type="text"
            class="form-input"
            placeholder="例: 1, 3, 5-7"
          />
          <p class="form-hint">
            页码用逗号分隔，支持范围（如 <code>1-3</code>）。
          </p>
        </div>
      </div>
    </template>

    <!-- ==================== 模式 B：区域框选 ==================== -->
    <template v-else>
      <!-- 未上传：上传区 -->
      <div v-if="!pages.length" class="form-section">
        <label class="form-label">选择 PDF 文件</label>
        <DropZone
          ref="areaDropRef"
          accept=".pdf"
          icon="📁"
          text="拖拽 PDF 文件到此处，或点击选择"
          @files="onAreaFiles"
        />
        <p v-if="preparing" class="form-hint">正在生成预览...</p>
      </div>

      <!-- 已上传：预览 + 框选 -->
      <template v-else>
        <!-- 工具栏 -->
        <div class="area-toolbar">
          <div class="area-stats">
            已选 <b>{{ rects.length }}</b> 个区域
            <span v-if="areaFile" class="area-file">· {{ areaFile.name }}</span>
          </div>
          <div class="area-zoom">
            <span class="zoom-label">缩放：</span>
            <button class="zoom-btn" @click="zoomOut" title="缩小">−</button>
            <span class="zoom-value">{{ Math.round(zoom * 100) }}%</span>
            <button class="zoom-btn" @click="zoomIn" title="放大">＋</button>
            <button class="zoom-reset" @click="zoom = 1">重置</button>
          </div>
          <div class="area-actions">
            <button
              v-if="rects.length"
              class="btn-ghost danger"
              @click="clearRects"
            >🗑️ 清空区域</button>
            <button class="btn-ghost" @click="resetArea">🔄 重新上传</button>
          </div>
        </div>

        <!-- 填充颜色 -->
        <div class="form-section">
          <label class="form-label">填充颜色</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" v-model="areaFill" value="black" />
              <span>黑块</span>
            </label>
            <label class="radio-item">
              <input type="radio" v-model="areaFill" value="white" />
              <span>白块</span>
            </label>
          </div>
        </div>

        <!-- 形状 -->
        <div class="form-section">
          <label class="form-label">形状</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" v-model="shape" value="rect" />
              <span>方块</span>
            </label>
            <label class="radio-item">
              <input type="radio" v-model="shape" value="ellipse" />
              <span>椭圆</span>
            </label>
            <label class="radio-item">
              <input type="radio" v-model="shape" value="circle" />
              <span>圆形</span>
            </label>
          </div>
          <p class="form-hint">
            拖拽时圈多大面积就遮多大。圆形按短边取正圆。
          </p>
        </div>

        <!-- 预览列表 -->
        <div class="pages-list">
          <div v-for="p in pages" :key="p.index" class="page-item">
            <div class="page-header">
              第 {{ p.index + 1 }} 页
              <span v-if="rectsOfPage(p.index).length" class="page-badge">
                {{ rectsOfPage(p.index).length }} 个区域
              </span>
            </div>

            <div
              class="canvas-outer"
              :style="{ width: (p.preview_width * zoom) + 'px', height: (p.preview_height * zoom) + 'px' }"
            >
              <div
                class="canvas-wrap"
                :style="{
                  width: p.preview_width + 'px',
                  height: p.preview_height + 'px',
                  transform: `scale(${zoom})`,
                  transformOrigin: 'top left'
                }"
                @mousedown="onDown($event, p)"
              >
                <img
                  :src="p.preview"
                  :width="p.preview_width"
                  :height="p.preview_height"
                  class="page-img"
                  draggable="false"
                />
                <svg
                  class="page-svg"
                  :width="p.preview_width"
                  :height="p.preview_height"
                >
                  <g
                    v-for="(r, i) in rectsOfPage(p.index)"
                    :key="i"
                    class="area-shape"
                    @click.stop="removeRect(r._id)"
                  >
                    <rect
                      v-if="shape === 'rect'"
                      :x="r._dx0" :y="r._dy0"
                      :width="r._dx1 - r._dx0" :height="r._dy1 - r._dy0"
                      :fill="areaPreviewFill" stroke="#4f46e5" stroke-width="1.5"
                    />
                    <ellipse
                      v-else-if="shape === 'ellipse'"
                      :cx="(r._dx0 + r._dx1) / 2" :cy="(r._dy0 + r._dy1) / 2"
                      :rx="(r._dx1 - r._dx0) / 2" :ry="(r._dy1 - r._dy0) / 2"
                      :fill="areaPreviewFill" stroke="#4f46e5" stroke-width="1.5"
                    />
                    <circle
                      v-else
                      :cx="(r._dx0 + r._dx1) / 2" :cy="(r._dy0 + r._dy1) / 2"
                      :r="Math.min(r._dx1 - r._dx0, r._dy1 - r._dy0) / 2"
                      :fill="areaPreviewFill" stroke="#4f46e5" stroke-width="1.5"
                    />
                  </g>

                  <template v-if="dragging && dragging.pageIndex === p.index">
                    <rect
                      v-if="shape === 'rect'"
                      :x="Math.min(dragging.x0, dragging.x1)"
                      :y="Math.min(dragging.y0, dragging.y1)"
                      :width="Math.abs(dragging.x1 - dragging.x0)"
                      :height="Math.abs(dragging.y1 - dragging.y0)"
                      fill="rgba(79,70,229,0.3)" stroke="#4f46e5"
                      stroke-dasharray="4 3" stroke-width="1.5"
                    />
                    <ellipse
                      v-else-if="shape === 'ellipse'"
                      :cx="(dragging.x0 + dragging.x1) / 2"
                      :cy="(dragging.y0 + dragging.y1) / 2"
                      :rx="Math.abs(dragging.x1 - dragging.x0) / 2"
                      :ry="Math.abs(dragging.y1 - dragging.y0) / 2"
                      fill="rgba(79,70,229,0.3)" stroke="#4f46e5"
                      stroke-dasharray="4 3" stroke-width="1.5"
                    />
                    <circle
                      v-else
                      :cx="(dragging.x0 + dragging.x1) / 2"
                      :cy="(dragging.y0 + dragging.y1) / 2"
                      :r="Math.min(Math.abs(dragging.x1 - dragging.x0), Math.abs(dragging.y1 - dragging.y0)) / 2"
                      fill="rgba(79,70,229,0.3)" stroke="#4f46e5"
                      stroke-dasharray="4 3" stroke-width="1.5"
                    />
                  </template>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- 操作按钮 -->
    <ActionBar
      :can-submit="canSubmit"
      :loading="loading"
      @submit="submit"
      @reset="resetAll"
    />

    <ResultCard :result="result" />
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import FileList from './common/FileList.vue'
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])

// ==================== 模式 ====================
const mode = ref('text')

// ==================== 模式 A：文字内容 ====================
const textDropRef = ref(null)
const uploadedFile = ref(null)
const fillMode = ref('mask')     // mask | erase
const textToRedact = ref('')
const scope = ref('all')
const pagesText = ref('')

// ==================== 模式 B：区域框选 ====================
const areaDropRef = ref(null)
const areaFile = ref(null)
const pages = ref([])
const sessionId = ref(null)
const preparing = ref(false)
const areaFill = ref('black')
const shape = ref('rect')
const zoom = ref(1)
const rects = ref([])
const dragging = ref(null)
let _nextId = 1

const areaPreviewFill = computed(() =>
  areaFill.value === 'black' ? '#000000' : '#ffffff'
)

// ==================== 通用 ====================
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (mode.value === 'text') {
    if (!uploadedFile.value) return false
    if (!textToRedact.value.trim()) return false
    if (scope.value === 'pages' && !pagesText.value.trim()) return false
    return true
  } else {
    return rects.value.length > 0 && !preparing.value
  }
})

// ==================== 模式 A：上传 ====================
function onTextFiles(files) {
  uploadedFile.value = files[0] || null
}

function onRemoveTextFile() {
  uploadedFile.value = null
}

// ==================== 模式 B：上传 + 预览 ====================
async function onAreaFiles(files) {
  const f = files[0]
  if (!f) return

  preparing.value = true
  areaFile.value = f
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/pdf-redact-area/prepare', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    sessionId.value = res.data.session_id
    pages.value = res.data.pages
    rects.value = []
  } catch (err) {
    const d = err.response?.data?.detail
    alert(typeof d === 'string' ? d : err.message)
    areaFile.value = null
  } finally {
    preparing.value = false
  }
}

const ZOOM_MIN = 0.5, ZOOM_MAX = 4, ZOOM_STEP = 0.25
function zoomIn() { zoom.value = Math.min(ZOOM_MAX, +(zoom.value + ZOOM_STEP).toFixed(2)) }
function zoomOut() { zoom.value = Math.max(ZOOM_MIN, +(zoom.value - ZOOM_STEP).toFixed(2)) }

// ==================== 模式 B：拖框 ====================
function onDown(e, pageMeta) {
  if (e.button !== 0) return
  e.preventDefault()

  const wrap = e.currentTarget
  const rect = wrap.getBoundingClientRect()
  const startX = (e.clientX - rect.left) / zoom.value
  const startY = (e.clientY - rect.top) / zoom.value

  dragging.value = {
    pageIndex: pageMeta.index,
    x0: startX, y0: startY, x1: startX, y1: startY,
  }

  const onMove = (ev) => {
    if (!dragging.value) return
    const x = Math.max(0, Math.min(pageMeta.preview_width, (ev.clientX - rect.left) / zoom.value))
    const y = Math.max(0, Math.min(pageMeta.preview_height, (ev.clientY - rect.top) / zoom.value))
    dragging.value.x1 = x
    dragging.value.y1 = y
  }

  const onUp = () => {
    if (!dragging.value) return
    const d = dragging.value
    const minSize = 5
    const w = Math.abs(d.x1 - d.x0)
    const h = Math.abs(d.y1 - d.y0)

    if (w >= minSize && h >= minSize) {
      const s = pageMeta.scale
      const dx0 = Math.min(d.x0, d.x1)
      const dy0 = Math.min(d.y0, d.y1)
      const dx1 = Math.max(d.x0, d.x1)
      const dy1 = Math.max(d.y0, d.y1)

      rects.value.push({
        _id: _nextId++,
        page: pageMeta.index,
        x0: dx0 * s, y0: dy0 * s, x1: dx1 * s, y1: dy1 * s,
        _dx0: dx0, _dy0: dy0, _dx1: dx1, _dy1: dy1,
      })
    }

    dragging.value = null
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function rectsOfPage(pageIndex) {
  return rects.value.filter(r => r.page === pageIndex)
}

function removeRect(id) {
  rects.value = rects.value.filter(r => r._id !== id)
}

function clearRects() {
  if (!confirm('确定清空所有已选框吗？')) return
  rects.value = []
}

function resetArea() {
  if (rects.value.length && !confirm('确定重新上传吗？当前已选区域会丢失。')) return
  pages.value = []
  rects.value = []
  sessionId.value = null
  areaFile.value = null
  zoom.value = 1
  result.value = null
  areaDropRef.value?.reset()
}

// ==================== 重置 ====================
function resetAll() {
  if (mode.value === 'text') {
    uploadedFile.value = null
    textToRedact.value = ''
    scope.value = 'all'
    pagesText.value = ''
    fillMode.value = 'mask'
  } else {
    resetArea()
    areaFill.value = 'black'
    shape.value = 'rect'
  }
  result.value = null
  loading.value = false
}

// ==================== 提交 ====================
async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null

  try {
    if (mode.value === 'text') {
      // 模式 A：调 /text-redact
      const fd = new FormData()
      fd.append('file', uploadedFile.value)
      fd.append('text_to_redact', textToRedact.value.trim())
      fd.append('redact_action', fillMode.value)
      fd.append('pages', scope.value === 'pages' ? pagesText.value : '')

      const res = await api.post('/text-redact', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      result.value = { success: true, message: res.data.message || '处理完成' }
    } else {
      // 模式 B：调 /pdf-redact-area/apply
      const payload = rects.value.map(r => ({
        page: r.page, x0: r.x0, y0: r.y0, x1: r.x1, y1: r.y1,
      }))
      const fd = new FormData()
      fd.append('session_id', sessionId.value)
      fd.append('rects_json', JSON.stringify(payload))
      fd.append('fill_mode', areaFill.value)
      fd.append('shape', shape.value)

      const res = await api.post('/pdf-redact-area/apply', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      result.value = { success: true, message: res.data.message || '遮掩完成' }
    }
    emit('submitted')
  } catch (err) {
    let msg = '请求失败'
    const d = err.response?.data?.detail
    if (typeof d === 'string') msg = d
    else if (Array.isArray(d)) msg = d[0]?.msg || msg
    else if (err.message) msg = err.message
    result.value = { success: false, message: msg }
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', () => {})
  document.removeEventListener('mouseup', () => {})
})
</script>

<style scoped>
/* 区域框选工具栏 */
.area-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.area-stats { font-size: 14px; color: #1e3a8a; }
.area-stats b { color: #1e40af; font-weight: 700; }
.area-file { color: #6b7280; font-size: 12px; }
.area-actions { display: flex; gap: 8px; }

.area-zoom {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #1e3a8a;
}
.zoom-label { font-weight: 500; }
.zoom-btn {
  width: 28px; height: 28px;
  border: 1px solid #bfdbfe; background: #fff; color: #1e40af;
  border-radius: 6px; font-size: 16px; font-weight: 700; cursor: pointer;
}
.zoom-btn:hover { background: #dbeafe; }
.zoom-value {
  min-width: 48px; text-align: center; font-weight: 600; color: #1e40af;
}
.zoom-reset {
  padding: 4px 10px; border: 1px solid #bfdbfe; background: #fff;
  color: #1e40af; border-radius: 6px; font-size: 12px; cursor: pointer;
}
.zoom-reset:hover { background: #dbeafe; }

/* 预览列表 */
.pages-list {
  display: flex; flex-direction: column; gap: 20px;
  margin-top: 16px; max-height: 700px; overflow-y: auto;
  padding-right: 8px;
}
.page-item {
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px; padding: 12px; background: #fafbfc;
}
.page-header {
  font-size: 13px; font-weight: 600; color: var(--text-primary, #111827);
  margin-bottom: 8px; display: flex; align-items: center; gap: 8px;
}
.page-badge {
  font-size: 11px; color: #4f46e5; background: #eef2ff;
  padding: 2px 8px; border-radius: 10px; font-weight: 500;
}

.canvas-outer {
  position: relative; background: #fff; border: 1px solid #e5e7eb;
  border-radius: 4px; overflow: hidden; display: inline-block;
}
.canvas-wrap {
  position: absolute; top: 0; left: 0; user-select: none; cursor: crosshair;
}
.page-img { display: block; pointer-events: none; user-select: none; }
.page-svg { position: absolute; top: 0; left: 0; pointer-events: none; }
.area-shape { pointer-events: auto; cursor: pointer; }
</style>