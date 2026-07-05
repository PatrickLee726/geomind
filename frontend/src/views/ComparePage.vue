<template>
  <div class="compare-page">
    <div class="cp-header">
      <router-link to="/" class="cp-back">← 返回首页</router-link>
      <h1>结果对比</h1>
      <p>比较不同参数配置下的经典 vs ML 精度差异</p>
      <button class="cp-clear" @click="clearAll" v-if="records.length">清空全部记录</button>
    </div>

    <div v-if="records.length === 0" class="cp-empty">
      <div class="empty-icon">📊</div>
      <p>暂无保存的对比记录</p>
      <p class="hint">运行案例后，在结果页点击「保存此结果」即可在此对比</p>
    </div>

    <div v-else class="cp-table-wrap">
      <table class="cp-table">
        <thead>
          <tr>
            <th>案例</th>
            <th>经典 RMSE</th>
            <th>ML RMSE</th>
            <th>提升</th>
            <th>参数摘要</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in records" :key="i" :class="{ best: r.improvement >= 50 }">
            <td><strong>{{ r.caseName }}</strong></td>
            <td>{{ r.classicRmse }} {{ r.unit }}</td>
            <td class="ml-val">{{ r.mlRmse }} {{ r.unit }}</td>
            <td>
              <span class="imp-badge" :class="{ gold: r.improvement >= 50 }">
                {{ r.improvement }}%
              </span>
            </td>
            <td class="params-cell">{{ r.paramsSummary }}</td>
            <td class="time-cell">{{ r.time }}</td>
            <td>
              <button class="cp-del" @click="removeRecord(i)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="records.length >= 2" class="cp-chart-section">
      <h3>RMSE 对比趋势</h3>
      <div ref="compareChartRef" class="cp-chart"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const STORAGE_KEY = 'geomind_compare_records'

const records = ref([])
const compareChartRef = ref(null)

function loadRecords() {
  try {
    records.value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch { records.value = [] }
}

function removeRecord(i) {
  records.value.splice(i, 1)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records.value))
  loadRecords()
}

function clearAll() {
  if (confirm('确定清空全部对比记录？')) {
    localStorage.removeItem(STORAGE_KEY)
    records.value = []
  }
}

onMounted(() => {
  loadRecords()
  if (records.value.length >= 2) {
    nextTick(renderChart)
  }
})

function renderChart() {
  const el = compareChartRef.value
  if (!el) return
  const chart = echarts.init(el)
  const names = records.value.map((r, i) => r.caseName + ' #' + (i + 1))
  const classic = records.value.map(r => r.classicRmse)
  const ml = records.value.map(r => r.mlRmse)
  chart.setOption({
    tooltip: {},
    legend: { data: ['经典方法', 'ML 方法'], top: 0 },
    grid: { left: '10%', right: '10%', top: '15%', bottom: '10%' },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 20, fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [
      { name: '经典方法', type: 'bar', data: classic, itemStyle: { color: '#64748b', borderRadius: [4,4,0,0] } },
      { name: 'ML 方法', type: 'bar', data: ml, itemStyle: { color: '#3b82f6', borderRadius: [4,4,0,0] } },
    ],
  })
}
</script>

<style scoped>
.compare-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  background: #fff;
}
.cp-header {
  margin-bottom: 32px;
}
.cp-back {
  color: #3b82f6;
  text-decoration: none;
  font-size: 14px;
}
.cp-header h1 {
  font-size: 28px;
  font-weight: 800;
  color: #1a365d;
  margin: 8px 0 4px;
}
.cp-header p {
  color: #718096;
  font-size: 14px;
}
.cp-clear {
  margin-top: 12px;
  padding: 6px 16px;
  border: 1px solid #feb2b2;
  border-radius: 6px;
  background: #fff5f5;
  color: #c53030;
  font-size: 12px;
  cursor: pointer;
}
.cp-empty {
  text-align: center;
  padding: 80px 20px;
  color: #a0aec0;
}
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.cp-empty p { font-size: 16px; }
.cp-empty .hint { font-size: 13px; margin-top: 8px; }

.cp-table-wrap { overflow-x: auto; }
.cp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.cp-table th {
  background: #1e3a8a;
  color: #fff;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
}
.cp-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
}
.cp-table tr.best td { background: #fffbeb; }
.ml-val { color: #2563eb; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.imp-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #dbeafe;
  color: #2563eb;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}
.imp-badge.gold { background: #fef3c7; color: #d97706; }
.params-cell { font-size: 11px; color: #718096; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.time-cell { font-size: 11px; color: #a0aec0; }
.cp-del {
  padding: 3px 10px;
  border: none;
  border-radius: 4px;
  background: #fee2e2;
  color: #dc2626;
  font-size: 11px;
  cursor: pointer;
}

.cp-chart-section {
  margin-top: 40px;
}
.cp-chart-section h3 {
  font-size: 18px;
  font-weight: 700;
  color: #1a365d;
  margin-bottom: 16px;
}
.cp-chart {
  width: 100%;
  height: 300px;
}
</style>
