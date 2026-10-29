<template>
  <div class="tool-pdf-decrypt">
    <!-- 警告 -->
    <div class="form-section warn-banner">
      ⚠️ 本功能仅供破解您本人遗忘密码的 PDF。请勿用于他人文件。
    </div>

    <!-- 选择文件 -->
    <div class="form-section">
      <label class="form-label">选择已加密的 PDF 文件</label>
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

    <!-- 破解模式 -->
    <div class="form-section">
      <label class="form-label">破解方式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="crackMode" value="smart" />
          <span><b>智能尝试（推荐）</b> — 空密码 → 常见弱密码 → 短数字</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="crackMode" value="dictionary" />
          <span><b>字典破解</b> — 从内置字典或自定义字典中尝试</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="crackMode" value="brute" />
          <span><b>暴力破解</b> — 指定字符集和长度范围</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="crackMode" value="mask" />
          <span><b>掩码破解</b> — 已知部分 + 未知部分（?）</span>
        </label>
      </div>
    </div>

    <!-- 字典模式 -->
    <div v-if="crackMode === 'dictionary'" class="form-section">
      <label class="form-label">字典来源</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="dictSource" value="builtin-simple" />
          <span><b>内置简单</b> — 常见弱密码 + 4/6 位纯数字</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="dictSource" value="builtin-medium" />
          <span><b>内置中等</b> — 需管理员放置字典文件</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="dictSource" value="builtin-complex" />
          <span><b>内置复杂</b> — 需管理员放置字典文件</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="dictSource" value="custom" />
          <span><b>自定义上传</b></span>
        </label>
      </div>

      <div v-if="dictSource === 'custom'" style="margin-top: 14px;">
        <label class="form-label">上传字典文件（每行一个密码）</label>
        <input
          type="file"
          accept=".txt,.dict,.dic"
          ref="dictInputRef"
          @change="onDictFile"
          class="native-file-input"
        />
        <FileList
          :files="dictFile ? [dictFile] : []"
          icon="📝"
        />
        <p class="form-hint">
          上传的字典会保存到您的专属目录，多个任务可复用
        </p>
      </div>
    </div>

    <!-- 暴力模式 -->
    <div v-if="crackMode === 'brute'" class="form-section">
      <label class="form-label">字符集</label>
      <div class="checkbox-grid">
        <label class="checkbox-item">
          <input type="checkbox" v-model="bruteDigits" />
          <span>数字 0-9</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="bruteLower" />
          <span>小写字母</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="bruteUpper" />
          <span>大写字母</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="bruteSymbols" />
          <span>特殊符号</span>
        </label>
      </div>
      <label class="form-label" style="margin-top: 14px;">长度范围</label>
      <div style="display: flex; align-items: center; gap: 10px;">
        <input
          v-model.number="bruteMinLen"
          type="number" min="1" max="11"
          class="form-input" style="width: 80px;" />
        <span>~</span>
        <input
          v-model.number="bruteMaxLen"
          type="number" min="1" max="11"
          class="form-input" style="width: 80px;" />
        <span class="form-hint" style="margin: 0;">（最长 11 位，适合手机号）</span>
      </div>
      <p class="form-hint">
        ⚠️ 11 位纯数字有 1000 亿种，正常机器要跑几天几夜。建议先用掩码模式缩小范围。
      </p>
    </div>

    <!-- 掩码模式 -->
    <div v-if="crackMode === 'mask'" class="form-section">
      <label class="form-label">掩码（? = 未知位）</label>
      <input
        v-model="maskPattern"
        type="text"
        class="form-input"
        placeholder="例：138????????  或  ????????1234"
        maxlength="16"
      />
      <label class="form-label" style="margin-top: 14px;">未知位字符集</label>
      <div class="checkbox-grid">
        <label class="checkbox-item">
          <input type="checkbox" v-model="maskDigits" />
          <span>数字 0-9</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="maskLower" />
          <span>小写字母</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" v-model="maskUpper" />
          <span>大写字母</span>
        </label>
      </div>
      <p class="form-hint">
        示例：<br>
        • 手机号前 3 位已知 → <code>138????????</code>（11 位）<br>
        • 手机号后 4 位已知 → <code>???????1234</code>（11 位）<br>
        • 8 位纯数字密码 → <code>????????</code>
      </p>
    </div>

    <!-- 运行中的进度面板 -->
    <div v-if="crackTaskId && crackStatus && crackStatus.status === 'running'" class="form-section crack-panel">
      <div class="crack-header">
        <span class="crack-spinner"></span>
        <span>正在破解…（{{ crackStatus.phase }}）</span>
      </div>
      <div class="crack-progress-bar">
        <div class="crack-progress-fill" :style="{ width: (crackStatus.progress * 100) + '%' }"></div>
      </div>
      <div class="crack-stats">
        <div>已尝试：<b>{{ crackStatus.attempts.toLocaleString() }}</b> 次</div>
        <div v-if="crackStatus.total_estimate">
          总数：<b>{{ crackStatus.total_estimate.toLocaleString() }}</b>
        </div>
        <div>速度：<b>{{ crackStatus.speed.toLocaleString() }}</b> 次/秒</div>
        <div>已用时：<b>{{ formatDuration(crackStatus.elapsed) }}</b></div>
        <div v-if="crackStatus.eta_seconds">
          预计剩余：<b>{{ formatDuration(crackStatus.eta_seconds) }}</b>
        </div>
        <div v-if="crackStatus.workers">
          并行：<b>{{ crackStatus.workers }}</b> 线程
          <span v-if="crackStatus.hardware" style="color: #6b7280;">
            （CPU {{ crackStatus.hardware.cpu_logical }} 核 × {{ crackStatus.hardware.cpu_target_pct }}%）
          </span>
        </div>
      </div>
      <button class="btn-ghost danger" @click="cancelCrack">⏹ 取消</button>
    </div>

    <!-- 破解成功 -->
    <div v-if="crackStatus && crackStatus.status === 'done' && crackStatus.success" class="result-card success" style="margin-top: 16px;">
      <span class="result-icon">✅</span>
      <div class="result-body">
        <h4>破解成功！</h4>
        <p class="result-msg">
          找到密码：<code class="crack-password">{{ crackStatus.found_password }}</code>
        </p>
        <p class="result-hint">
          用时 {{ formatDuration(crackStatus.elapsed) }}，
          共尝试 {{ crackStatus.attempts.toLocaleString() }} 次
        </p>
        <button class="btn-primary" style="margin-top: 12px;" @click="applyDecrypt" :disabled="loading">
          🔓 用此密码解密并保存
        </button>
      </div>
    </div>

    <!-- 破解完成：未找到 -->
    <div v-if="crackStatus && crackStatus.status === 'done' && !crackStatus.success" class="result-card error" style="margin-top: 16px;">
      <span class="result-icon">❌</span>
      <div class="result-body">
        <h4>未找到密码</h4>
        <p class="result-msg">{{ crackStatus.error }}</p>
        <p class="result-hint">
          已尝试 {{ crackStatus.attempts.toLocaleString() }} 次，用时 {{ formatDuration(crackStatus.elapsed) }}
        </p>
      </div>
    </div>

    <!-- 破解失败（出错） -->
    <div v-if="crackStatus && crackStatus.status === 'failed'" class="result-card error" style="margin-top: 16px;">
      <span class="result-icon">❌</span>
      <div class="result-body">
        <h4>破解失败</h4>
        <p class="result-msg">{{ crackStatus.error }}</p>
      </div>
    </div>

    <!-- 已取消 -->
    <div v-if="crackStatus && crackStatus.status === 'cancelled'" class="result-card error" style="margin-top: 16px;">
      <span class="result-icon">⏹</span>
      <div class="result-body">
        <h4>已取消</h4>
        <p class="result-hint">
          已尝试 {{ crackStatus.attempts.toLocaleString() }} 次，用时 {{ formatDuration(crackStatus.elapsed) }}
        </p>
      </div>
    </div>

    <!-- 服务重启中断 -->
    <div v-if="crackStatus && crackStatus.status === 'interrupted'" class="result-card error" style="margin-top: 16px;">
      <span class="result-icon">⚠️</span>
      <div class="result-body">
        <h4>任务已中断</h4>
        <p class="result-msg">{{ crackStatus.error || '服务重启，任务未完成' }}</p>
        <p class="result-hint">
          已尝试 {{ crackStatus.attempts.toLocaleString() }} 次
        </p>
      </div>
    </div>

    <!-- 操作按钮（破解进行中时隐藏） -->
    <ActionBar
      v-if="!isRunning"
      :can-submit="canSubmit"
      :loading="loading"
      @submit="startCrack"
      @reset="reset"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import FileList from './common/FileList.vue'
