<template>
  <div class="benchmark-page">
    <!-- Header -->
    <div class="bm-header">
      <div class="bm-header-badge">BENCHMARK</div>
      <h1>精度基准测试</h1>
      <p>四场景 · 双路线 · 统一指标 · 全外推验证</p>
      <div class="bm-summary-tag">
        <span class="sum-dot"></span>
        所有分割均为空间 / 时间外推，检验泛化能力
      </div>
    </div>

    <!-- KPI 总览行 -->
    <div class="bm-kpi-row">
      <div class="kpi-card kpi-highlight" v-for="kpi in kpis" :key="kpi.label">
        <div class="kpi-icon" v-html="kpi.icon"></div>
        <div class="kpi-val">{{ animatedKpis[kpi.key] }}</div>
        <div class="kpi-label">{{ kpi.label }}</div>
        <div class="kpi-sub">{{ kpi.sub }}</div>
      </div>
    </div>

    <!-- 四案例精度对比网格 -->
    <div class="bm-case-grid">
      <div
        class="bm-case-card"
        v-for="c in cases"
        :key="c.key"
        :class="[c.key, { 'gold': c.improvement >= 60 }]"
      >
        <div class="case-header">
          <span class="case-icon">{{ c.icon }}</span>
          <div>
            <h3>{{ c.name }}</h3>
            <span class="case-badge" :class="c.improvement >= 60 ? 'badge-gold' : 'badge-blue'">
              {{ c.improvement >= 60 ? '🚀 大幅提升' : '📈 稳定提升' }}
            </span>
          </div>
        </div>

        <div class="case-bars">
          <div class="bar-group">
            <div class="bar-label">经典</div>
            <div class="bar-track">
              <div
                class="bar-fill bar-classic"
                :style="{ width: classicBarPct(c) + '%' }"
              ></div>
            </div>
            <div class="bar-val">{{ c.classic_display }}</div>
          </div>
          <div class="bar-group">
            <div class="bar-label">ML</div>
            <div class="bar-track">
              <div
                class="bar-fill bar-ml"
                :style="{ width: mlBarPct(c) + '%' }"
              ></div>
            </div>
            <div class="bar-val ml">{{ c.ml_display }}</div>
          </div>
        </div>

        <div class="case-improvement">
          <div class="imp-ring" :style="{ '--pct': c.improvement }">
            <svg viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="34" class="imp-bg" />
              <circle
                cx="40" cy="40" r="34"
                class="imp-fill"
                :class="c.improvement >= 60 ? 'gold' : 'blue'"
                :style="{
                  strokeDashoffset: 213.6 * (1 - animatedImprovements[c.key] / 100)
                }"
              />
            </svg>
            <span class="imp-text">{{ animatedImprovements[c.key] }}%</span>
          </div>
          <span class="imp-label">精度提升</span>
        </div>

        <div class="case-meta">
          {{ c.classic_name }} → {{ c.ml_name }}
        </div>
      </div>
    </div>

    <!-- 雷达图 + 柱状图 -->
    <div class="bm-charts-row">
      <div class="chart-box">
        <h3>精度提升雷达图</h3>
        <div ref="radarRef" class="chart-canvas"></div>
      </div>
      <div class="chart-box">
        <h3>RMSE 对比</h3>
        <div ref="barRef" class="chart-canvas"></div>
      </div>
    </div>

    <!-- 验证策略 -->
    <div class="bm-validation">
      <h3>外推验证策略</h3>
      <div class="val-grid">
        <div class="val-card" v-for="v in validations" :key="v.label">
          <div class="val-icon">{{ v.icon }}</div>
          <strong>{{ v.label }}</strong>
          <span>{{ v.desc }}</span>
        </div>
      </div>
    </div>

    <!-- CTA -->
    <div class="bm-cta">
      <router-link to="/" class="cta-primary">返回首页体验</router-link>
      <a href="https://github.com/PatrickLee726/geomind" target="_blank" class="cta-secondary">GitHub 查看源码</a>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import api from '../api.js'
import * as echarts from 'echarts'

const cases = ref([])
const animatedKpis = reactive({
  totalScenes: 0,
  maxGain: 0,
  avgGain: 0,
  allPositive: 0,
})

