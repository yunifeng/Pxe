<template>
  <div>
    <h2>仪表盘</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>节点</template>
          <div class="stat">
            <span class="num">{{ data.nodes?.total || 0 }}</span>
            <span class="label">总数</span>
            <el-divider />
            <span class="label">在线 {{ data.nodes?.online || 0 }} / 离线 {{ data.nodes?.offline || 0 }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>主机</template>
          <div class="stat">
            <span class="num">{{ data.hosts?.total || 0 }}</span>
            <span class="label">总数</span>
            <el-divider />
            <span class="label">运行中 {{ data.hosts?.running || 0 }} / 失败 {{ data.hosts?.failed || 0 }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>BMC</template>
          <div class="stat">
            <span class="num">{{ data.bmc?.total || 0 }}</span>
            <span class="label">总数</span>
            <el-divider />
            <span class="label">开机 {{ data.bmc?.on || 0 }} / 关机 {{ data.bmc?.off || 0 }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>服务</template>
          <div>
            <el-tag :type="data.services?.dnsmasq ? 'success' : 'danger'" size="large">dnsmasq</el-tag>
            <el-tag :type="data.services?.tftp ? 'success' : 'danger'" size="large" style="margin-left:8px">TFTP</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:20px">
      <template #header>最近安装任务</template>
      <el-table :data="data.recent_tasks || []" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="status" label="状态">
          <template #default="{row}">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="100" />
        <el-table-column prop="started_at" label="开始时间" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import {ref, onMounted} from 'vue'
import {dashboardApi} from '@/api'

const data = ref({})

const fetchData = async () => {
  try {
    const res = await dashboardApi.get()
    data.value = res.data.data
  } catch {
    // ignore
  }
}

onMounted(fetchData)
</script>

<style scoped>
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.stat .num {
  font-size: 36px;
  font-weight: bold;
}
.stat .label {
  color: #909399;
}
</style>