import ActionBar from './common/ActionBar.vue'

const emit = defineEmits(['submitted'])

const dropRef = ref(null)
const file = ref(null)

// 破解参数
const crackMode = ref('smart')
const dictSource = ref('builtin-simple')
const dictFile = ref(null)
const dictInputRef = ref(null)
const bruteDigits = ref(true)
const bruteLower = ref(false)
const bruteUpper = ref(false)
const bruteSymbols = ref(false)
const bruteMinLen = ref(1)
const bruteMaxLen = ref(6)
const maskPattern = ref('')
const maskDigits = ref(true)
const maskLower = ref(false)
const maskUpper = ref(false)

// 任务状态
const crackTaskId = ref(null)
const crackStatus = ref(null)
const loading = ref(false)
let pollTimer = null

const isRunning = computed(
  () => crackTaskId.value && crackStatus.value?.status === 'running'
)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (isRunning.value) return false
  if (crackMode.value === 'dictionary' && dictSource.value === 'custom') {
    if (!dictFile.value) return false
  }
  return true
})

// ============ 上传 ============
function onFiles(files) {
  file.value = files[0] || null
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
}

function onDictFile(e) {
  dictFile.value = e.target.files?.[0] || null
}

// ============ 字符集 ============
function buildBruteCharset() {
  let cs = ''
  if (bruteDigits.value) cs += '0123456789'
  if (bruteLower.value) cs += 'abcdefghijklmnopqrstuvwxyz'
  if (bruteUpper.value) cs += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  if (bruteSymbols.value) cs += '!@#$%^&*()_+-=[]{}|;:,.<>?'
  return cs
}

