<template>
  <div>
    <h2>主机管理</h2>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between">
          <span>主机列表</span>
          <div>
            <el-button type="primary" size="small" @click="showAdd = true">添加主机</el-button>
            <el-button size="small" @click="fetchList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="hostname" label="主机名" />
        <el-table-column prop="ip" label="IP" />
        <el-table-column prop="mac_address" label="MAC" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="row.deploy_status === 'running' ? 'success' : 'info'">{{ row.deploy_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" prop="install_progress" width="80" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" @click="handleHardware(row.id)">硬件</el-button>
            <el-button size="small" type="danger" @click="handleRemove(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAdd" title="添加主机" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="主机名"><el-input v-model="form.hostname" /></el-form-item>
        <el-form-item label="IP"><el-input v-model="form.ip" /></el-form-item>
        <el-form-item label="MAC"><el-input v-model="form.mac_address" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showHW" title="硬件信息" width="700px">
      <pre>{{ JSON.stringify(hwInfo, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import {ref, reactive, onMounted} from 'vue'
import {hostApi} from '@/api'
import {ElMessage} from 'element-plus'

const list = ref([])
const showAdd = ref(false)
const showHW = ref(false)
const hwInfo = ref({})
const form = reactive({hostname: '', ip: '', mac_address: ''})

const fetchList = async () => {
  try {
    const res = await hostApi.list()
    list.value = res.data.data
  } catch {
    // ignore
  }
}

const handleAdd = async () => {
  try {
    await hostApi.add(form)
    ElMessage.success('添加成功')
    showAdd.value = false
    fetchList()
  } catch {
    ElMessage.error('添加失败')
  }
}

const handleHardware = async (id) => {
  try {
    const res = await hostApi.hardware(id)
    hwInfo.value = res.data.data
    showHW.value = true
  } catch {
    ElMessage.error('获取硬件信息失败')
  }
}

const handleRemove = async (id) => {
  try {
    await hostApi.remove(id)
    ElMessage.success('已移除')
    fetchList()
  } catch {
    ElMessage.error('移除失败')
  }
}

onMounted(fetchList)
</script>
