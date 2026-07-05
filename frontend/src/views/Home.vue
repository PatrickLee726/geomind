<template>
  <div class="home">
    <!-- ====== Hero ====== -->
    <section class="hero-full">
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="title-main">测智云 GeoMind</span>
          <span class="title-sub">开源可分叉的 AI 平差计算引擎</span>
        </h1>
        <p class="hero-desc">
          将机器学习引入测绘平差的精度引擎<br>
          代码开源 · 架构可分叉 · 精度提升最高 65%
        </p>
        <a class="hero-github" href="https://github.com/PatrickLee726/geomind" target="_blank" title="Star us on GitHub">
          <svg class="github-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
          <span class="github-text">GitHub</span>
        </a>
        <button class="hero-cta" @click="scrollToCases">
          <span>进入实验</span>
          <span class="cta-arrow">↓</span>
        </button>
      </div>

      <!-- 背景装饰：卫星轨道 -->
      <div class="hero-decoration">
        <div class="orbit-ring ring-1"></div>
        <div class="orbit-ring ring-2"></div>
        <div class="orbit-ring ring-3"></div>
        <div class="satellite sat-1">🛰️</div>
        <div class="satellite sat-2">🛰️</div>
        <div class="satellite sat-3">🛰️</div>
        <div class="earth"></div>
      </div>
    </section>

    <!-- ====== 案例选择 ====== -->
    <section class="cases-section" id="cases-anchor">
      <h2 class="section-title">四大平差场景</h2>
      <p class="section-subtitle">每个场景内置经典方法与 ML 双路线，点击卡片进入</p>

      <div class="case-grid">
        <div
          v-for="(c, idx) in cases"
          :key="c.id"
          class="case-card"
          @click="goCase(c.id)"
          :style="{ animationDelay: (idx * 0.12) + 's' }"
        >
          <!-- CSS 示意图 -->
          <div class="card-diagram" :class="'diagram-' + c.id">
            <div class="diagram-inner">
              <!-- Troposphere -->
              <template v-if="c.id === 'troposphere'">
                <div class="trop-sat1">🛰️</div>
                <div class="trop-sat2">🛰️</div>
                <div class="trop-ray1"></div>
                <div class="trop-ray2"></div>
                <div class="trop-troposphere"></div>
                <div class="trop-earth2"></div>
                <div class="trop-antenna"></div>
                <div class="trop-ztd-label">ZTD</div>
                <div class="trop-cloud c1"></div>
                <div class="trop-cloud c2"></div>
              </template>

              <!-- Ionosphere -->
              <template v-if="c.id === 'ionosphere'">
                <div class="iono-sat">🛰️</div>
                <div class="iono-beam"></div>
                <div class="iono-shell-outer"></div>
                <div class="iono-shell-inner"></div>
                <div class="iono-band b1"></div>
                <div class="iono-band b2"></div>
                <div class="iono-band b3"></div>
                <div class="iono-globe2"></div>
                <div class="iono-station2"></div>
                <div class="iono-tec-label">VTEC</div>
              </template>

              <!-- Elevation -->
              <template v-if="c.id === 'elevation'">
                <div class="elev-mountain m1"></div>
                <div class="elev-mountain m2"></div>
                <div class="elev-mountain m3"></div>
                <div class="elev-point p1"></div>
                <div class="elev-point p2"></div>
                <div class="elev-point p3"></div>
                <div class="elev-base"></div>
              </template>

              <!-- GNSS -->
              <template v-if="c.id === 'gnss'">
                <div class="gnss-node n1"></div>
                <div class="gnss-node n2"></div>
                <div class="gnss-node n3"></div>
                <div class="gnss-node n4"></div>
                <div class="gnss-node n5"></div>
                <div class="gnss-edge e12"></div>
                <div class="gnss-edge e13"></div>
                <div class="gnss-edge e14"></div>
                <div class="gnss-edge e23"></div>
                <div class="gnss-edge e35"></div>
                <div class="gnss-edge e45"></div>
              </template>
            </div>
          </div>

          <div class="card-info">
            <h3>{{ c.name }}</h3>
            <span class="card-tag">{{ caseTags[c.id] }}</span>
          </div>

          <div class="card-arrow">→</div>
        </div>
      </div>
    </section>

    <!-- ====== Forkable Developer Section ====== -->
    <section class="fork-section">
      <div class="fork-bg-dots">
        <span class="dot-item" v-for="n in 20" :key="n"
          :style="{ left: (n*47)%100 + '%', top: (n*31)%100 + '%', animationDelay: (n*0.15)+'s' }"
        ></span>
      </div>

      <div class="fork-header">
        <div class="fork-icon-badge">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v1a2 2 0 01-2 2H8a2 2 0 01-2-2V9"/><path d="M12 12v3"/></svg>
        </div>
        <h2 class="fork-title">可分叉架构</h2>
        <p class="fork-subtitle">Fork 仓库，新建一个 Python 文件，实现 5 个方法，你的自定义平差案例即刻上线</p>
      </div>

      <!-- Flow Pipeline -->
      <div class="fork-flow">
        <div class="flow-step">
          <div class="flow-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5.52 19c.64-2.2 1.84-3 3.22-3h6.52c1.38 0 2.58.8 3.22 3"/><circle cx="12" cy="10" r="3"/><circle cx="12" cy="12" r="9"/><path d="M12 1v3M12 20v3M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M1 12h3M20 12h3M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"/></svg></div>
          <span class="flow-label">git clone</span>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
          <div class="flow-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 13.87A4 4 0 017 6a4 4 0 015 3.87M6 13.87A3.99 3.99 0 019 18M6 13.87a3.99 3.99 0 003 4.13M15 13.87A4 4 0 0017 6a4 4 0 00-5 3.87M15 13.87A3.99 3.99 0 0113 18a3.99 3.99 0 01-3-4.13M15 13.87a3.99 3.99 0 01-3 4.13"/></svg></div>
          <span class="flow-label">新建 Pipeline</span>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
          <div class="flow-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg></div>
          <span class="flow-label">注册上线</span>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
          <div class="flow-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg></div>
          <span class="flow-label">前端自动适配</span>
        </div>
      </div>

      <!-- 5 Interface Cards -->
      <div class="fork-grid">
        <div class="fork-card" v-for="(item, idx) in forkItems" :key="idx">
          <div class="fork-card-glow"></div>
          <div class="fork-num-ring">
            <span class="fork-num">{{ idx + 1 }}</span>
          </div>
          <div class="fork-info">
            <code class="fork-method">{{ item.method }}</code>
            <p class="fork-desc">{{ item.desc }}</p>
          </div>
        </div>
      </div>

      <!-- Code Block -->
      <div class="fork-code-block">
        <div class="fork-code-header">
          <span class="fork-code-dot dot-red"></span>
          <span class="fork-code-dot dot-yellow"></span>
          <span class="fork-code-dot dot-green"></span>
          <span class="fork-code-label">my_pipeline.py</span>
        </div>
        <pre class="fork-code"><code><span class="line-num"> 1</span>  <span class="kw">class</span> <span class="cls">MyPipeline</span>(<span class="cls">Pipeline</span>):