function buildMaskCharset() {
  let cs = ''
  if (maskDigits.value) cs += '0123456789'
  if (maskLower.value) cs += 'abcdefghijklmnopqrstuvwxyz'
  if (maskUpper.value) cs += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  return cs
}

// ============ 破解流程 ============
async function startCrack() {
  if (!file.value) return
  if (isRunning.value) return

  loading.value = true

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('mode', crackMode.value)

    if (crackMode.value === 'dictionary') {
      fd.append('dict_source', dictSource.value)
      if (dictSource.value === 'custom') {
        if (!dictFile.value) {
          alert('请上传字典文件')
          loading.value = false
          return
        }
        fd.append('dict_file', dictFile.value)
      }
    }

    if (crackMode.value === 'brute') {
      const cs = buildBruteCharset()
      if (!cs) {
        alert('请至少选择一种字符集')
        loading.value = false
        return
      }
      if (bruteMinLen.value < 1 || bruteMaxLen.value < bruteMinLen.value || bruteMaxLen.value > 11) {
        alert('长度范围需在 1~11 之间')
        loading.value = false
        return
      }
      fd.append('charset', cs)
      fd.append('min_len', String(bruteMinLen.value))
      fd.append('max_len', String(bruteMaxLen.value))
    }

    if (crackMode.value === 'mask') {
      if (!maskPattern.value || !maskPattern.value.includes('?')) {
        alert('掩码必须包含至少一个 ?')
        loading.value = false
        return
      }
      const cs = buildMaskCharset()
      if (!cs) {
        alert('请至少选择一种字符集')
        loading.value = false
        return
      }
      fd.append('mask', maskPattern.value)
      fd.append('charset', cs)
    }

    const res = await api.post('/pdf-decrypt/start', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    crackTaskId.value = res.data.task_id
    crackStatus.value = {
      status: 'running',
      phase: '初始化',
      attempts: 0,
      speed: 0,
      progress: 0,
      elapsed: 0,
      total_estimate: null,
      eta_seconds: null,
      found_password: null,
      success: null,
      error: null,
      workers: 0,
      hardware: null,
    }
    startPolling()
  } catch (err) {
    const d = err.response?.data?.detail
    alert(typeof d === 'string' ? d : err.message)
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!crackTaskId.value) {
      stopPolling()
      return
    }
    try {
      const res = await api.get(`/pdf-decrypt/status/${crackTaskId.value}`)
      crackStatus.value = res.data
      if (res.data.status !== 'running') {
        stopPolling()
      }
    } catch (e) {
      if (e.response?.status === 404) stopPolling()
    }
  }, 500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function cancelCrack() {
  if (!crackTaskId.value) return
  if (!confirm('确定要取消破解吗？')) return
  try {
    await api.post(`/pdf-decrypt/cancel/${crackTaskId.value}`)
  } catch (e) {
    console.warn(e)
  }
}

