<template>
  <div class="tool-pdf-encrypt">
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

    <!-- 打开密码 -->
    <div class="form-section">
      <label class="form-label">打开密码（必填，打开 PDF 时需输入）</label>
      <input
        v-model="password"
        type="password"
        class="form-input"
        placeholder="请输入打开密码"
        autocomplete="new-password"
        maxlength="64"
      />
    </div>

    <!-- 确认密码 -->
    <div class="form-section">
      <label class="form-label">确认打开密码</label>
      <input
        v-model="password2"
        type="password"
        class="form-input"
        placeholder="请再次输入打开密码"
        autocomplete="new-password"
        maxlength="64"
      />
      <p v-if="passwordMismatch" class="form-hint error-hint">
        ⚠️ 两次输入的密码不一致
      </p>
    </div>

    <!-- 权限密码 -->
    <div class="form-section">
      <label class="form-label">权限密码（可选，用于修改权限设置）</label>
      <input
        v-model="ownerPassword"
        type="password"
        class="form-input"
        placeholder="留空则自动生成随机权限密码"
        autocomplete="new-password"
        maxlength="64"
      />
      <p class="form-hint">
        拥有权限密码的人可以修改权限（打印、复制等）。留空则用随机值，更安全。
      </p>
    </div>

    <!-- 权限级别 -->
    <div class="form-section">
      <label class="form-label">权限级别</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="permLevel" value="all" />
          <span><b>全权限</b> — 仅加密，不限制任何操作</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="permLevel" value="print-only" />
          <span><b>仅阅读 + 打印</b> — 禁止复制、修改、批注</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="permLevel" value="readonly" />
          <span><b>仅阅读</b> — 禁止打印、复制、修改等所有操作</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="permLevel" value="custom" />
          <span><b>自定义</b> — 逐项选择允许的操作</span>
        </label>
      </div>
    </div>

    <!-- 自定义权限 -->
    <div v-if="permLevel === 'custom'" class="form-section">
      <label class="form-label">允许的操作</label>
      <div class="checkbox-grid">
        <label class="checkbox-item">
          <input type="checkbox" v-model="permPrint" />
          <span>打印</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="permCopy" />
          <span>复制文字</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="permModify" />
          <span>修改内容</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="permAnnotate" />
          <span>添加批注</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="permForm" />
          <span>填写表单</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="permAccessibility" />
          <span>无障碍访问</span>
        </label>
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
const password = ref('')
const password2 = ref('')
const ownerPassword = ref('')
const permLevel = ref('all')
const permPrint = ref(true)
const permCopy = ref(true)
const permModify = ref(true)
const permAnnotate = ref(true)
const permForm = ref(true)
const permAccessibility = ref(true)
const loading = ref(false)
const result = ref(null)

const passwordMismatch = computed(() =>
  password.value && password2.value && password.value !== password2.value
)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (!password.value) return false
  if (password.value !== password2.value) return false
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
  password.value = ''
  password2.value = ''
  ownerPassword.value = ''
  permLevel.value = 'all'
  permPrint.value = true
  permCopy.value = true
  permModify.value = true
  permAnnotate.value = true
  permForm.value = true
  permAccessibility.value = true
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
    fd.append('password', password.value)
    fd.append('owner_password', ownerPassword.value)
    fd.append('perm_level', permLevel.value)
    fd.append('perm_print', String(permPrint.value))
    fd.append('perm_copy', String(permCopy.value))
    fd.append('perm_modify', String(permModify.value))
    fd.append('perm_annotate', String(permAnnotate.value))
    fd.append('perm_form', String(permForm.value))
    fd.append('perm_accessibility', String(permAccessibility.value))

    const res = await api.post('/pdf-encrypt', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '加密完成',
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