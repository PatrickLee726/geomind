<template>
  <div id="app-container">
    <header class="app-header">
      <router-link to="/" class="logo">
        <span class="logo-icon">◈</span>
        <span class="logo-text">测智云 GeoMind</span>
      </router-link>
      <span class="subtitle">开源可分叉的 AI 平差计算引擎</span>
    </header>

    <!-- 全局任务悬浮面板 -->
    <div class="task-panel" v-if="totalJobs > 0" @click="showPanel = !showPanel">
      <div class="task-panel-trigger">
        <span class="task-dot running" v-if="runningCount > 0"></span>
        <span class="task-count">{{ runningCount > 0 ? runningCount + ' 运行中' : '' }}</span>
        <span class="task-divider" v-if="runningCount > 0 && doneCount > 0">|</span>
        <span class="task-count done" v-if="doneCount > 0">{{ doneCount }} 已完成</span>
      </div>
      <div class="task-dropdown" v-if="showPanel" @click.stop>
        <div class="task-dropdown-header">
          <span>任务列表</span>
          <router-link to="/jobs" class="task-view-all">查看全部 →</router-link>
        </div>
        <div class="task-list">
          <div v-for="j in recentJobs" :key="j.jobId" class="task-item">
            <span class="task-item-name">{{ caseNames[j.caseId] || j.caseId }}</span>
            <span class="task-item-status" :class="j.status">
              {{ j.status === 'done' ? '已完成' : '运行中' }}
            </span>
            <router-link v-if="j.status === 'done'" :to="`/result/${j.jobId}`" class="task-item-link">查看</router-link>
          </div>
        </div>
        <div class="task-dropdown-footer" @click.stop>
          <button @click="clearDone" v-if="doneCount > 0">清除已完成</button>
        </div>
      </div>
    </div>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const showPanel = ref(false)
const jobs = ref([])
const caseNames = {
  troposphere: '对流层 ZTD', ionosphere: '电离层 VTEC',
  gnss: 'GNSS 基线网', elevation: '高程异常',
}
let pollTimer = null

function loadJobs() {
  const raw = JSON.parse(localStorage.getItem('geomind_jobs') || '[]')
  jobs.value = raw
}

const runningCount = computed(() => jobs.value.filter(j => j.status !== 'done').length)
const doneCount = computed(() => jobs.value.filter(j => j.status === 'done').length)
const totalJobs = computed(() => jobs.value.length)
const recentJobs = computed(() => jobs.value.slice(0, 8))

function clearDone() {
  const remaining = jobs.value.filter(j => j.status !== 'done')
  localStorage.setItem('geomind_jobs', JSON.stringify(remaining))
  loadJobs()
}

// Poll for status updates
function pollStatus() {
  jobs.value.forEach((j, i) => {
    if (j.status !== 'done') {
      fetch(`/api/jobs/${j.jobId}`).then(r => r.json()).then(data => {
        if (data.status === 'done' || data.status === 'failed') {
          const all = JSON.parse(localStorage.getItem('geomind_jobs') || '[]')
          const idx = all.findIndex(x => x.jobId === j.jobId)
          if (idx >= 0) {
            all[idx].status = data.status === 'done' ? 'done' : 'failed'
            localStorage.setItem('geomind_jobs', JSON.stringify(all))
            loadJobs()
          }
        }
      }).catch(() => {})
    }
  })
}

onMounted(() => {
  loadJobs()
  window.addEventListener('geomind:job-created', loadJobs)
  window.addEventListener('click', () => { showPanel.value = false })
  pollTimer = setInterval(pollStatus, 5000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif; 
  background: linear-gradient(135deg, #f0f4f8 0%, #e8eef5 50%, #f5f7fa 100%);
  background-size: 200% 200%;
  animation: bgBreathe 8s ease infinite;
  color: #2c3e50; 
  min-height: 100vh;
}
a { text-decoration: none; color: inherit; }

.app-header {
  background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #1a365d 100%);
  background-size: 200% 200%;
  animation: btnShine 6s ease infinite;
  color: white;
  padding: 14px 40px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.12);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}
.logo { display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 700; transition: transform 0.3s ease; }
.logo:hover { transform: scale(1.03); }
.logo-icon { font-size: 24px; animation: fadeIn 0.6s ease; }
.subtitle { font-size: 13px; opacity: 0.75; margin-left: auto; letter-spacing: 0.5px; }

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
  animation: fadeInUp 0.5s ease-out;
}

/* ====== Task Panel ====== */
.task-panel {
  position: fixed;
  top: 68px;
  right: 24px;
  z-index: 200;
  cursor: pointer;
}
.task-panel-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}
.task-panel:hover .task-panel-trigger {
  border-color: #3b82f6;
  box-shadow: 0 4px 16px rgba(59,130,246,0.15);
}
.task-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: dotBlink 1.5s ease-in-out infinite;
}
.task-dot.running { background: #3b82f6; }
.task-count { color: #1e3a8a; }
.task-count.done { color: #16a34a; }
.task-divider { color: #cbd5e0; margin: 0 2px; }

.task-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  overflow: hidden;
}
.task-dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  font-weight: 700;
  font-size: 14px;
  color: #1a365d;
}
.task-view-all { font-size: 12px; color: #3b82f6; font-weight: 500; }
.task-list { max-height: 260px; overflow-y: auto; }
.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
}
.task-item-name { flex: 1; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-item-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.task-item-status.运行中 { background: #dbeafe; color: #2563eb; }
.task-item-status.已完成 { background: #dcfce7; color: #16a34a; }
.task-item-link { font-size: 11px; color: #3b82f6; }
.task-dropdown-footer { padding: 8px 16px; border-top: 1px solid #e2e8f0; text-align: right; }
.task-dropdown-footer button {
  padding: 4px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #fff;
  font-size: 11px;
  color: #64748b;
  cursor: pointer;
}
</style>
