import axios from 'axios'

const api = axios.create({
  baseURL: `http://${window.location.hostname}:8000/api/v1`,
  timeout: 30000,
})

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login(username, password) {
    return api.post('/auth/login', {username, password})
  },
  profile() {
    return api.get('/auth/profile')
  },
  logout() {
    return api.post('/auth/logout')
  },
  clearToken() {
    api.defaults.headers.common.Authorization = ''
  },
}

// Dashboard API
export const dashboardApi = {
  get() {
    return api.get('/dashboard/')
  },
}

// PXE API
export const pxeApi = {
  config() {
    return api.get('/pxe/config')
  },
  updateConfig(data) {
    return api.put('/pxe/config', data)
  },
  services() {
    return api.get('/pxe/services')
  },
  controlService(name, action) {
    return api.post(`/pxe/services/${name}/control`, {action})
  },
  images() {
    return api.get('/pxe/images')
  },
  addImage(data) {
    return api.post('/pxe/images', data)
  },
  tasks() {
    return api.get('/pxe/tasks')
  },
  getTask(id) {
    return api.get(`/pxe/tasks/${id}`)
  },
  createTask(data) {
    return api.post('/pxe/tasks', data)
  },
  retryTask(id) {
    return api.post(`/pxe/tasks/${id}/retry`)
  },
}

// BMC API
export const bmcApi = {
  list(params) {
    return api.get('/bmc/', {params})
  },
  add(data) {
    return api.post('/bmc/', data)
  },
  batchAdd(data) {
    return api.post('/bmc/batch', data)
  },
  power(id, action) {
    return api.post(`/bmc/${id}/power/${action}`)
  },
  stats() {
    return api.get('/bmc/stats')
  },
}

// Node API
export const nodeApi = {
  list(params) {
    return api.get('/node/', {params})
  },
  add(data) {
    return api.post('/node/', data)
  },
  remove(id) {
    return api.delete(`/node/${id}`)
  },
  check(id) {
    return api.post(`/node/${id}/check`)
  },
  sshInfo(id) {
    return api.get(`/node/${id}/ssh`)
  },
}

// Host API
export const hostApi = {
  list(params) {
    return api.get('/host/', {params})
  },
  add(data) {
    return api.post('/host/', data)
  },
  remove(id) {
    return api.delete(`/host/${id}`)
  },
  hardware(id) {
    return api.get(`/host/${id}/hardware`)
  },
  runAnsible(id, playbook, extraVars) {
    return api.post(`/host/${id}/ansible`, null, {
      params: {playbook, extra_vars: extraVars},
    })
  },
  sshInfo(id) {
    return api.post(`/host/${id}/ssh`)
  },
}

// File API
export const fileApi = {
  list(category) {
    return api.get('/file/', {params: category ? {category} : {}})
  },
  upload(file, category) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/file/upload', formData, {
      params: {category: category || 'script'},
      headers: {'Content-Type': 'multipart/form-data'},
    })
  },
  remove(id) {
    return api.delete(`/file/${id}`)
  },
  download(id) {
    return api.get(`/file/${id}/download`)
  },
  sync(fileIds, nodeId) {
    return api.post(`/file/sync?node_id=${nodeId}`, fileIds)
  },
}

// Template API
export const templateApi = {
  list(type) {
    return api.get('/template/', {params: type ? {type} : {}})
  },
  add(data) {
    return api.post('/template/', data)
  },
  get(id) {
    return api.get(`/template/${id}`)
  },
  update(id, data) {
    return api.put(`/template/${id}`, data)
  },
  remove(id) {
    return api.delete(`/template/${id}`)
  },
  render(id, variables) {
    return api.post(`/template/${id}/render`, {variables})
  },
}

export default api
