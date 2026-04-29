<template>
  <div>
    <h2>配置模板</h2>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between">
          <span>模板列表</span>
          <el-button type="primary" size="small" @click="showAdd = true">创建模板</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleRemove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAdd" title="创建模板" width="600px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type">
            <el-option label="user-data" value="user-data" />
            <el-option label="kickstart" value="kickstart" />
            <el-option label="preseed" value="preseed" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {ref, reactive, onMounted} from 'vue'
import {templateApi} from '@/api'
import {ElMessage} from 'element-plus'

const list = ref([])
const showAdd = ref(false)
const form = reactive({name: '', type: 'user-data', content: ''})

const fetchList = async () => {
  try {
    const res = await templateApi.list()
    list.value = res.data.data
  } catch {
    // ignore
  }
}

const handleAdd = async () => {
  try {
    await templateApi.add(form)
    ElMessage.success('创建成功')
    showAdd.value = false
    fetchList()
  } catch {
    ElMessage.error('创建失败')
  }
}

const handleEdit = (row) => {
  // TODO: implement edit dialog
}

const handleRemove = async (id) => {
  try {
    await templateApi.remove(id)
    ElMessage.success('已删除')
    fetchList()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchList)
</script>
