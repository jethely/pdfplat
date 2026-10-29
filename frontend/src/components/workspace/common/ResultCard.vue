<template>
  <div v-if="result" class="result-section">
    <div :class="['result-card', result.success ? 'success' : 'error']">
      <span class="result-icon">{{ result.success ? '✅' : '❌' }}</span>
      <div class="result-body">
        <h4>{{ result.success ? '处理成功' : '处理失败' }}</h4>
        <p class="result-msg">{{ result.message }}</p>
        <p v-if="result.success && showHint" class="result-hint">
          生成的文件已保存到下方「我的文件」，可展开下载。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  result:   { type: Object,  default: null },
  showHint: { type: Boolean, default: true },
})
</script>