<span class="line-num"> 2</span>      case_id = <span class="str">"my_case"</span>
<span class="line-num"> 3</span>      case_name = <span class="str">"我的自定义案例"</span>
<span class="line-num"> 4</span>      description = <span class="str">"描述你的平差场景"</span>
<span class="line-num"> 5</span>
<span class="line-num"> 6</span>      <span class="kw">def</span> <span class="fn">config_schema</span>(<span class="kw">self</span>):
<span class="line-num"> 7</span>          <span class="kw">return</span> {<span class="str">"type"</span>: <span class="str">"object"</span>, <span class="str">"properties"</span>: {...}}
<span class="line-num"> 8</span>
<span class="line-num"> 9</span>      <span class="kw">def</span> <span class="fn">run</span>(<span class="kw">self</span>, data_source, params, progress):
<span class="line-num">10</span>          classic = <span class="kw">self</span>.<span class="fn">_run_classic</span>(data_source, params)
<span class="line-num">11</span>          ml = <span class="kw">self</span>.<span class="fn">_run_ml</span>(data_source, params)
<span class="line-num">12</span>          <span class="kw">return</span> <span class="cls">PipelineResult</span>(classic, ml)</code></pre>
      </div>

      <div class="fork-cta-row">
        <a class="fork-cta-btn" href="https://github.com/PatrickLee726/geomind" target="_blank">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
          Fork on GitHub
        </a>
        <a class="fork-cta-btn secondary" href="https://github.com/PatrickLee726/geomind/blob/master/CONTRIBUTING.md" target="_blank">
          贡献指南 →
        </a>
      </div>
    </section>

    <!-- ====== Footer ====== -->
    <footer class="site-footer">
      <div class="footer-left">
        <span class="footer-brand">测智云 GeoMind</span>
        <span class="footer-version">v0.1.0</span>
      </div>
      <div class="footer-right">
        <a href="https://github.com/PatrickLee726/geomind/blob/master/LICENSE" target="_blank">MIT License</a>
        <span class="footer-divider">·</span>
        <a href="https://github.com/PatrickLee726/geomind" target="_blank">GitHub</a>
        <span class="footer-divider">·</span>
        <a href="https://github.com/PatrickLee726/geomind/blob/master/CONTRIBUTING.md" target="_blank">贡献指南</a>
      </div>
    </footer>

    <!-- Loading / Error -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"><div class="spinner-dot"></div></div>
      <p>加载案例列表...</p>
    </div>

    <div v-if="errorMsg" class="error-box">
      <p><strong>后端连接失败</strong></p>
      <p>{{ errorMsg }}</p>
      <p style="font-size:12px; margin-top:6px;">
        请确认后端已启动: <code>cd backend && py -m uvicorn app.main:app --port 8000</code>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'

