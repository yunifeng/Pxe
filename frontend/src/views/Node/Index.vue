<template>
  <div>
    <h2>节点管理</h2>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between">
          <span>节点列表</span>
          <el-button type="primary" size="small" @click="showAdd = true">添加节点</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="hostname" label="主机名" />
        <el-table-column prop="ip" label="IP" />
        <el-table-column prop="mode" label="模式" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后心跳" prop="last_heartbeat" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" @click="handleCheck(row.id)">检查</el-button>
            <el-button size="small" type="danger" @click="handleRemove(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAdd" title="添加节点" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="主机名"><el-input v-model="form.hostname" /></el-form-item>
        <el-form-item label="IP"><el-input v-model="form.ip" /></el-form-item>
        <el-form-item label="模式">
          <el-select v-model="form.mode">
            <el-option label="Agent" value="agent" />
            <el-option label="Master" value="master" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {ref, reactive, onMounted} from 'vue'
import {nodeApi} from '@/api'
import {ElMessage} from 'element-plus'

const list = ref([])
const showAdd = ref(false)
const form = reactive({hostname: '', ip: '', mode: 'agent'})

const fetchList = async () => {
  try {
    const res = await nodeApi.list()
    list.value = res.data.data
  } catch {
    // ignore
  }
}

const handleAdd = async () => {
  try {
    await nodeApi.add(form)
    ElMessage.success('添加成功')
    showAdd.value = false
    fetchList()
  } catch {
    ElMessage.error('添加失败')
  }
}

const handleCheck = async (id) => {
  try {
    await nodeApi.check(id)
    ElMessage.success('状态检查完成')
    fetchList()
  } catch {
    ElMessage.error('检查失败')
  }
}

const handleRemove = async (id) => {
  try {
    await nodeApi.remove(id)
    ElMessage.success('已移除')
    fetchList()
  } catch {
    ElMessage.error('移除失败')
  }
}

onMounted(fetchList)
</script>
