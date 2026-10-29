<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Tab -->
      <div class="auth-tabs">
        <button
          :class="['auth-tab', { active: mode === 'login' }]"
          @click="switchMode('login')"
        >登录</button>
        <button
          :class="['auth-tab', { active: mode === 'register' }]"
          @click="switchMode('register')"
        >注册</button>
      </div>

      <h2 class="auth-heading">
        {{ mode === 'login' ? '欢迎回来' : '创建新账号' }}
      </h2>

      <form @submit.prevent="submit">
        <div class="form-section">
          <label class="form-label">用户名</label>
          <input
            ref="usernameRef"
            v-model="username"
            class="form-input"
            :placeholder="mode === 'register' ? '3~32 位' : '请输入用户名'"
            autocomplete="username"
            maxlength="32"
          />
        </div>

        <div class="form-section">
          <label class="form-label">密码</label>
          <div class="password-wrap">
            <input
              v-model="password"
              :type="showPwd ? 'text' : 'password'"
              class="form-input"
              :placeholder="mode === 'register' ? '至少 8 位' : '请输入密码'"
              :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
            />
            <button type="button" class="pwd-toggle" @click="showPwd = !showPwd">
              {{ showPwd ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <div v-if="mode === 'register'" class="form-section">
          <label class="form-label">确认密码</label>
          <input
            v-model="password2"
            :type="showPwd ? 'text' : 'password'"
            class="form-input"
            placeholder="请再次输入密码"
            autocomplete="new-password"
          />
        </div>

        <div v-if="errorMsg" class="auth-error">⚠️ {{ errorMsg }}</div>

        <button type="submit" class="btn-primary auth-submit" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>{{ mode === 'login' ? '登 录' : '注 册' }}</span>
        </button>
      </form>

      <div class="auth-footer">
        <template v-if="mode === 'login'">
          还没有账号？<a href="#" @click.prevent="switchMode('register')">立即注册</a>
        </template>
        <template v-else>
          已有账号？<a href="#" @click.prevent="switchMode('login')">返回登录</a>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAuth } from '../stores/auth'

const emit = defineEmits(['success'])
const { login, register } = useAuth()

const mode = ref('login')
const username = ref('')
const password = ref('')
const password2 = ref('')
const showPwd = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const usernameRef = ref(null)

onMounted(() => nextTick(() => usernameRef.value?.focus()))

function switchMode(m) {
  mode.value = m
  errorMsg.value = ''
  password.value = ''
  password2.value = ''
}

function validate() {
  const u = username.value.trim()
  if (!u) return '请输入用户名'
  if (mode.value === 'register') {
    if (u.length < 3 || u.length > 32) return '用户名长度需 3~32 位'
  }
  if (!password.value) return '请输入密码'
  if (mode.value === 'register') {
    if (password.value.length < 6) return '密码至少 6 位'
    if (password.value !== password2.value) return '两次输入的密码不一致'
  }
  return ''
}

async function submit() {
  errorMsg.value = ''
  const err = validate()
  if (err) { errorMsg.value = err; return }

  loading.value = true
  try {
    if (mode.value === 'login') {
      await login(username.value.trim(), password.value)
    } else {
      await register(username.value.trim(), password.value)
    }
    emit('success')
  } catch (e) {
    const d = e.response?.data?.detail
    errorMsg.value =
      typeof d === 'string' ? d
      : d?.[0]?.msg || e.message || '请求失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
  padding: 24px;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  padding: 36px 32px;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
}

.auth-tabs {
  display: flex;
  background: #f1f5f9;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 24px;
}
.auth-tab {
  flex: 1;
  padding: 10px 0;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}
.auth-tab.active {
  background: #fff;
  color: #4f46e5;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.auth-heading {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 20px;
}

.form-section { margin-bottom: 16px; }
.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  color: #111827;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}
.form-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}

.password-wrap { position: relative; }
.password-wrap .form-input { padding-right: 42px; }
.pwd-toggle {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  font-size: 16px;
  padding: 6px;
  cursor: pointer;
  border-radius: 6px;
}
.pwd-toggle:hover { background: #f3f4f6; }

.auth-error {
  padding: 10px 14px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 14px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px 0;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
}
.btn-primary:hover:not(:disabled) {
  background: #4338ca;
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.35);
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.auth-submit { margin-top: 6px; }

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.auth-footer {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}
.auth-footer a {
  color: #4f46e5;
  font-weight: 600;
  text-decoration: none;
}
.auth-footer a:hover { text-decoration: underline; }
</style>