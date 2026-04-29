<template>
  <div>
    <h2>文件管理</h2>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between">
          <span>文件列表</span>
          <el-upload :show-file-list="false" :before-upload="handleUpload">
            <el-button type="primary" size="small">上传文件</el-button>
          </el-upload>
        </div>
      </template>
      <el-tabs v-model="category" @tab-click="fetchList">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="脚本" name="script" />
        <el-tab-pane label="配置" name="config" />
        <el-tab-pane label="仓库" name="repo" />
      </el-tabs>
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="文件名" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="size" label="大小" width="100" />
        <el-table-column label="同步状态">
          <template #default="{ row }">
            <el-tag :type="row.sync_status === 'synced' ? 'success' : 'info'">{{ row.sync_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleRemove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import {ref, onMounted} from 'vue'
import {fileApi} from '@/api'
import {ElMessage} from 'element-plus'

const list = ref([])
const category = ref('all')

const fetchList = async () => {
  try {
    const res = await fileApi.list(category.value === 'all' ? null : category.value)
    list.value = res.data.data
  } catch {
    // ignore
  }
}

const handleUpload = async (file) => {
  try {
    await fileApi.upload(file, 'script')
    ElMessage.success('上传成功')
    fetchList()
  } catch {
    ElMessage.error('上传失败')
  }
  return false
}

const handleRemove = async (id) => {
  try {
    await fileApi.remove(id)
    ElMessage.success('已删除')
    fetchList()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchList)
</script>
