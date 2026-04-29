<template>
  <div>
    <template v-if="auth.isLoggedIn">
      <layout>
        <router-view />
      </layout>
    </template>
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<script setup>
import {useAuthStore} from '@/stores/auth'
import Layout from '@/components/Layout.vue'

const auth = useAuthStore()
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}
</style>
