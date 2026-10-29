<template>
  <div class="action-bar">
    <button
      class="btn-primary"
      :disabled="!canSubmit || loading"
      @click="$emit('submit')"
    >
      <span v-if="loading" class="spinner"></span>
      <span v-else class="btn-icon">🚀</span>
      <span v-if="loading" class="btn-text">{{ loadingText }}</span>
      <span v-else class="btn-text">{{ submitText }}</span>
    </button>
    <button class="btn-secondary" @click="$emit('reset')">
      <span class="btn-icon">🔄</span>
      <span class="btn-text">重置</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  canSubmit:   { type: Boolean, default: false },
  loading:     { type: Boolean, default: false },
  submitText:  { type: String,  default: '开始处理' },
  loadingText: { type: String,  default: '处理中...' },
})

defineEmits(['submit', 'reset'])
</script>