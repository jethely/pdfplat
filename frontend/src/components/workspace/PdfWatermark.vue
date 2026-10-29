<template>
  <div class="tool-pdf-watermark">
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

    <!-- 水印文字 -->
    <div class="form-section">
      <label class="form-label">水印文字</label>
      <input
        v-model="text"
        type="text"
        class="form-input"
        placeholder="例：机密 / 内部资料 / 公司名称"
        maxlength="100"
      />
    </div>

    <!-- 位置 -->
    <div class="form-section">
      <label class="form-label">位置</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="position" value="center" />
          <span>居中（大标题水印）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="tile" />
          <span>平铺（密集重复，适合防泄密）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="top-left" />
          <span>左上角</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="top-right" />
          <span>右上角</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="bottom-left" />
          <span>左下角</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="position" value="bottom-right" />
          <span>右下角</span>
        </label>
      </div>
    </div>

    <!-- 旋转角度 -->
    <div class="form-section">
      <label class="form-label">旋转角度</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model.number="rotation" :value="0" />
          <span>水平 0°</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="rotation" :value="30" />
          <span>30°</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="rotation" :value="45" />
          <span>45°（推荐）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="rotation" :value="-45" />
          <span>-45°</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="rotation" :value="90" />
          <span>垂直 90°</span>
        </label>
      </div>
    </div>

    <!-- 字号 / 颜色 / 透明度 -->
    <div class="form-section">
      <label class="form-label">字号：{{ fontsize }} pt</label>
      <input
        v-model.number="fontsize"
        type="range"
        min="20" max="200" step="5"
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
      <label class="form-label">透明度：{{ (opacity * 100).toFixed(0) }}%</label>
      <input
        v-model.number="opacity"
        type="range"
        min="0.05" max="1" step="0.05"
        class="slider"
      />
      <p class="form-hint">
        透明度越低，水印越浅淡；建议 20%~40%。
      </p>
    </div>

    <!-- 页码范围 -->
    <div class="form-section">
      <label class="form-label">应用范围</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="scope" value="all" />
          <span>全部页面</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="scope" value="pages" />
          <span>指定页面</span>
        </label>
      </div>
      <div v-if="scope === 'pages'" style="margin-top: 12px;">
        <input
          v-model="pages"
          type="text"
          class="form-input"
          placeholder="例: 1, 3, 5-7"
        />
        <p class="form-hint">
          页码用逗号分隔，支持范围（如 <code>1-3</code>）。
        </p>
      </div>
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
const text = ref('机密')
const position = ref('center')
const rotation = ref(45)
const fontsize = ref(60)
const color = ref('#888888')
const opacity = ref(0.3)
const scope = ref('all')
const pages = ref('')
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (!text.value.trim()) return false
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
  text.value = '机密'
  position.value = 'center'
  rotation.value = 45
  fontsize.value = 60
  color.value = '#888888'
  opacity.value = 0.3
  scope.value = 'all'
  pages.value = ''
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
    fd.append('text', text.value.trim())
    fd.append('position', position.value)
    fd.append('rotation', String(rotation.value))
    fd.append('fontsize', String(fontsize.value))
    fd.append('color', color.value)
    fd.append('opacity', String(opacity.value))
    fd.append('pages', scope.value === 'pages' ? pages.value : '')

    const res = await api.post('/pdf-watermark', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '水印添加完成',
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