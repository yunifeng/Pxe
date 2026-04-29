<template>
  <div>
    <h2>PXE 服务管理</h2>
    <el-card>
      <template #header>服务状态</template>
      <el-button type="primary" @click="fetchServices">刷新</el-button>
      <div style="margin-top:12px">
        <el-tag :type="services.dnsmasq ? 'success' : 'danger'" size="large">dnsmasq {{ services.dnsmasq ? '运行中' : '已停止' }}</el-tag>
        <el-tag :type="services.tftp ? 'success' : 'danger'" size="large" style="margin-left:8px">TFTP {{ services.tftp ? '运行中' : '已停止' }}</el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import {ref} from 'vue'
import {pxeApi} from '@/api'

const services = ref({})
const fetchServices = async () => {
  try {
    const res = await pxeApi.services()
    services.value = res.data.data
  } catch {
    // ignore
  }
}
</script>