const router = useRouter()
const cases = ref([])
const loading = ref(true)
const errorMsg = ref('')

const caseTags = {
  troposphere: '天顶延迟预测',
  ionosphere: '全球 VTEC 建模',
  elevation: '高程异常拟合',
  gnss: '基线网平差',
}

const forkItems = [
  { method: 'case_id', desc: '案例唯一标识，注册后自动出现在前端列表中' },
  { method: 'case_name', desc: '案例名称，显示在卡片标题中' },
  { method: 'description', desc: '案例简介，向用户说明你的平差场景' },
  { method: 'config_schema()', desc: '返回 JSON Schema，前端自动渲染参数配置表单' },
  { method: 'run(data_source, params, progress)', desc: '编写经典 / ML 双路线逻辑，返回统一 PipelineResult' },
]

onMounted(async () => {
  try {
    const res = await api.getCases()
    cases.value = res.data.cases || []
    if (cases.value.length === 0) {
      errorMsg.value = '后端返回了空案例列表，可能后端未注册任何案例。'
    }
  } catch (e) {
    errorMsg.value = e.message || '请求失败，请检查后端服务是否已启动。'
    console.error('加载案例失败:', e)
  } finally {
    loading.value = false
  }
})

function goCase(id) {
  router.push(`/case/${id}`)
}

function scrollToCases() {
  const el = document.getElementById('cases-anchor')
  if (el) el.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
/* ========== Hero ========== */
.hero-full {
  position: relative;
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 20px;
  margin-bottom: 48px;
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 40%, #3b82f6 100%);
  animation: fadeInUp 0.6s ease-out;
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 60px 24px;
  max-width: 640px;
}

.hero-badge {
  display: inline-block;
  padding: 5px 18px;
  border-radius: 20px;
  background: rgba(255,255,255,0.1);
  color: #a3bffa;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 1px;
  margin-bottom: 20px;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.08);
}

.hero-title {
  margin-bottom: 16px;
}
.title-main {
  display: block;
  font-size: 48px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -1px;
  line-height: 1.15;
  text-shadow: 0 2px 20px rgba(0,0,0,0.25);
}
.title-sub {
  display: block;
  font-size: 18px;
  font-weight: 400;
  color: #a3bffa;
  margin-top: 8px;
}

.hero-desc {
  font-size: 15px;
  color: rgba(255,255,255,0.7);
  line-height: 1.8;
  margin-bottom: 32px;
}

.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 36px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #4299e1, #3182ce);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(66,153,225,0.35);
  transition: all 0.3s ease;
}
.hero-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(66,153,225,0.45);
}
.cta-arrow {
  transition: transform 0.3s ease;
}
.hero-cta:hover .cta-arrow {
  transform: translateY(3px);
}

/* ========== Hero Decoration ========== */
.hero-decoration {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}
.orbit-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 50%;
  transform: translate(-50%, -50%);
}
.ring-1 { width: 280px; height: 280px; }
.ring-2 { width: 380px; height: 380px; border-color: rgba(255,255,255,0.04); }
.ring-3 { width: 480px; height: 480px; border-color: rgba(255,255,255,0.03); }

