<template>
  <div>
    <h2>BMC 管理</h2>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between">
          <span>BMC 列表</span>
          <div>
            <el-button type="success" size="small" @click="showBatch = true">批量添加</el-button>
            <el-button type="primary" size="small" @click="fetchList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="hostname" label="主机名" />
        <el-table-column prop="bmc_ip" label="BMC IP" />
        <el-table-column prop="protocol" label="协议" />
        <el-table-column label="电源状态">
          <template #default="{ row }">
            <el-tag :type="row.power_status === 'on' ? 'success' : 'info'">{{ row.power_status || '未知' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="handlePower(row.id, 'on')">开机</el-button>
            <el-button size="small" type="danger" @click="handlePower(row.id, 'off')">关机</el-button>
            <el-button size="small" @click="handlePower(row.id, 'restart')">重启</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showBatch" title="批量添加" width="600px">
      <el-input v-model="csvText" type="textarea" :rows="4" placeholder="hostname,bmc_ip,username,password,protocol" />
      <template #footer>
        <el-button @click="showBatch = false">取消</el-button>
        <el-button type="primary" @click="handleBatchAdd">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {ref, onMounted} from 'vue'
import {bmcApi} from '@/api'
import {ElMessage} from 'element-plus'

const list = ref([])
const showBatch = ref(false)
const csvText = ref('')

const fetchList = async () => {
  try {
    const res = await bmcApi.list()
    list.value = res.data.data
  } catch {
    // ignore
  }
}

const handlePower = async (id, action) => {
  try {
    await bmcApi.power(id, action)
    ElMessage.success('操作成功')
    fetchList()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleBatchAdd = async () => {
  try {
    await bmcApi.batchAdd({csv_data: csvText.value})
    ElMessage.success('批量添加成功')
    showBatch.value = false
    csvText.value = ''
    fetchList()
  } catch {
    ElMessage.error('批量添加失败')
  }
}

onMounted(fetchList)
</script>
