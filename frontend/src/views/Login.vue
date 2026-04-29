<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="login-left">
        <div class="logo-area">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M20 7L4 7M20 7L12 15M20 7L12 1" />
              <path d="M4 7V17a1 1 0 001 1h14a1 1 0 001-1V7" />
              <path d="M9 20h6" />
              <path d="M12 15v5" />
            </svg>
          </div>
          <h1>PXE Manager</h1>
          <p class="tagline">PXE 网络启动分布式管理系统</p>
        </div>
        <div class="features">
          <div class="feature-item">
            <span class="feature-dot" />
            <span>PXE 网络批量装机</span>
          </div>
          <div class="feature-item">
            <span class="feature-dot" />
            <span>BMC 电源远程管控</span>
          </div>
          <div class="feature-item">
            <span class="feature-dot" />
            <span>节点实时监控</span>
          </div>
        </div>
      </div>
      <div class="login-right">
        <div class="login-form-wrapper">
          <div class="login-header">
            <h2>欢迎登录</h2>
            <p>请输入您的账号和密码</p>
          </div>
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            @submit.prevent="handleLogin"
            class="login-form"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                show-password
                :prefix-icon="Lock"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                size="large"
                class="login-btn"
                @click="handleLogin"
              >
                <span v-if="!loading">登 录</span>
                <span v-else>登录中...</span>
              </el-button>
            </el-form-item>
          </el-form>
          <div class="login-footer">
            <span>PXE Manager v0.1.0</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const formRef = ref(null)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.replace('/')
  } catch {
    ElMessage.error('用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  margin: 0;
  padding: 0;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.login-bg {
  display: flex;
  width: 100%;
  height: 100%;
}

/* Left panel */
.login-left {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.login-left::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 60%);
  animation: pulse 8s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.logo-area {
  position: relative;
  z-index: 1;
  margin-bottom: 60px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  background: rgba(255,255,255,0.2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
}

.logo-icon svg {
  width: 36px;
  height: 36px;
  stroke: #fff;
}

.logo-area h1 {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.tagline {
  font-size: 15px;
  opacity: 0.8;
  margin: 0;
  font-weight: 300;
}

.features {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  font-weight: 400;
  opacity: 0.9;
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.8);
  flex-shrink: 0;
}

/* Right panel */
.login-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 40px;
}

.login-form-wrapper {
  width: 100%;
  max-width: 380px;
}

.login-header {
  margin-bottom: 36px;
}

.login-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 8px 0;
}

.login-header p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

.login-form .el-input {
  --el-input-height: 50px;
}

.login-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  letter-spacing: 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.login-btn:hover {
  opacity: 0.9;
}

.login-footer {
  text-align: center;
  margin-top: 32px;
  color: #ccc;
  font-size: 12px;
}

/* Responsive */
@media (max-width: 768px) {
  .login-left {
    display: none;
  }
  .login-right {
    padding: 24px;
  }
}
</style>
