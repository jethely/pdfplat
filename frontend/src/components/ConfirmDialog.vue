<template>
  <Teleport to="body">
    <transition name="dlg-fade">
      <div v-if="visible" class="dlg-overlay" @click.self="onCancel">
        <div class="dlg-box">
          <div class="dlg-icon">{{ danger ? '⚠️' : '❓' }}</div>
          <h3 class="dlg-title">{{ title }}</h3>
          <p class="dlg-message" v-html="message"></p>
          <div class="dlg-actions">
            <button class="dlg-btn cancel" @click="onCancel">
              {{ cancelText }}
            </button>
            <button
              class="dlg-btn"
              :class="danger ? 'danger' : 'primary'"
              @click="onConfirm"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
defineProps({
  visible:     { type: Boolean, default: false },
  title:       { type: String,  default: '确认操作' },
  message:     { type: String,  default: '' },
  confirmText: { type: String,  default: '确定' },
  cancelText:  { type: String,  default: '取消' },
  danger:      { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

function onConfirm() {
  emit('update:visible', false)
  emit('confirm')
}
function onCancel() {
  emit('update:visible', false)
  emit('cancel')
}
</script>

<style scoped>
.dlg-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.dlg-box {
  background: #fff;
  border-radius: 14px;
  padding: 26px 24px 20px;
  width: 100%;
  max-width: 380px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
}

.dlg-icon {
  font-size: 40px;
  line-height: 1;
  margin-bottom: 12px;
}

.dlg-title {
  font-size: 17px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 10px;
}

.dlg-message {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 22px;
}
.dlg-message :deep(.strong) {
  color: #111827;
  font-weight: 600;
}

.dlg-actions {
  display: flex;
  gap: 10px;
}

.dlg-btn {
  flex: 1;
  padding: 10px 0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s;
}
.dlg-btn.cancel {
  background: #f3f4f6;
  color: #374151;
  border-color: #e5e7eb;
}
.dlg-btn.cancel:hover { background: #e5e7eb; }

.dlg-btn.primary {
  background: #4f46e5;
  color: #fff;
}
.dlg-btn.primary:hover { background: #4338ca; }

.dlg-btn.danger {
  background: #dc2626;
  color: #fff;
}
.dlg-btn.danger:hover { background: #b91c1c; }

.dlg-fade-enter-active,
.dlg-fade-leave-active { transition: opacity 0.15s ease; }
.dlg-fade-enter-from,
.dlg-fade-leave-to { opacity: 0; }
</style>