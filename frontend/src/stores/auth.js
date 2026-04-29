import {defineStore} from 'pinia'
import {authApi} from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token') || '',
    role: localStorage.getItem('role') || '',
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.role === 'admin',
    isOperator: (state) => state.role === 'operator',
  },

  actions: {
    async login(username, password) {
      const res = await authApi.login(username, password)
      this.token = res.data.data.token
      this.user = res.data.data.user
      this.role = res.data.data.user.role
      localStorage.setItem('token', this.token)
      localStorage.setItem('role', this.role)
    },

    logout() {
      this.user = null
      this.token = ''
      this.role = ''
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      authApi.clearToken()
    },
  },
})
