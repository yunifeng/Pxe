import {createRouter, createWebHistory} from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {public: true},
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
  },
  {
    path: '/pxe',
    name: 'PXE',
    component: () => import('@/views/PXE/Index.vue'),
  },
  {
    path: '/bmc',
    name: 'BMC',
    component: () => import('@/views/BMC/Index.vue'),
  },
  {
    path: '/node',
    name: 'Node',
    component: () => import('@/views/Node/Index.vue'),
  },
  {
    path: '/host',
    name: 'Host',
    component: () => import('@/views/Host/Index.vue'),
  },
  {
    path: '/file',
    name: 'File',
    component: () => import('@/views/FileMgr/Index.vue'),
  },
  {
    path: '/template',
    name: 'Template',
    component: () => import('@/views/Template/Index.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Route guard: redirect to login if not authenticated
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    return '/login'
  }
})

export default router
