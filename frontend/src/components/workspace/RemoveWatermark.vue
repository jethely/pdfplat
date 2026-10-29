<template>
  <div class="tool-remove-watermark">
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
      <FileList :files="file ? [file] : []" icon="📄" @remove="onRemove" />
    </div>

    <!-- 现实提示 -->
    <div class="form-section warn-banner">
      ⚠️ 只支持**文字型水印**（PDF 文字对象）。<br>
      **图片水印、扫描件水印无法去除**——这是业界难题，任何工具都做不到完美。
    </div>

    <!-- 策略 -->
    <div class="form-section">
      <label class="form-label">去除策略</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="strategy" value="auto" />
          <span><b>按文字内容去除（推荐）</b> — 输入水印文字，自动找到并删除</span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="B" disabled />
          <span><b>按样式特征识别</b> — 自动检测疑似水印<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="C" disabled />
          <span><b>图像处理修复</b> — 图片水印/AI 修复<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
      </div>
    </div>

    <!-- 水印文字 -->
    <div class="form-section">
      <label class="form-label">要去除的水印文字</label>
      <input
        v-model="text"
        type="text"
        class="form-input"
        placeholder="例：机密 / 内部资料 / 公司名称"
      />
      <p class="form-hint">
        精确匹配。同名文字会全部去除。
      </p>
    </div>

    <!-- 填充方式 -->
    <div class="form-section">
      <label class="form-label">填充方式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="fillMode" value="auto" />
          <span><b>自动（推荐）</b> — 从水印周围采样背景色填充</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fillMode" value="white" />
          <span><b>纯白色</b> — 适用于白底 PDF</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fillMode" value="custom" />
          <span><b>自定义颜色</b></span>
        </label>
      </div>

      <div v-if="fillMode === 'custom'" style="margin-top: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <input type="color" v-model="customColor" class="color-picker" />
          <code>{{ customColor }}</code>
        </div>
      </div>
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
        <p class="form-hint">页码用逗号分隔，支持范围。</p>
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
const strategy = ref('auto')
const text = ref('')
const fillMode = ref('auto')
const customColor = ref('#ffffff')
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

function onFiles(files) { file.value = files[0] || null }
function onRemove() { file.value = null; dropRef.value?.reset() }
function reset() {
  text.value = ''
  fillMode.value = 'auto'
  customColor.value = '#ffffff'
  scope.value = 'all'
  pages.value = ''
  result.value = null
  loading.value = false
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('strategy', strategy.value)
    fd.append('text', text.value.trim())
    fd.append('fill_mode', fillMode.value)
    fd.append('custom_color', customColor.value)
    fd.append('pages', scope.value === 'pages' ? pages.value : '')

    const res = await api.post('/remove-watermark', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = { success: true, message: res.data.message }
    emit('submitted')
  } catch (err) {
    const d = err.response?.data?.detail
    result.value = {
      success: false,
      message: typeof d === 'string' ? d : err.message,
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.radio-item.disabled { opacity: 0.55; cursor: not-allowed; }
.color-picker {
  width: 60px;
  height: 36px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  cursor: pointer;
  background: none;
}
</style>