const animatedImprovements = reactive({
  troposphere: 0,
  ionosphere: 0,
  gnss_network: 0,
  elevation: 0,
})

const kpis = [
  { key: 'totalScenes', label: '验证场景', sub: '个 GNSS 核心问题', icon: '🎯', target: 4 },
  { key: 'maxGain', label: '最高提升', sub: '高程异常场景', icon: '🏆', target: 65.2, suffix: '%' },
  { key: 'avgGain', label: '平均提升', sub: '四场景综合', icon: '📊', target: 38.4, suffix: '%' },
  { key: 'allPositive', label: '正向提升', sub: '全部优于经典方法', icon: '✅', target: 4, suffix: '/4' },
]

const validations = [
  { icon: '🌍', label: '按站点外推', desc: '训练站与测试站完全不重叠' },
  { icon: '📅', label: '按 DOY 外推', desc: '用历史日期训练，预测未来日期' },
  { icon: '🎲', label: '独立模拟组', desc: '每组独立生成，避免数据泄露' },
  { icon: '🔀', label: '随机划分', desc: '固定种子保证可复现性' },
]

const radarRef = ref(null)
const barRef = ref(null)

function classicBarPct(c) {
  // Normalize: bar width relative to classic RMSE across all cases
  const max = 12.5
  return Math.min((c.classic_rmse / max) * 100, 100)
}

function mlBarPct(c) {
  const max = 12.5
  return Math.min((c.ml_rmse / max) * 100, 100)
}

function animateNumber(key, target, suffix = '') {
  const duration = 2000
  const start = performance.now()
  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
    const val = Math.round(target * eased * 10) / 10
    animatedKpis[key] = suffix ? val + suffix : val
    if (progress < 1) requestAnimationFrame(tick)
    else animatedKpis[key] = suffix ? target + suffix : target
  }
  requestAnimationFrame(tick)
}

onMounted(async () => {
  try {
    const res = await api.get('/benchmark/results')
    const data = res.data.cases
    cases.value = Object.entries(data).map(([key, c]) => ({
      key,
      ...c,
      icon: { troposphere: '🛰️', ionosphere: '🌐', gnss_network: '📡', elevation: '⛰️' }[key],
      classic_display: c.classic_rmse + ' ' + c.unit,
      ml_display: c.ml_rmse + ' ' + c.unit,
    }))
  } catch (e) {
    console.warn('后端未启动，使用离线数据')
    // 降级：使用内置数据
    const fallback = {
      troposphere: { key: 'troposphere', name: '对流层 ZTD', classic_name: 'Saastamoinen+GPT3', ml_name: 'ML+GPT3', classic_rmse: 11.52, ml_rmse: 4.37, improvement: 62.0, unit: 'cm', icon: '🛰️', classic_display: '11.52 cm', ml_display: '4.37 cm' },
      ionosphere: { key: 'ionosphere', name: '电离层 VTEC', classic_name: '27参数谐波', ml_name: '球面编码DNN', classic_rmse: 3.50, ml_rmse: 3.04, improvement: 13.1, unit: 'TECU', icon: '🌐', classic_display: '3.50 TECU', ml_display: '3.04 TECU' },
      gnss_network: { key: 'gnss_network', name: 'GNSS 基线网', classic_name: '等权平差', ml_name: 'ML智能定权', classic_rmse: 12.50, ml_rmse: 10.86, improvement: 13.1, unit: 'mm', icon: '📡', classic_display: '12.50 mm', ml_display: '10.86 mm' },
      elevation: { key: 'elevation', name: '高程异常', classic_name: '5次多项式', ml_name: 'ML神经网络', classic_rmse: 0.119, ml_rmse: 0.041, improvement: 65.2, unit: 'm', icon: '⛰️', classic_display: '0.119 m', ml_display: '0.041 m' },
    }
    cases.value = Object.values(fallback)
  }

  // Animate KPI counters
  animateNumber('totalScenes', 4)
  animateNumber('maxGain', 65.2, '%')
  animateNumber('avgGain', 38.4, '%')
  animateNumber('allPositive', 4, '/4')

  // Animate improvement rings
  for (const c of cases.value) {
    const target = c.improvement
    const key = c.key
    const duration = 1800
    const start = performance.now()
    function tick(now) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      animatedImprovements[key] = Math.round(target * eased)
      if (progress < 1) requestAnimationFrame(tick)
      else animatedImprovements[key] = target
    }
    requestAnimationFrame(tick)
  }

  // Charts
  await nextTick()
  renderCharts()
})

