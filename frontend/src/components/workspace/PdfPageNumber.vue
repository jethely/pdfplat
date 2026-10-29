<template>
  <div class="tool-pdf-page-number">
    <!-- 选择文件 -->
    <div class="form-section">
      <label class="form-label">选择 PDF 文件</label>
      <DropZone
        ref="dropRef"
        accept=".pdf"
        icon="📁"
        text="拖拽 PDF 文件到此处，或点击选择"
        @files="onFiles"
      />
      <FileList
        :files="file ? [file] : []"
        icon="📄"
        @remove="onRemove"
      />
    </div>

    <!-- 页码格式 -->
    <div class="form-section">
      <label class="form-label">页码格式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="n" />
          <span>1, 2, 3...（纯数字）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="n/m" />
          <span>1/20（数字/总数）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="n-m" />
          <span>1-20（数字-总数）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="di-n-ye" />
          <span>第 N 页</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="di-n-ye-gong-m-ye" />
          <span>第 N 页 / 共 M 页</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="page-n" />
          <span>Page N</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fmt" value="page-n-of-m" />
          <span>Page N of M</span>
        </label>
      </div>
    </div>

    <!-- 位置 -->
    <div class="form-section">
      <label class="form-label">位置</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model="position" value="bottom-center" />
          <span>底部居中</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="bottom-right" />
          <span>底部右</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="bottom-left" />
          <span>底部左</span>
        </label>
      </div>
      <div class="radio-group" style="margin-top: 10px;">
        <label class="radio-item">
          <input type="radio" v-model="position" value="top-center" />
          <span>顶部居中</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="top-right" />
          <span>顶部右</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="top-left" />
          <span>顶部左</span>
        </label>
      </div>
    </div>

    <!-- 起始编号 -->
    <div class="form-section">
      <label class="form-label">起始编号</label>
      <input
        v-model.number="startNumber"
        type="number"
        min="0"
        class="form-input"
        style="max-width: 160px;"
      />
      <p class="form-hint">
        从该数字开始编号。比如从第 5 页开始标 "1"，这里填 1 并在下方跳过前 4 页。
      </p>
    </div>

    <!-- 应用范围 -->
    <div class="form-section">
      <label class="form-label">应用范围</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="scope" value="all" />
          <span>全部页面</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="scope" value="skip-first" />
          <span>跳过前 N 页（封面等）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="scope" value="pages" />
          <span>指定页面</span>
        </label>
      </div>

      <div v-if="scope === 'skip-first'" style="margin-top: 12px;">
        <input
          v-model.number="skipFirst"
          type="number"
          min="0"
          class="form-input"
          style="max-width: 160px;"
        />
        <p class="form-hint">
          例：填 1 则第 1 页不标页码，从第 2 页开始。
        </p>
      </div>

      <div v-if="scope === 'pages'" style="margin-top: 12px;">
        <input
          v-model="pages"
          type="text"
          class="form-input"
          placeholder="例: 2, 3, 5-7"
        />
        <p class="form-hint">
          指定页码才会被标号，未指定的页保持原样。
        </p>
      </div>
    </div>

    <!-- 字号 / 颜色 / 边距 -->
    <div class="form-section">
      <label class="form-label">字号：{{ fontsize }} pt</label>
      <input
        v-model.number="fontsize"
        type="range"
        min="6" max="48" step="1"
        class="slider"
      />
    </div>

    <div class="form-section">
      <label class="form-label">颜色</label>
      <div style="display: flex; align-items: center; gap: 10px;">
        <input type="color" v-model="color" class="color-picker" />
        <code>{{ color }}</code>
      </div>
    </div>

    <div class="form-section">
      <label class="form-label">边距：{{ margin }} px</label>
      <input
        v-model.number="margin"
        type="range"
        min="10" max="120" step="5"
        class="slider"
      />
      <p class="form-hint">
        页码距离页面边缘的距离。
      </p>
    </div>

    <ActionBar
      :can-submit="canSubmit"
      :loading="loading"
      @submit="submit"
      @reset="reset"
    />

    <ResultCard :result="result" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import FileList from './common/FileList.vue'
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])

const dropRef = ref(null)
const file = ref(null)
const fmt = ref('n')
const position = ref('bottom-center')
const startNumber = ref(1)
const scope = ref('all')
const skipFirst = ref(1)
const pages = ref('')
const fontsize = ref(8)
const color = ref('#000000')
const margin = ref(30)
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (scope.value === 'pages' && !pages.value.trim()) return false
  return true
})

function onFiles(files) {
  file.value = files[0] || null
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
}

function reset() {
  file.value = null
  fmt.value = 'n'
  position.value = 'bottom-center'
  startNumber.value = 1
  scope.value = 'all'
  skipFirst.value = 1
  pages.value = ''
  fontsize.value = 8
  color.value = '#000000'
  margin.value = 30
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('fmt', fmt.value)
    fd.append('position', position.value)
    fd.append('start_number', String(startNumber.value))
    fd.append('fontsize', String(fontsize.value))
    fd.append('color', color.value)
    fd.append('margin', String(margin.value))

    if (scope.value === 'pages') {
      fd.append('pages', pages.value)
      fd.append('skip_first', '0')
    } else if (scope.value === 'skip-first') {
      fd.append('pages', '')
      fd.append('skip_first', String(skipFirst.value))
    } else {
      fd.append('pages', '')
      fd.append('skip_first', '0')
    }

    const res = await api.post('/pdf-page-number', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '页码添加完成',
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
</script>

<style scoped>
.slider {
  width: 100%;
  max-width: 480px;
  cursor: pointer;
}
.color-picker {
  width: 60px;
  height: 36px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  cursor: pointer;
  background: none;
}
</style>