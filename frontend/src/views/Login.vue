<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>PXE Manager</h2>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" size="large" style="width:100%" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import {ref, reactive} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage} from 'element-plus'
import {useAuthStore} from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({username: '', password: ''})

const handleLogin = async () => {
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
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background-color: #f0f2f5;
}
.login-card {
  width: 400px;
  text-align: center;
}
.login-card h2 {
  margin-bottom: 24px;
  color: #304156;
}
</style>