.earth {
  position: absolute;
  bottom: -60px;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #2c5282, #1a365d 60%, #0f1b3a);
  opacity: 0.35;
  box-shadow: inset -20px -20px 40px rgba(0,0,0,0.3), 0 0 60px rgba(49,130,206,0.15);
}

.satellite {
  position: absolute;
  font-size: 22px;
  opacity: 0.7;
  animation: float 6s ease-in-out infinite;
}
.sat-1 { top: 18%; left: 18%; animation-delay: 0s; }
.sat-2 { top: 12%; right: 22%; animation-delay: 2s; }
.sat-3 { bottom: 28%; right: 14%; animation-delay: 4s; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

/* ========== Cases Section ========== */
.cases-section {
  padding: 0 8px 40px;
  animation: fadeInUp 0.5s 0.2s ease-out both;
}
.section-title {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: #1a365d;
  margin-bottom: 6px;
}
.section-subtitle {
  text-align: center;
  font-size: 14px;
  color: #718096;
  margin-bottom: 32px;
}

.case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
}

.case-card {
  position: relative;
  background: white;
  border-radius: 20px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
  border: 1px solid #e8ecf1;
  animation: fadeInUp 0.5s ease-out both;
  transition: transform 0.35s cubic-bezier(0.34,1.56,0.64,1),
              box-shadow 0.35s ease;
}
.case-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 40px rgba(49,130,206,0.15);
  border-color: #c3dafe;
}
.case-card:hover .card-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* ========== Diagram Area ========== */
.card-diagram {
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.diagram-inner {
  position: relative;
  width: 160px;
  height: 140px;
}

/* ---- Troposphere ---- */
.diagram-troposphere { background: linear-gradient(180deg, #7dd3fc 0%, #bae6fd 35%, #dbeafe 70%, #93c5fd 100%); }

.trop-sat1 {
  position: absolute;
  top: 6px;
  left: 32px;
  font-size: 16px;
  z-index: 5;
  animation: float 4.5s ease-in-out infinite;
}
.trop-sat2 {
  position: absolute;
  top: 10px;
  right: 36px;
  font-size: 14px;
  z-index: 5;
  animation: float 5s ease-in-out infinite;
  animation-delay: 1.5s;
}

.trop-ray1 {
  position: absolute;
  top: 22px;
  left: 40px;
  width: 2px;
  height: 68px;
  background: linear-gradient(to bottom, rgba(255,255,255,0.7), rgba(14,165,233,0.5), transparent);
  transform: rotate(7deg);
  border-radius: 1px;
  z-index: 4;
}
.trop-ray2 {
  position: absolute;
  top: 24px;
  right: 44px;
  width: 2px;
  height: 62px;
  background: linear-gradient(to bottom, rgba(255,255,255,0.6), rgba(14,165,233,0.4), transparent);
  transform: rotate(-6deg);
  border-radius: 1px;
  z-index: 4;
}

.trop-troposphere {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 130px;
  height: 88px;
  border-radius: 65px 65px 0 0;
  background: linear-gradient(180deg, rgba(148,163,184,0.18) 0%, rgba(100,116,139,0.32) 100%);
  z-index: 2;
}

.trop-earth2 {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: linear-gradient(135deg, #22c55e, #15803d);
  box-shadow: 0 4px 16px rgba(21,128,61,0.25), inset -6px -6px 12px rgba(0,0,0,0.15);
  z-index: 1;
}

.trop-antenna {
  position: absolute;
  bottom: 55px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 4;
}
.trop-antenna::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-bottom: 16px solid #374151;
}
.trop-antenna::after {
  content: '';
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  width: 12px;
  height: 4px;
  background: #4b5563;
  border-radius: 2px;
}

.trop-ztd-label {
  position: absolute;
  bottom: 8px;
  right: 14px;
  font-size: 10px;
  font-weight: 700;
  color: #0369a1;
  letter-spacing: 1px;
  opacity: 0.85;
}

.trop-cloud {
  position: absolute;
  background: rgba(255,255,255,0.55);
  border-radius: 20px;
  z-index: 3;
}
.trop-cloud.c1 {
  width: 32px;
  height: 13px;
  top: 52px;
  left: 26px;
}
.trop-cloud.c1::before {
  content: '';
  position: absolute;
  top: -7px;
  left: 5px;
  width: 18px;
  height: 18px;
  background: rgba(255,255,255,0.55);
  border-radius: 50%;
}
.trop-cloud.c2 {
  width: 26px;
  height: 11px;
  top: 46px;
  right: 30px;
}
.trop-cloud.c2::before {
  content: '';
  position: absolute;
  top: -6px;
  right: 4px;
  width: 16px;
  height: 16px;
  background: rgba(255,255,255,0.55);
  border-radius: 50%;
}

/* ---- Ionosphere ---- */
.diagram-ionosphere { background: linear-gradient(180deg, #0f172a 0%, #1e293b 40%, #fef3c7 100%); }

.iono-sat {
  position: absolute;
  top: 6px;
  left: 62px;
  font-size: 18px;
  z-index: 5;
  animation: float 4s ease-in-out infinite;
}

.iono-beam {
  position: absolute;
  top: 22px;
  left: 69px;
  width: 2px;
  height: 68px;
  background: linear-gradient(to bottom, rgba(255,255,255,0.5), rgba(251,191,36,0.6), rgba(255,255,255,0.1));
  border-radius: 1px;
  transform: rotate(8deg);
  z-index: 4;
}

.iono-shell-outer {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 108px;
  height: 108px;
  border-radius: 50%;
  border: 2px dashed rgba(251,191,36,0.25);
  z-index: 2;
}

.iono-shell-inner {
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  width: 96px;
  height: 96px;
  border-radius: 50%;
  border: 1px solid rgba(251,191,36,0.15);
  z-index: 2;
}

.iono-band {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  height: 6px;
  border-radius: 3px;
  opacity: 0.7;
  z-index: 3;
}
.iono-band.b1 {
  bottom: 52px;
  width: 80px;
  background: linear-gradient(90deg, transparent, #fbbf24, transparent);
}
.iono-band.b2 {
  bottom: 64px;
  width: 60px;
  background: linear-gradient(90deg, transparent, #f59e0b, transparent);
}
.iono-band.b3 {
  bottom: 76px;
  width: 36px;
  background: linear-gradient(90deg, transparent, #ef4444, transparent);
}

.iono-globe2 {
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e40af, #1e3a8a);
  box-shadow: 0 4px 16px rgba(30,58,138,0.4), inset -8px -8px 16px rgba(0,0,0,0.2);
  z-index: 1;
}

.iono-station2 {
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  width: 10px;
  height: 10px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(255,255,255,0.8);
  z-index: 4;
}

.iono-tec-label {
  position: absolute;
  bottom: 8px;
  right: 14px;
  font-size: 10px;
  font-weight: 700;
  color: #d97706;
  letter-spacing: 1px;
  opacity: 0.8;
}

/* ---- Elevation ---- */
.diagram-elevation { background: linear-gradient(180deg, #ecfdf5 0%, #d1fae5 100%); }
.elev-mountain {
  position: absolute;
  bottom: 20px;
  width: 0;
  height: 0;
  border-style: solid;
}
.elev-mountain.m1 {
  left: 25px;
  border-width: 0 25px 55px 25px;
  border-color: transparent transparent #10b981 transparent;
}
.elev-mountain.m2 {
  left: 55px;
  border-width: 0 35px 75px 35px;
  border-color: transparent transparent #059669 transparent;
}
.elev-mountain.m3 {
  left: 95px;
  border-width: 0 22px 45px 22px;
  border-color: transparent transparent #34d399 transparent;
}
.elev-point {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #fff;
  border: 2px solid #dc2626;
  border-radius: 50%;
  z-index: 2;
}
.elev-point.p1 { bottom: 75px; left: 48px; }
.elev-point.p2 { bottom: 95px; left: 88px; }
.elev-point.p3 { bottom: 65px; left: 115px; }
.elev-base {
  position: absolute;
  bottom: 18px;
  left: 20px;
  right: 20px;
  height: 3px;
  background: #065f46;
  border-radius: 2px;
}

/* ---- GNSS ---- */
.diagram-gnss { background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%); }
.gnss-node {
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #7c3aed;
  box-shadow: 0 2px 8px rgba(124,58,237,0.35);
  z-index: 2;
  transition: transform 0.3s ease;
}
.case-card:hover .gnss-node { transform: scale(1.15); }
.gnss-node.n1 { top: 30px; left: 30px; }
.gnss-node.n2 { top: 20px; left: 90px; }
.gnss-node.n3 { top: 70px; left: 50px; }
.gnss-node.n4 { top: 65px; left: 110px; }
.gnss-node.n5 { top: 100px; left: 80px; background: #a78bfa; }
.gnss-edge {
  position: absolute;
  height: 2px;
  background: linear-gradient(90deg, rgba(124,58,237,0.3), rgba(124,58,237,0.15));
  border-radius: 1px;
  transform-origin: left center;
}
.gnss-edge.e12 { top: 32px; left: 40px; width: 50px; transform: rotate(-8deg); }
.gnss-edge.e13 { top: 50px; left: 38px; width: 28px; transform: rotate(55deg); }
.gnss-edge.e14 { top: 52px; left: 40px; width: 72px; transform: rotate(22deg); }
.gnss-edge.e23 { top: 48px; left: 56px; width: 42px; transform: rotate(120deg); }
.gnss-edge.e35 { top: 82px; left: 58px; width: 32px; transform: rotate(40deg); }
.gnss-edge.e45 { top: 86px; left: 90px; width: 30px; transform: rotate(-45deg); }

/* ========== Card Info ========== */
.card-info {
  padding: 20px 24px 24px;
  text-align: center;
}
.card-info h3 {
  font-size: 17px;
  font-weight: 700;
  color: #1a365d;
  margin-bottom: 6px;
}
.card-tag {
  font-size: 13px;
  color: #718096;
  font-weight: 500;
}
.card-arrow {
  position: absolute;
  bottom: 24px;
  right: 24px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3182ce, #2c5282);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  opacity: 0;
  transform: translateX(-8px);
  transition: all 0.3s ease;
}

/* ========== Loading / Error ========== */
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #718096;
}
.loading-state p {
  margin-top: 16px;
  font-size: 14px;
  animation: statusBlink 1.5s ease infinite;
}
.error-box {
  text-align: center;
  padding: 24px;
  margin: 20px auto;
  max-width: 500px;
  background: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 12px;
  color: #c53030;
  animation: fadeInUp 0.4s ease-out;
}
.error-box code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #2d3748;
}

/* ========== Hero GitHub Link ========== */
.hero-github {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  padding: 8px 20px;
  border-radius: 8px;
  background: rgba(255,255,255,0.1);
  color: #a3bffa;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid rgba(255,255,255,0.12);
  transition: all 0.3s ease;
}
.hero-github:hover {
  background: rgba(255,255,255,0.18);
  color: #fff;
  border-color: rgba(255,255,255,0.25);
}
.github-icon {
  width: 18px;
  height: 18px;
}

/* ========== Fork Section ========== */
.fork-section {
  position: relative;
  margin: 48px -20px 0;
  padding: 60px 40px 50px;
  background: linear-gradient(170deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  overflow: hidden;
  animation: fadeInUp 0.5s 0.4s ease-out both;
}

/* 背景粒子 */
.fork-bg-dots {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}
.fork-bg-dots .dot-item {
  position: absolute;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(99,179,237,0.3);
  animation: dotBlink 3s ease-in-out infinite;
}
@keyframes dotBlink {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.6; }
}

/* 头部 */
.fork-header {
  text-align: center;
  margin-bottom: 40px;
  position: relative;
  z-index: 1;
}
.fork-icon-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(99,179,237,0.2), rgba(99,179,237,0.05));
  border: 1px solid rgba(99,179,237,0.2);
  color: #63b3ed;
  margin-bottom: 20px;
}
.fork-title {
  font-size: 28px;
  font-weight: 800;
  color: #f1f5f9;
  margin-bottom: 10px;
  letter-spacing: -0.5px;
}
.fork-subtitle {
  font-size: 15px;
  color: #94a3b8;
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.6;
}

/* Flow Pipeline */
.fork-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
  margin-bottom: 44px;
  position: relative;
  z-index: 1;
}
.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
}
.flow-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #334155, #1e293b);
  border: 1px solid rgba(99,179,237,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #63b3ed;
  transition: all 0.3s ease;
}
.flow-step:hover .flow-icon {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border-color: #3b82f6;
  color: #fff;
  box-shadow: 0 0 24px rgba(37,99,235,0.3);
  transform: translateY(-2px);
}
.flow-label {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  white-space: nowrap;
}
.flow-arrow {
  font-size: 24px;
  color: #475569;
  font-weight: 400;
  padding: 0 4px;
  margin-bottom: 16px;
}

/* 5 Interface Cards */
.fork-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin: 0 auto 40px;
  max-width: 1000px;
  position: relative;
  z-index: 1;
}
.fork-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 24px 16px 20px;
  background: rgba(30,41,59,0.8);
  border: 1px solid rgba(71,85,105,0.3);
  border-radius: 14px;
  backdrop-filter: blur(8px);
  transition: all 0.35s cubic-bezier(0.34,1.56,0.64,1);
  overflow: hidden;
}
.fork-card:hover {
  border-color: #3b82f6;
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.3), 0 0 0 1px rgba(59,130,246,0.2);
}
.fork-card-glow {
  position: absolute;
  top: -40px;
  right: -40px;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(59,130,246,0.1), transparent 70%);
  opacity: 0;
  transition: opacity 0.5s ease;
}
.fork-card:hover .fork-card-glow {
  opacity: 1;
}
.fork-num-ring {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(37,99,235,0.2), rgba(37,99,235,0.05));
  border: 2px solid rgba(59,130,246,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.35s ease;
}
.fork-card:hover .fork-num-ring {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border-color: #3b82f6;
  box-shadow: 0 0 20px rgba(37,99,235,0.4);
}
.fork-num {
  font-size: 16px;
  font-weight: 800;
  color: #63b3ed;
  transition: color 0.35s ease;
}
.fork-card:hover .fork-num {
  color: #fff;
}
.fork-info {
  min-width: 0;
}
.fork-method {
  display: inline-block;
  font-size: 13px;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 6px;
  padding: 3px 10px;
  background: rgba(37,99,235,0.15);
  border-radius: 5px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  letter-spacing: -0.3px;
}
.fork-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0;
}

