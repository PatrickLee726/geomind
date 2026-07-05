<template>
  <div class="result-page">
    <div class="back-link">
      <router-link to="/">← 返回首页</router-link>
    </div>

    <div v-if="loading" class="loading">加载结果...</div>

    <template v-if="!loading && result">
      <h1>计算结果</h1>
      <p class="case-name">{{ result.case_id }}</p>

      <!-- 摘要 -->
      <section class="section">
        <h2>摘要</h2>
        <pre class="summary">{{ result.summary }}</pre>
      </section>

      <!-- 指标卡片 -->
      <section class="section" v-if="result.final_metrics">
        <h2>精度指标</h2>
        <div class="metrics-grid">
          <div v-for="(metrics, methodName) in nestedMetrics" :key="methodName" class="metrics-block">
            <h3>{{ methodName === 'classical' ? '经典方法' : methodName === 'ml' ? '机器学习' : methodName === 'harmonic' ? '谐波模型' : methodName }}</h3>
            <div v-for="(v, k) in metrics" :key="k" class="metric-row">
              <span class="metric-label">{{ k.replace(/_/g, ' ') }}</span>
              <span class="metric-value">{{ v }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 图表 -->
      <section class="section" v-if="chartNames.length">
        <h2>可视化图表</h2>
        <div v-for="name in chartNames" :key="name" class="chart-container">
          <h3>{{ name }}</h3>
          <img :src="getChartUrl(name)" :alt="name" class="chart-img" />
        </div>
      </section>

      <!-- 执行步骤 -->
      <section class="section" v-if="result.steps">
        <h2>执行步骤</h2>
        <div v-for="step in result.steps" :key="step.name" class="step-row">
          <span class="step-dot" :class="step.status"></span>
          <span class="step-name">{{ step.name }}</span>
          <span class="step-metrics" v-if="step.metrics">
            <template v-for="(v, k) in step.metrics" :key="k">
              {{ k }}={{ v }}
            </template>
          </span>
        </div>
      </section>
    </template>

    <div v-if="!loading && error" class="error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api.js'

const route = useRoute()
const jobId = route.params.jobId

const loading = ref(true)
const error = ref(null)
const result = ref(null)

const chartNames = computed(() => {
  if (!result.value?.charts) return []
  return Object.keys(result.value.charts)
})

const nestedMetrics = computed(() => {
  if (!result.value?.final_metrics) return {}
  const out = {}
  for (const [k, v] of Object.entries(result.value.final_metrics)) {
    if (v && typeof v === 'object' && !Array.isArray(v) && Object.values(v).some(x => typeof x !== 'object')) {
      out[k] = v
    }
  }
  return out
})

onMounted(async () => {
  try {
    const res = await api.getResult(jobId)
    result.value = res.data
  } catch (e) {
    error.value = '加载结果失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
})

function getChartUrl(name) {
  return api.getChart(jobId, name)
}
</script>

<style scoped>
.result-page { max-width: 800px; margin: 0 auto; }
.back-link { margin-bottom: 16px; font-size: 14px; color: #3182ce; transition: transform 0.3s ease; display: inline-block; }
.back-link:hover { transform: translateX(-4px); }
h1 { font-size: 28px; color: #1a365d; margin-bottom: 4px; animation: slideDown 0.4s ease-out; }
.case-name { color: #6b7c8e; font-size: 13px; margin-bottom: 24px; animation: fadeIn 0.5s 0.1s ease-out both; }

.section { 
  background: white; border-radius: 16px; padding: 28px; margin-bottom: 20px; 
  box-shadow: 0 1px 6px rgba(0,0,0,0.03); border: 1px solid #e8ecf1;
  animation: fadeInUp 0.5s ease-out both;
  transition: box-shadow 0.3s ease;
}
.section:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
.section:nth-child(2) { animation-delay: 0.08s; }
.section:nth-child(3) { animation-delay: 0.16s; }
.section:nth-child(4) { animation-delay: 0.24s; }
.section:nth-child(5) { animation-delay: 0.32s; }
.section h2 { font-size: 18px; color: #1a365d; margin-bottom: 16px; font-weight: 700; }

.summary { 
  font-size: 14px; line-height: 1.8; color: #444; white-space: pre-wrap; 
  background: #f7fafc; padding: 18px; border-radius: 10px;
  border-left: 3px solid #3182ce;
}

.metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.metrics-block { 
  background: #f7fafc; border-radius: 12px; padding: 18px;
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}
.metrics-block:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.06); transform: translateY(-2px); }
.metrics-block h3 { font-size: 14px; color: #4a5568; margin-bottom: 12px; }
.metric-row { 
  display: flex; justify-content: space-between; padding: 7px 0; font-size: 14px; 
  border-bottom: 1px solid #e2e8f0; 
  animation: countUp 0.4s ease-out both;
}
.metric-value { font-weight: 700; color: #2d3748; }

.chart-container { margin-bottom: 24px; animation: fadeInUp 0.5s ease-out both; }
.chart-container h3 { font-size: 15px; color: #4a5568; margin-bottom: 12px; }
.chart-img { 
  width: 100%; border-radius: 10px; border: 1px solid #e8ecf1;
  transition: box-shadow 0.4s ease, transform 0.4s ease;
  cursor: pointer;
}
.chart-img:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.12); transform: scale(1.02); }

.step-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; font-size: 14px; border-bottom: 1px solid #f0f0f0; transition: background 0.2s; }
.step-row:hover { background: #fafcfe; }
.step-dot { width: 10px; height: 10px; border-radius: 50%; background: #ccc; flex-shrink: 0; transition: background 0.3s ease; }
.step-dot.done { background: #48bb78; box-shadow: 0 0 0 3px rgba(72, 187, 120, 0.2); }
.step-dot.running { background: #4299e1; animation: statusBlink 1s ease infinite; box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2); }
.step-dot.failed { background: #f56565; box-shadow: 0 0 0 3px rgba(245, 101, 101, 0.2); }
.step-name { font-weight: 600; min-width: 100px; }
.step-metrics { color: #718096; font-size: 12px; }

.loading { text-align: center; padding: 60px; color: #718096; animation: statusBlink 1.2s ease infinite; }
.error { padding: 20px; background: #fff5f5; color: #c53030; border-radius: 12px; animation: fadeInUp 0.4s ease-out; }
</style>
