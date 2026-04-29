<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">PXE Manager</div>
      <el-menu
        :default-active="currentRoute"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/node">
          <el-icon><Connection /></el-icon>
          <span>节点管理</span>
        </el-menu-item>
        <el-menu-item index="/host">
          <el-icon><Cpu /></el-icon>
          <span>主机管理</span>
        </el-menu-item>
        <el-menu-item index="/bmc">
          <el-icon><Switch /></el-icon>
          <span>BMC 管理</span>
        </el-menu-item>
        <el-menu-item index="/pxe">
          <el-icon><Cloudy /></el-icon>
          <span>PXE 服务</span>
        </el-menu-item>
        <el-menu-item index="/file">
          <el-icon><Folder /></el-icon>
          <span>文件管理</span>
        </el-menu-item>
        <el-menu-item
          v-if="auth.isAdmin || auth.isOperator"
          index="/template"
        >
          <el-icon><Document /></el-icon>
          <span>配置模板</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-right">
          <span>欢迎，{{ auth.user?.username || '用户' }}</span>
          <el-button type="danger" text @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import {useAuthStore} from '@/stores/auth'
import {useRoute, useRouter} from 'vue-router'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const currentRoute = route.path

const handleLogout = () => {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background-color: #304156;
  overflow-y: auto;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
}
.header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