/* Code Block */
.fork-code-block {
  max-width: 580px;
  margin: 0 auto;
  background: #0b1120;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(71,85,105,0.4), 0 8px 40px rgba(0,0,0,0.5);
  position: relative;
  z-index: 1;
}
.fork-code-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  background: #1a2236;
  border-bottom: 1px solid rgba(71,85,105,0.3);
}
.fork-code-dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
}
.dot-red { background: #ef4444; }
.dot-yellow { background: #f59e0b; }
.dot-green { background: #22c55e; }
.fork-code-label {
  margin-left: 10px;
  font-size: 12px;
  color: #64748b;
  font-weight: 400;
}
.fork-code {
  padding: 22px 24px;
  margin: 0;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.85;
  color: #e2e8f0;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  background: transparent;
}
.fork-code code {
  background: transparent;
}
.fork-code .line-num {
  color: #334155;
  user-select: none;
  margin-right: 12px;
}
.fork-code .kw { color: #c084fc; }
.fork-code .cls { color: #67e8f9; }
.fork-code .str { color: #86efac; }
.fork-code .fn { color: #fde68a; }

/* CTA Buttons */
.fork-cta-row {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
  position: relative;
  z-index: 1;
}
.fork-cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(37,99,235,0.3);
}
.fork-cta-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(37,99,235,0.45);
}
.fork-cta-btn.secondary {
  background: transparent;
  color: #94a3b8;
  border: 1px solid rgba(71,85,105,0.4);
  box-shadow: none;
}
.fork-cta-btn.secondary:hover {
  border-color: #3b82f6;
  color: #fff;
  box-shadow: none;
}

/* ========== Footer ========== */
.site-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 24px 16px;
  margin-top: 40px;
  border-top: 1px solid #e8ecf1;
}
.footer-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.footer-brand {
  font-weight: 700;
  color: #1a365d;
  font-size: 14px;
}
.footer-version {
  font-size: 12px;
  color: #a0aec0;
  background: #edf2f7;
  padding: 2px 8px;
  border-radius: 4px;
}
.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.footer-right a {
  font-size: 13px;
  color: #718096;
  text-decoration: none;
  transition: color 0.2s;
}
.footer-right a:hover { color: #3182ce; }
.footer-divider {
  color: #cbd5e0;
  font-size: 13px;
}
</style>