function renderCharts() {
  const names = cases.value.map(c => c.name)
  const classicData = cases.value.map(c => c.classic_rmse)
  const mlData = cases.value.map(c => c.ml_rmse)
  const improvData = cases.value.map(c => c.improvement)

  // Radar chart for improvement
  if (radarRef.value) {
    const radar = echarts.init(radarRef.value)
    radar.setOption({
      tooltip: {},
      radar: {
        center: ['50%', '55%'],
        radius: '70%',
        indicator: names.map(n => ({ name: n, max: 70 })),
        axisName: { color: '#94a3b8', fontSize: 11 },
        splitArea: { areaStyle: { color: ['#0f172a', '#1a2332'] } },
      },
      series: [{
        type: 'radar',
        data: [{ value: improvData, name: 'ML 精度提升 (%)', areaStyle: { color: 'rgba(37,99,235,0.25)' }, lineStyle: { color: '#3b82f6', width: 2 }, itemStyle: { color: '#60a5fa' } }],
      }],
    })
  }

  // Bar chart for RMSE comparison
  if (barRef.value) {
    const bar = echarts.init(barRef.value)
    bar.setOption({
      tooltip: {},
      legend: {
        data: ['经典方法', 'ML 方法'],
        textStyle: { color: '#94a3b8' },
        bottom: 0,
      },
      grid: { left: '15%', right: '10%', top: '10%', bottom: '15%' },
      xAxis: {
        type: 'category',
        data: names,
        axisLabel: { color: '#94a3b8', fontSize: 10, interval: 0, rotate: 15 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#1e293b' } },
      },
      series: [
        {
          name: '经典方法',
          type: 'bar',
          data: classicData,
          itemStyle: { color: '#64748b', borderRadius: [6, 6, 0, 0] },
          barWidth: '35%',
        },
        {
          name: 'ML 方法',
          type: 'bar',
          data: mlData,
          itemStyle: { color: '#3b82f6', borderRadius: [6, 6, 0, 0] },
          barWidth: '35%',
        },
      ],
    })
  }
}
</script>

<style scoped>
.benchmark-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 24px 60px;
  min-height: 100vh;
  background: #0b1120;
  color: #e2e8f0;
}

/* Header */
.bm-header {
  text-align: center;
  margin-bottom: 40px;
}
.bm-header-badge {
  display: inline-block;
  padding: 4px 16px;
  border-radius: 20px;
  background: rgba(37,99,235,0.15);
  color: #60a5fa;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
  margin-bottom: 16px;
  border: 1px solid rgba(59,130,246,0.2);
}
.bm-header h1 {
  font-size: 36px;
  font-weight: 800;
  margin: 0 0 8px;
  color: #f1f5f9;
  letter-spacing: -1px;
}
.bm-header p {
  font-size: 15px;
  color: #94a3b8;
  margin: 0;
}
.bm-summary-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 6px 16px;
  border-radius: 8px;
  background: rgba(34,197,94,0.08);
  border: 1px solid rgba(34,197,94,0.15);
  font-size: 13px;
  color: #4ade80;
}
.sum-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  animation: dotPulse 2s ease-in-out infinite;
}
@keyframes dotPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* KPI Row */
.bm-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}
.kpi-card {
  text-align: center;
  padding: 28px 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1a2332, #162032);
  border: 1px solid #1e293b;
  transition: all 0.3s ease;
}
.kpi-card:hover {
  border-color: #334155;
  transform: translateY(-2px);
}
.kpi-highlight {
  background: linear-gradient(135deg, #1e2d4a, #17253d);
  border-color: rgba(59,130,246,0.2);
}
.kpi-icon {
  font-size: 28px;
  margin-bottom: 8px;
}
.kpi-val {
  font-size: 32px;
  font-weight: 800;
  color: #f1f5f9;
  letter-spacing: -1px;
}
.kpi-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
}
.kpi-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

