#!/usr/bin/env bash
# scripts/init_frontend.sh
# 初始化前端目录结构 + 默认文件（已存在的不覆盖）
set -e
cd "$(dirname "$0")/.."

FE="frontend"

if [ ! -d "$FE" ]; then
    echo "❌ 未找到 $FE/ 目录"
    echo "   请先执行:"
    echo "     npm create vite@latest frontend -- --template vue"
    echo "     cd frontend && npm install && npm install axios"
    exit 1
fi

if [ ! -f "$FE/package.json" ]; then
    echo "❌ $FE/package.json 不存在，请先执行 npm create vite"
    exit 1
fi

echo "========================================="
echo " 前端目录初始化"
echo "========================================="

# ==================== 1. 建目录 ====================
echo ""
echo "📁 创建目录结构..."
mkdir -p "$FE/src/components/workspace/common"
mkdir -p "$FE/src/views"
mkdir -p "$FE/src/stores"
mkdir -p "$FE/src/assets"
mkdir -p "$FE/public"
echo "   ✅ src/components/workspace/common/"
echo "   ✅ src/views/  src/stores/  src/assets/"
echo "   ✅ public/"

# ==================== 2. 已存在则不覆盖 ====================
create_if_absent() {
    local path="$1"
    local content="$2"
    if [ -f "$path" ]; then
        echo "   ⏭  $path （已存在，跳过）"
    else
        printf '%s' "$content" > "$path"
        echo "   ✨ $path"
    fi
}

echo ""
echo "📝 生成默认文件（已存在的不覆盖）..."

# ---- src/api.js ----
create_if_absent "$FE/src/api.js" 'import axios from "axios"

const api = axios.create({
  baseURL: "/api",
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token")
      localStorage.removeItem("user")
      window.dispatchEvent(new Event("auth:logout"))
    }
    return Promise.reject(err)
  }
)

export default api
'

# ---- src/stores/auth.js ----
create_if_absent "$FE/src/stores/auth.js" 'import { ref, computed } from "vue"
import api from "../api"

const token = ref(localStorage.getItem("token") || "")
const user  = ref(safeParse(localStorage.getItem("user")))
const booting = ref(true)

function safeParse(s) {
  if (!s) return null
  try { return JSON.parse(s) } catch { return null }
}

function setAuth(t, u) {
  token.value = t
  user.value = u
  localStorage.setItem("token", t)
  localStorage.setItem("user", JSON.stringify(u))
}

function clearAuth() {
  token.value = ""
  user.value = null
  localStorage.removeItem("token")
  localStorage.removeItem("user")
}

window.addEventListener("auth:logout", clearAuth)

export function useAuth() {
  const isLoggedIn = computed(() => !!token.value && !!user.value)

  async function register(username, password) {
    const res = await api.post("/auth/register", { username, password })
    setAuth(res.data.token, res.data.user)
    return res.data.user
  }

  async function login(username, password) {
    const res = await api.post("/auth/login", { username, password })
    setAuth(res.data.token, res.data.user)
    return res.data.user
  }

  function logout() { clearAuth() }

  async function bootstrap() {
    booting.value = true
    try {
      if (token.value) {
        const res = await api.get("/auth/me")
        user.value = res.data
        localStorage.setItem("user", JSON.stringify(res.data))
      }
    } catch {
      // 401 由拦截器处理
    } finally {
      booting.value = false
    }
  }

  return { token, user, booting, isLoggedIn, register, login, logout, bootstrap }
}
'

# ---- src/views/AuthView.vue（最小骨架）----
create_if_absent "$FE/src/views/AuthView.vue" '<template>
  <div class="auth-page">
    <h2>登录 / 注册</h2>
    <!-- TODO: 由 make frontend_init 补齐 -->
  </div>
</template>

<script setup>
</script>

<style scoped>
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
</style>
'

# ---- src/components/workspace/Workspace.vue（主容器骨架）----
create_if_absent "$FE/src/components/workspace/Workspace.vue" '<template>
  <main class="workspace">
    <div class="workspace-header">
      <span class="header-icon">{{ tool?.icon }}</span>
      <h1 class="header-title">{{ tool?.label }}</h1>
    </div>
    <div class="workspace-body">
      <!-- 子工具组件在 Workspace.vue 里根据 tool.id 渲染 -->
    </div>
  </main>
</template>

<script setup>
const props = defineProps({
  tool: { type: Object, default: null },
})
</script>

<style scoped>
.workspace {
  position: fixed;
  top: 0; right: 0; bottom: 0;
  left: var(--sidebar-width, 260px);
  overflow-y: auto;
  background: var(--bg, #fff);
}
.workspace-header {
  padding: 18px 32px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.workspace-body { padding: 28px 32px; }
</style>
'

# ---- 其它工具组件（空壳）----
for name in PdfToImage ImageToPdf PdfSplit PdfMerge PdfCompress PdfEncrypt PdfDecrypt \
            TextReplace PerforatedStamp StampOperation TextRedact; do
    create_if_absent "$FE/src/components/workspace/$name.vue" "<template>
  <div class=\"tool-$name\">
    <!-- TODO: $name 功能 -->
  </div>
</template>

<script setup>
</script>
"
done

# ---- 通用子组件（空壳）----
for name in DropZone ResultCard ActionBar; do
    create_if_absent "$FE/src/components/workspace/common/$name.vue" "<template>
  <div class=\"c-$name\">
    <!-- TODO: 通用组件 $name -->
  </div>
</template>

<script setup>
</script>
"
done

# ==================== 3. 完成 ====================
echo ""
echo "========================================="
echo " ✅ 初始化完成"
echo "========================================="
echo ""
echo "下一步:"
echo "  make run-frontend       启动前端"
echo "  make build-frontend     构建到 backend/static/"
echo ""
