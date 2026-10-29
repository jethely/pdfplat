import { ref, computed } from 'vue'
import api from '../api'

// ============ 全局单例 ============
const token = ref(localStorage.getItem('token') || '')
const user  = ref(safeParse(localStorage.getItem('user')))
const booting = ref(true)   // ⭐ 启动校验中，用于避免闪屏

function safeParse(s) {
  if (!s) return null
  try { return JSON.parse(s) } catch { return null }
}

function setAuth(t, u) {
  token.value = t
  user.value = u
  localStorage.setItem('token', t)
  localStorage.setItem('user', JSON.stringify(u))
}

function clearAuth() {
  token.value = ''
  user.value = null
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

// axios 拦截器 401 时会派发这个事件
window.addEventListener('auth:logout', clearAuth)

// ============ 对外 hook ============
export function useAuth() {
  const isLoggedIn = computed(() => !!token.value && !!user.value)

  async function register(username, password) {
    const res = await api.post('/auth/register', { username, password })
    setAuth(res.data.token, res.data.user)
    return res.data.user
  }

  async function login(username, password) {
    const res = await api.post('/auth/login', { username, password })
    setAuth(res.data.token, res.data.user)
    return res.data.user
  }

  function logout() {
    clearAuth()
  }

  /** 冷启动时调一次：校验本地 token 是否还有效 */
  async function bootstrap() {
    booting.value = true
    try {
      if (token.value) {
        // 有 token 就拿它去问后端：还有效吗？
        const res = await api.get('/auth/me')
        user.value = res.data
        localStorage.setItem('user', JSON.stringify(res.data))
      }
    } catch {
      // 401 会被拦截器捕获并 clearAuth，这里不用额外处理
    } finally {
      booting.value = false
    }
  }

  return {
    token, user, booting,
    isLoggedIn,
    register, login, logout, bootstrap,
  }
}