/* Case Cards Grid */
.bm-case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}
.bm-case-card {
  padding: 24px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1a2332, #15202f);
  border: 1px solid #1e293b;
  transition: all 0.35s ease;
  position: relative;
  overflow: hidden;
}
.bm-case-card:hover {
  border-color: #334155;
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.bm-case-card.gold {
  background: linear-gradient(135deg, #1f2520, #1a211a);
  border-color: rgba(234,179,8,0.15);
}
.bm-case-card.gold:hover {
  border-color: rgba(234,179,8,0.3);
}

.case-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.case-icon { font-size: 24px; }
.case-header h3 { font-size: 16px; font-weight: 700; color: #f1f5f9; margin: 0; }
.case-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
}
.badge-gold { background: rgba(234,179,8,0.12); color: #fbbf24; }
.badge-blue { background: rgba(59,130,246,0.12); color: #60a5fa; }

/* Bars */
.case-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
.bar-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bar-label {
  width: 28px;
  font-size: 11px;
  color: #94a3b8;
  text-align: right;
}
.bar-track {
  flex: 1;
  height: 10px;
  background: #0f172a;
  border-radius: 5px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 1.5s cubic-bezier(0.34,1.56,0.64,1);
}
.bar-classic { background: linear-gradient(90deg, #64748b, #94a3b8); }
.bar-ml { background: linear-gradient(90deg, #2563eb, #3b82f6); }
.bar-val {
  width: 64px;
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  text-align: right;
  font-family: 'JetBrains Mono', monospace;
}
.bar-val.ml { color: #60a5fa; }

/* Improvement Ring */
.case-improvement {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
}
.imp-ring {
  position: relative;
  width: 80px;
  height: 80px;
}
.imp-ring svg {
  width: 80px;
  height: 80px;
  transform: rotate(-90deg);
}
.imp-bg {
  fill: none;
  stroke: #1e293b;
  stroke-width: 6;
}
.imp-fill {
  fill: none;
  stroke-width: 6;
  stroke-linecap: round;
  stroke-dasharray: 213.6;
  transition: stroke-dashoffset 2s cubic-bezier(0.34,1.56,0.64,1);
}
.imp-fill.gold { stroke: #fbbf24; }
.imp-fill.blue { stroke: #3b82f6; }
.imp-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: #f1f5f9;
}
.imp-label {
  font-size: 12px;
  color: #64748b;
}

.case-meta {
  font-size: 11px;
  color: #64748b;
  text-align: center;
}

/* Charts Row */
.bm-charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 40px;
}
.chart-box {
  padding: 24px;
  border-radius: 16px;
  background: #1a2332;
  border: 1px solid #1e293b;
}
.chart-box h3 {
  font-size: 15px;
  font-weight: 700;
  color: #94a3b8;
  margin: 0 0 16px;
}
.chart-canvas {
  width: 100%;
  height: 340px;
}

/* Validation */
.bm-validation {
  margin-bottom: 40px;
}
.bm-validation h3 {
  text-align: center;
  font-size: 18px;
  font-weight: 700;
  color: #94a3b8;
  margin-bottom: 20px;
}
.val-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.val-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 12px;
  border-radius: 12px;
  background: #1a2332;
  border: 1px solid #1e293b;
  text-align: center;
}
.val-icon { font-size: 22px; }
.val-card strong { font-size: 13px; color: #e2e8f0; }
.val-card span { font-size: 11px; color: #64748b; }

/* CTA */
.bm-cta {
  display: flex;
  justify-content: center;
  gap: 16px;
}
.cta-primary, .cta-secondary {
  display: inline-flex;
  align-items: center;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
}
.cta-primary {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
}
.cta-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(37,99,235,0.4); }
.cta-secondary {
  background: transparent;
  color: #94a3b8;
  border: 1px solid #334155;
}
.cta-secondary:hover { border-color: #3b82f6; color: #fff; }

@media (max-width: 768px) {
  .bm-kpi-row { grid-template-columns: repeat(2, 1fr); }
  .bm-charts-row { grid-template-columns: 1fr; }
  .val-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