async function applyDecrypt() {
  if (!crackTaskId.value) return
  loading.value = true
  try {
    const res = await api.post(`/pdf-decrypt/apply/${crackTaskId.value}`)
    alert(res.data.message || '解密完成')
    emit('submitted')
  } catch (err) {
    const d = err.response?.data?.detail
    alert(typeof d === 'string' ? d : err.message)
  } finally {
    loading.value = false
  }
}

// ============ 恢复上次任务 ============
async function restoreCrackTask() {
  if (crackTaskId.value) return
  try {
    const res = await api.get('/pdf-decrypt/tasks')
    const tasks = res.data.tasks || []
    if (!tasks.length) return
    const latest = tasks[0]
    crackTaskId.value = latest.task_id
    crackStatus.value = {
      status: latest.status,
      phase: latest.phase,
      attempts: latest.attempts,
      speed: latest.speed,
      progress: latest.progress,
      elapsed: latest.elapsed,
      total_estimate: latest.total_estimate,
      eta_seconds: latest.eta_seconds,
      found_password: latest.found_password,
      success: latest.success,
      error: latest.error,
      workers: latest.workers,
      hardware: latest.hardware,
    }
    if (latest.status === 'running') {
      startPolling()
    }
  } catch (e) {
    console.warn('恢复破解任务失败', e)
  }
}

// ============ 重置 ============
function reset() {
  file.value = null
  crackMode.value = 'smart'
  dictSource.value = 'builtin-simple'
  dictFile.value = null
  bruteDigits.value = true
  bruteLower.value = false
  bruteUpper.value = false
  bruteSymbols.value = false
  bruteMinLen.value = 1
  bruteMaxLen.value = 6
  maskPattern.value = ''
  maskDigits.value = true
  maskLower.value = false
  maskUpper.value = false
  crackTaskId.value = null
  crackStatus.value = null
  stopPolling()
  if (dictInputRef.value) dictInputRef.value.value = ''
  dropRef.value?.reset()
}

// ============ 时长格式化 ============
function formatDuration(sec) {
  if (!sec && sec !== 0) return '—'
  sec = Math.floor(sec)
  if (sec < 60) return `${sec} 秒`
  if (sec < 3600) return `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h} 小时 ${m} 分`
}

// ============ 生命周期 ============
onMounted(() => {
  restoreCrackTask()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>