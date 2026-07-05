<template>
  <div class="jobs-page">
    <div class="jp-header">
      <router-link to="/" class="jp-back">← 返回首页</router-link>
      <h1>任务列表</h1>
      <p>查看所有已提交的计算任务</p>
    </div>

    <div v-if="jobs.length === 0" class="jp-empty">
      <p>暂无任务记录</p>
      <router-link to="/" class="jp-go">去首页开始实验 →</router-link>
    </div>

    <div v-else class="jp-table-wrap">
      <table class="jp-table">
        <thead>
          <tr>
            <th>任务 ID</th>
            <th>案例</th>
            <th>提交时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in jobs" :key="j.jobId">
            <td class="mono">{{ j.jobId?.slice(0, 8) }}...</td>
            <td>{{ caseNames[j.caseId] || j.caseId }}</td>
            <td>{{ j.time }}</td>
            <td>
              <span class="jp-status" :class="j.status">{{ statusLabel[j.status] || '未知' }}</span>
            </td>
            <td>
              <router-link v-if="j.status === 'done'" :to="`/result/${j.jobId}`" class="jp-view">
                查看结果 →
              </router-link>
              <span v-else class="jp-wait">后台运行中</span>
            </td>
          </tr>
        </tbody>
      </table>
      <button class="jp-clear" @click="clearJobs">清空记录</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const jobs = ref([])
const caseNames = {
  troposphere: '对流层 ZTD', ionosphere: '电离层 VTEC',
  gnss: 'GNSS 基线网', elevation: '高程异常',
}
const statusLabel = { pending: '等待中', running: '运行中', done: '已完成', failed: '失败' }

onMounted(() => {
  loadJobs()
  window.addEventListener('geomind:job-created', loadJobs)
})

function loadJobs() {
  const raw = JSON.parse(localStorage.getItem('geomind_jobs') || '[]')
  jobs.value = raw.map(j => ({ ...j, status: 'running' }))
  // Try to get actual status from backend
  raw.forEach((j, i) => {
    api.get(`/jobs/${j.jobId}`).then(res => {
      jobs.value[i] = { ...jobs.value[i], status: res.data?.status || 'running' }
    }).catch(() => {})
  })
}

function clearJobs() {
  if (confirm('清空全部任务记录？')) {
    localStorage.removeItem('geomind_jobs')
    jobs.value = []
  }
}
</script>

<style scoped>
.jobs-page { max-width: 800px; margin: 0 auto; padding: 40px 24px; min-height: 100vh; background: #fff; }
.jp-header { margin-bottom: 32px; }
.jp-back { color: #3b82f6; text-decoration: none; font-size: 14px; }
.jp-header h1 { font-size: 28px; font-weight: 800; color: #1a365d; margin: 8px 0 4px; }
.jp-header p { color: #718096; font-size: 14px; }
.jp-empty { text-align: center; padding: 80px 20px; color: #a0aec0; }
.jp-go { color: #3b82f6; font-weight: 600; }
.jp-table-wrap { overflow-x: auto; }
.jp-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.jp-table th { background: #1e3a8a; color: #fff; padding: 10px 12px; text-align: left; }
.jp-table td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.jp-status { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.jp-status.已完成 { background: #dcfce7; color: #16a34a; }
.jp-status.运行中, .jp-status.等待中 { background: #dbeafe; color: #2563eb; }
.jp-status.失败 { background: #fee2e2; color: #dc2626; }
.jp-view { color: #3b82f6; font-weight: 600; text-decoration: none; }
.jp-wait { color: #a0aec0; font-size: 12px; }
.jp-clear { margin-top: 16px; padding: 6px 16px; border: 1px solid #feb2b2; border-radius: 6px; background: #fff5f5; color: #c53030; font-size: 12px; cursor: pointer; }
</style>
