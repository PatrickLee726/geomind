<template>
  <div class="case-page">
    <div class="back-link">
      <router-link to="/">← 返回首页</router-link>
    </div>

    <div v-if="loading" class="loading">加载案例信息...</div>

    <template v-if="!loading">
      <h1>{{ caseInfo.name }}</h1>
      <p class="desc">{{ caseInfo.description }}</p>

      <!-- 数据源（仅非模拟案例） -->
      <section class="section" v-if="!isSimulation">
        <h2>1. 选择数据源</h2>

        <!-- 对流层 -->
        <template v-if="caseId === 'troposphere'">
        <div class="source-tabs">
          <button :class="{ active: sourceType === 'igs' }" @click="sourceType = 'igs'">
            IGS CDDIS 数据
          </button>
          <button :class="{ active: sourceType === 'upload' }" @click="sourceType = 'upload'">
            上传文件
          </button>
        </div>

        <div v-if="sourceType === 'igs'" class="source-config">
          <label>
            站点（可多选）：
            <div class="checkbox-group">
              <label v-for="st in igsStations" :key="st.name" class="checkbox-item">
                <input type="checkbox" :value="st.name" v-model="selectedStations" />
                {{ st.name }} ({{ st.lat.toFixed(1) }}°N, {{ st.H }}m)
              </label>
            </div>
          </label>
          <label class="field">
            DOY（逗号分隔）：
            <input v-model="daysInput" placeholder="1,46,91,136,181,226,271,316,361" />
          </label>
          <button class="btn" @click="loadIGSData">加载数据</button>
          <div v-if="dataProfile" class="data-info">
            已加载 {{ dataProfile.n_samples }} 条记录
          </div>
        </div>

        <div v-if="sourceType === 'upload'" class="source-config">
          <label class="field">
            TRO 文件：
            <input type="file" multiple @change="onTroFiles" accept=".TRO,.TRO.gz,.tro,.gz" />
          </label>
          <label class="field">
            气象文件（可选 .25m）：
            <input type="file" multiple @change="onMetFiles" accept=".25m,.25m.gz" />
          </label>
          <button class="btn" @click="uploadFiles" :disabled="!troFiles.length">上传</button>
          <div v-if="dataProfile" class="data-info">
            已加载 {{ dataProfile.n_samples }} 条记录
          </div>
        </div>
        </template>

        <!-- 高程异常 -->
        <template v-if="caseId === 'elevation'">
          <div class="source-tabs">
            <button :class="{ active: elevSource === 'sim' }" @click="elevSource = 'sim'">
              模拟数据
            </button>
            <button :class="{ active: elevSource === 'csv' }" @click="elevSource = 'csv'">
              上传CSV
            </button>
          </div>

          <div v-if="elevSource === 'sim'" class="source-config">
            <p class="hint">使用内置模拟数据。在下方参数配置中选择场景（A/B/C）和噪声水平。</p>
          </div>

          <div v-if="elevSource === 'csv'" class="source-config">
            <label class="field">
              CSV文件（至少含X, Y, Z三列）：
              <input type="file" @change="onCSVFile" accept=".csv" />
            </label>
            <button class="btn primary" @click="uploadCSV" :disabled="!csvFile || csvUploading">
              {{ csvUploading ? '上传中...' : '上传并解析' }}
            </button>
            <div v-if="dataProfile" class="data-info">
              ✓ {{ dataProfile.n_samples }} 个点，特征: {{ dataProfile.feature_names?.join(', ') }}，ζ 范围: {{ dataProfile.elevation_range?.toFixed(3) }}m
            </div>
            <div v-if="csvError" class="data-error">{{ csvError }}</div>
          </div>
        </template>

        <!-- GNSS基线网 -->
        <template v-if="caseId === 'gnss'">
          <div class="source-tabs">
            <button :class="{ active: gnssSource === 'sim' }" @click="gnssSource = 'sim'">
              模拟网形
            </button>
            <button :class="{ active: gnssSource === 'upload' }" @click="gnssSource = 'upload'">
              上传基线CSV
            </button>
          </div>

          <div v-if="gnssSource === 'sim'" class="source-config">
            <p class="hint">蒙特卡洛随机生成GNSS网形。在下方参数配置中调整测站数、基线数和粗差比例。</p>
          </div>

          <div v-if="gnssSource === 'upload'" class="source-config">
            <label class="field">
              CSV文件（列: from/to/dx/dy/dz，可选std）：
              <input type="file" @change="onGNSSFile" accept=".csv" />
            </label>
            <p class="hint form-help">
              格式示例：<br/>
              <code>from,to,dx,dy,dz,std</code><br/>
              第一条基线的 from 站自动作为已知点。
            </p>
            <button class="btn primary" @click="uploadGNSSFile" :disabled="!gnssFile || gnssUploading">
              {{ gnssUploading ? '上传中...' : '上传并解析' }}
            </button>
            <div v-if="dataProfile" class="data-info">
              ✓ {{ dataProfile.n_samples }} 条基线，{{ dataProfile.feature_dim }} 个站点
            </div>
            <div v-if="gnssError" class="data-error">{{ gnssError }}</div>
          </div>
        </template>

        <!-- 电离层 -->
        <template v-if="caseId === 'ionosphere'">
          <div class="source-tabs">
            <button :class="{ active: ionoSource === 'default' }" @click="ionoSource = 'default'">
              默认数据
            </button>
            <button :class="{ active: ionoSource === 'upload' }" @click="ionoSource = 'upload'">
              上传IONEX
            </button>
          </div>

          <div v-if="ionoSource === 'default'" class="source-config">
            <p class="hint">使用服务器上预置的 COD 全球电离层地图数据（5天）。在下方参数配置中调整日期和采样。</p>
          </div>

          <div v-if="ionoSource === 'upload'" class="source-config">
            <label class="field">
              IONEX文件（.INX.gz，可多选）：
              <input type="file" multiple @change="onIonexFiles" accept=".INX,.INX.gz,.gz" />
            </label>
            <p class="hint form-help">可从 <a href="https://cddis.nasa.gov/archive/gnss/products/ionex/" target="_blank">CDDIS IONEX</a> 下载最新数据。</p>
            <button class="btn primary" @click="uploadIonexFiles" :disabled="!ionexFiles.length || ionexUploading">
              {{ ionexUploading ? '上传中...' : '上传并解析' }}
            </button>
            <div v-if="dataProfile" class="data-info">
              ✓ {{ dataProfile.n_samples }} 个文件已上传
            </div>
            <div v-if="ionexError" class="data-error">{{ ionexError }}</div>
          </div>
        </template>
      </section>

      <!-- 参数配置（动态渲染） -->
      <section class="section">
        <h2>{{ isSimulation ? '1' : '2' }}. 配置参数</h2>
        <button class="btn-demo" @click="fillDemoConfig" title="一键填充推荐参数">
          ⚡ 使用示例数据
        </button>
        <button class="btn-sweep" @click="startSweep" :disabled="sweepRunning" title="自动搜索最优超参数">
          {{ sweepRunning ? '🔍 搜索中...' : '🔍 智能寻优' }}
        </button>
        <div v-if="sweepResult" class="sweep-result">
          <div class="sweep-best">
            🏆 最优参数：{{ sweepBestParams }}
            <span class="sweep-rmse">ML RMSE: {{ sweepBestRmse }}</span>
          </div>
          <button class="btn-apply" @click="applySweepResult">应用最优参数</button>
        </div>
        <div class="config-grid">
          <label v-for="(prop, key) in schemaProps" :key="key" class="field" :title="prop.description || ''">
            {{ prop.title || key }}：
            <template v-if="prop.type === 'integer' || prop.type === 'number'">
              <input
                v-if="prop.minimum !== undefined && prop.maximum !== undefined && prop.maximum - prop.minimum <= 1"
                type="range"
                v-model.number="config[key]"
                :min="prop.minimum"
                :max="prop.maximum"
                :step="prop.type === 'integer' ? 1 : (prop.maximum - prop.minimum) / 20"
              />
              <input
                v-else
                :type="prop.default !== undefined && prop.default > 10 ? 'number' : 'range'"
                v-model.number="config[key]"
                :min="prop.minimum"
                :max="prop.maximum"
                :step="prop.type === 'integer' ? 1 : 0.01"
              />
              <span v-if="prop.default !== undefined && prop.default > 10" class="value-tag">{{ config[key] }}</span>
            </template>
            <template v-else-if="prop.enum">
              <select v-model="config[key]">
                <option v-for="opt in prop.enum" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </template>
            <template v-else-if="prop.type === 'string'">
              <input type="text" v-model="config[key]" />
            </template>
          </label>
        </div>
      </section>

      <!-- 执行 -->
      <section class="section">
        <h2>{{ isSimulation ? '2' : '3' }}. 开始计算</h2>
        <button class="btn primary" @click="submitJob" :disabled="!canSubmit || running">
          {{ running ? '计算中...' : '开始计算' }}
        </button>
        <div v-if="jobStatus" class="job-status">
          <span class="status-badge" :class="jobStatus.status">{{ statusLabel[jobStatus.status] }}</span>
          <span>{{ jobStatus.message }}</span>
        </div>
        <div v-if="jobStatus?.job_id && jobStatus?.status !== 'done'" class="back-link-inline">
          <router-link to="/">← 返回首页（任务将继续在后台运行）</router-link>
        </div>
        <div v-if="jobStatus?.status === 'done'" class="done-actions">
          <router-link :to="`/result/${jobStatus.job_id}`" class="btn primary">
            查看结果 →
          </router-link>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api.js'

const route = useRoute()
const caseId = route.params.id

const caseInfo = ref({})
const loading = ref(true)

// 是否为纯模拟案例（无需数据源）
const isSimulation = computed(() => [].includes(caseId))

// 从 schema 提取属性定义
const schemaProps = ref({})

// 数据源
const sourceType = ref('igs')
const igsStations = ref([])
const selectedStations = ref(['BJFS', 'SHAO', 'CHAN', 'WUHN', 'TWTF'])
const daysInput = ref('1, 91, 181, 271, 361')
const troFiles = ref([])
const metFiles = ref([])
const dataProfile = ref(null)
const dsConfig = ref({})

// 高程异常专用
const elevSource = ref('sim')
const csvFile = ref(null)
const csvUploading = ref(false)
const csvError = ref('')

// GNSS基线网专用
const gnssSource = ref('sim')
const gnssFile = ref(null)
const gnssUploading = ref(false)
const gnssError = ref('')

// 电离层专用
const ionoSource = ref('default')
const ionexFiles = ref([])
const ionexUploading = ref(false)
const ionexError = ref('')

// 配置（动态初始化）
const config = ref({})

// 任务
const running = ref(false)
const jobStatus = ref(null)
const statusLabel = { pending: '等待中', running: '运行中', done: '已完成', failed: '失败' }

const canSubmit = computed(() => {
  if (caseId === 'elevation' && elevSource.value === 'sim') return true
  if (caseId === 'gnss' && gnssSource.value === 'sim') return true
  if (caseId === 'ionosphere' && ionoSource.value === 'default') return true
  return !!dataProfile.value
})

const demoConfigs = {
  troposphere: { hidden_layers: '128,256,128,64', epochs: 3000, learning_rate: 0.001, dropout: 0.2, batch_size: 64, split_mode: 'random' },
  ionosphere: { hidden_layers: '256,512,256,128', epochs: 300, learning_rate: 0.001, dropout: 0.2, batch_size: 128 },
  gnss: { n_stations: 8, n_groups: 100, outlier_rate: 0.15, noise_std: 2.0, hidden_layers: '64,64', epochs: 200, learning_rate: 0.001 },
  elevation: { scenario: 'B', noise: 0.05, test_ratio: 0.2, hidden_layers: '64,128,64', epochs: 500, learning_rate: 0.001, dropout: 0.2 },
}

function fillDemoConfig() {
  const demo = demoConfigs[caseId]
  if (!demo) return
  for (const [key, val] of Object.entries(demo)) {
    if (key in config.value) {
      config.value[key] = val
    }
  }
}

// 参数扫描
const sweepRunning = ref(false)
const sweepResult = ref(null)
const sweepBestParams = ref('')
const sweepBestRmse = ref('')

async function startSweep() {
  sweepRunning.value = true
  sweepResult.value = null
  // Build param grid from schema
  const grid = {}
  const props = schemaProps.value
  if (props.hidden_layers || props.ml_hidden_dims) {
    grid[props.hidden_layers ? 'hidden_layers' : 'ml_hidden_dims'] = ['64,64', '128,256,128', '256,512,256,128']
  }
  if (props.epochs || props.ml_epochs) {
    grid[props.epochs ? 'epochs' : 'ml_epochs'] = [100, 500, 1500]
  }
  if (props.learning_rate || props.ml_learning_rate) {
    grid[props.learning_rate ? 'learning_rate' : 'ml_learning_rate'] = [0.0005, 0.001, 0.005]
  }
  try {
    const res = await api.post('/sweep/start', { case_id: caseId, param_grid: grid, base_params: config.value })
    const sid = res.data.sweep_id
    pollSweep(sid)
  } catch (e) {
    sweepRunning.value = false
    alert('启动扫描失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function pollSweep(sid) {
  try {
    const res = await api.get(`/sweep/status/${sid}`)
    const data = res.data
    if (data.status === 'done') {
      sweepRunning.value = false
      const results = data.results
      if (results && results.length > 0) {
        const best = results[0]
        sweepResult.value = results.slice(0, 5)
        sweepBestParams.value = JSON.stringify(best.params)
        sweepBestRmse.value = best.RMSE || 'N/A'
      } else {
        alert('扫描完成但无有效结果')
      }
    } else if (data.status === 'failed') {
      sweepRunning.value = false
      alert('扫描失败: ' + (data.error || '未知错误'))
    } else {
      setTimeout(() => pollSweep(sid), 2000)
    }
  } catch (e) {
    sweepRunning.value = false
  }
}

function applySweepResult() {
  if (!sweepResult.value || !sweepResult.value.length) return
  const best = sweepResult.value[0].params
  for (const [key, val] of Object.entries(best)) {
    if (key in config.value) {
      config.value[key] = val
    }
  }
  sweepResult.value = null
}

function saveJobRef(jobId, caseId) {
  const key = 'geomind_jobs'
  const arr = JSON.parse(localStorage.getItem(key) || '[]')
  arr.unshift({ jobId, caseId, time: new Date().toLocaleString('zh-CN'), status: 'running' })
  if (arr.length > 30) arr.pop()
  localStorage.setItem(key, JSON.stringify(arr))
  // 同步更新全局任务计数
  window.dispatchEvent(new CustomEvent('geomind:job-created'))
}

onMounted(async () => {
  try {
    const [caseRes, stRes] = await Promise.all([
      api.getCase(caseId),
      isSimulation.value
        ? Promise.resolve({ data: { stations: [] } })
        : api.getIGSStations().catch(() => ({ data: { stations: [] } })),
    ])
    caseInfo.value = caseRes.data
    igsStations.value = stRes.data.stations || []

    // 从 schema 构建属性定义和默认配置
    const props = {}
    const defaults = {}
    const schema = caseRes.data.schema || {}
    const properties = schema.properties || {}
    for (const [key, prop] of Object.entries(properties)) {
      props[key] = prop
      defaults[key] = prop.default
    }
    schemaProps.value = props
    config.value = defaults
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function loadIGSData() {
  const days = daysInput.value.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
  try {
    const res = await api.fetchIGSTropo({
      stations: selectedStations.value,
      days,
    })
    dataProfile.value = res.data.profile
    dsConfig.value = { type: 'igs_troposphere', stations: selectedStations.value, days }
  } catch (e) {
    alert('加载失败: ' + (e.response?.data?.error || e.message))
  }
}

function onTroFiles(e) { troFiles.value = Array.from(e.target.files) }
function onMetFiles(e) { metFiles.value = Array.from(e.target.files) }

function onCSVFile(e) {
  csvFile.value = e.target.files[0] || null
  csvError.value = ''
  dataProfile.value = null
}

function onGNSSFile(e) {
  gnssFile.value = e.target.files[0] || null
  gnssError.value = ''
  dataProfile.value = null
}

async function uploadGNSSFile() {
  if (!gnssFile.value) return
  gnssUploading.value = true
  gnssError.value = ''
  const fd = new FormData()
  fd.append('file', gnssFile.value)
  try {
    const res = await api.uploadFile(fd)
    dataProfile.value = { n_samples: 1, feature_dim: 0 }
    dsConfig.value = {
      type: 'uploaded_csv',
      filepath: res.data.filepath,
    }
  } catch (e) {
    gnssError.value = '上传失败: ' + (e.response?.data?.error || e.message)
  } finally {
    gnssUploading.value = false
  }
}

function onIonexFiles(e) {
  ionexFiles.value = Array.from(e.target.files)
  ionexError.value = ''
  dataProfile.value = null
}

async function uploadIonexFiles() {
  if (!ionexFiles.value.length) return
  ionexUploading.value = true
  ionexError.value = ''
  try {
    const paths = []
    for (const f of ionexFiles.value) {
      const fd = new FormData()
      fd.append('file', f)
      const res = await api.uploadFile(fd)
      paths.push(res.data.filepath)
    }
    dataProfile.value = { n_samples: paths.length, feature_dim: 0 }
    dsConfig.value = {
      type: 'uploaded_ionex',
      filepaths: paths,
    }
  } catch (e) {
    ionexError.value = '上传失败: ' + (e.response?.data?.error || e.message)
  } finally {
    ionexUploading.value = false
  }
}

async function uploadCSV() {
  if (!csvFile.value) return
  csvUploading.value = true
  csvError.value = ''
  const fd = new FormData()
  fd.append('file', csvFile.value)
  try {
    const res = await api.uploadCSV(fd)
    dataProfile.value = res.data.profile
    dsConfig.value = {
      type: 'uploaded_csv',
      filepath: res.data.filepath,
    }
  } catch (e) {
    csvError.value = '上传失败: ' + (e.response?.data?.error || e.message)
  } finally {
    csvUploading.value = false
  }
}

async function uploadFiles() {
  const fd = new FormData()
  troFiles.value.forEach(f => fd.append('tro_files', f))
  metFiles.value.forEach(f => fd.append('met_files', f))
  try {
    const res = await api.uploadTroposphere(fd)
    dataProfile.value = res.data.profile
    dsConfig.value = { type: 'uploaded_troposphere', session_id: res.data.session_id }
  } catch (e) {
    alert('上传失败: ' + (e.response?.data?.error || e.message))
  }
}

async function submitJob() {
  running.value = true
  jobStatus.value = { status: 'pending', message: '正在提交...' }
  try {
    const payload = {
      case_id: caseId,
      config: { ...config.value },
    }
    // 模拟案例无需 data_source；高程异常/GNSS取决于数据源选择
    if (!isSimulation.value) {
      if ((caseId === 'elevation' && elevSource.value === 'sim') ||
          (caseId === 'gnss' && gnssSource.value === 'sim') ||
          (caseId === 'ionosphere' && ionoSource.value === 'default')) {
        // 使用默认数据，不传 data_source
      } else if (dsConfig.value && dsConfig.value.type) {
        payload.data_source = dsConfig.value
      }
    }
    const res = await api.submitJob(payload)
    const jobId = res.data.job_id
    jobStatus.value = { job_id: jobId, status: 'pending', message: '已提交' }
    // 记录到全局任务列表
    saveJobRef(jobId, caseId)
    pollJob(jobId)
  } catch (e) {
    jobStatus.value = { status: 'failed', message: '提交失败: ' + (e.response?.data?.error || e.message) }
    running.value = false
  }
}

async function pollJob(jobId) {
  const check = async () => {
    try {
      const res = await api.getJob(jobId)
      jobStatus.value = { job_id: jobId, ...res.data }
      if (res.data.status === 'done' || res.data.status === 'failed') {
        running.value = false
        return
      }
    } catch (_) {
      // 继续轮询
    }
    setTimeout(check, 2000)
  }
  check()
}
</script>

<style scoped>
.case-page { max-width: 800px; margin: 0 auto; }
.back-link { margin-bottom: 16px; font-size: 14px; color: #3182ce; }
.back-link-inline {
  margin: 12px 0;
  font-size: 13px;
}
.back-link-inline a {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}
.back-link-inline a:hover { text-decoration: underline; }
h1 { font-size: 28px; color: #1a365d; margin-bottom: 4px; }
.desc { color: #6b7c8e; font-size: 14px; line-height: 1.6; margin-bottom: 32px; }

.section { 
  background: white; border-radius: 16px; padding: 28px; margin-bottom: 20px; 
  box-shadow: 0 1px 6px rgba(0,0,0,0.03); border: 1px solid #e8ecf1;
  animation: fadeInUp 0.5s ease-out both;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
}
.section:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); border-color: #d0d7e0; }
.section:nth-child(2) { animation-delay: 0.10s; }
.section:nth-child(3) { animation-delay: 0.20s; }
.section:nth-child(4) { animation-delay: 0.30s; }
.section h2 { font-size: 18px; color: #1a365d; margin-bottom: 16px; font-weight: 700; }

.source-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.source-tabs button { 
  padding: 9px 22px; border: 1.5px solid #d0d7de; background: #fff; border-radius: 10px; 
  cursor: pointer; font-size: 14px; color: #555; font-weight: 500;
  transition: all 0.25s ease;
}
.source-tabs button:hover { border-color: #90cdf4; color: #2b6cb0; background: #f0f8ff; }
.source-tabs button.active { 
  background: linear-gradient(135deg, #3182ce, #2c5282); color: #fff; border-color: transparent;
  box-shadow: 0 2px 8px rgba(49, 130, 206, 0.3); transform: scale(1.03);
}

.source-config { margin-top: 12px; }
.checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.checkbox-item { font-size: 13px; display: flex; align-items: center; gap: 4px; cursor: pointer; padding: 4px 10px; border-radius: 6px; transition: background 0.2s ease; }
.checkbox-item:hover { background: #f0f5ff; }

.field { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; font-size: 14px; flex-wrap: wrap; }
.field input, .field select { 
  padding: 9px 14px; border: 1.5px solid #d0d7de; border-radius: 8px; font-size: 14px;
  transition: border-color 0.25s ease, box-shadow 0.25s ease; outline: none;
}
.field input:focus, .field select:focus { border-color: #3182ce; box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.12); }
.field input[type="number"] { width: 100px; }
.field input[type="range"] { width: 150px; accent-color: #3182ce; }
.value-tag { font-size: 12px; color: #3182ce; font-weight: 600; }

.btn { 
  padding: 10px 28px; border: none; border-radius: 10px; 
  background: #e2e8f0; color: #333; font-size: 14px; font-weight: 600; 
  cursor: pointer; transition: all 0.25s ease;
}
.btn:hover:not(:disabled) { background: #cbd5e0; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.btn:active:not(:disabled) { transform: translateY(0); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn.primary { 
  background: linear-gradient(135deg, #3182ce, #2c5282, #2b6cb0);
  background-size: 200% 200%;
  animation: btnShine 3s ease infinite;
  color: #fff; 
}
.btn.primary:hover:not(:disabled) { box-shadow: 0 4px 16px rgba(49, 130, 206, 0.35); transform: translateY(-2px); }

.btn-demo {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  margin: 4px 0 16px;
  border: 2px dashed #3b82f6;
  border-radius: 8px;
  background: rgba(59,130,246,0.06);
  color: #3b82f6;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}
.btn-demo:hover {
  background: rgba(59,130,246,0.12);
  border-color: #2563eb;
  border-style: solid;
}
.btn-sweep {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  margin: 4px 0 16px 8px;
  border: 2px dashed #d97706;
  border-radius: 8px;
  background: rgba(217,119,6,0.06);
  color: #d97706;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}
.btn-sweep:hover:not(:disabled) {
  background: rgba(217,119,6,0.12);
  border-color: #b45309;
  border-style: solid;
}
.btn-sweep:disabled { opacity: 0.5; cursor: wait; }
.sweep-result {
  margin: 8px 0 16px;
  padding: 12px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  font-size: 13px;
}
.sweep-best {
  font-weight: 600;
  color: #92400e;
  margin-bottom: 8px;
}
.sweep-rmse {
  margin-left: 12px;
  color: #2563eb;
  font-family: 'JetBrains Mono', monospace;
}
.btn-apply {
  padding: 5px 14px;
  border: none;
  border-radius: 6px;
  background: #d97706;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-apply:hover { background: #b45309; }

.data-info { 
  margin-top: 12px; padding: 10px 14px; background: #f0fff4; border-radius: 8px; font-size: 13px; color: #276749;
  border-left: 3px solid #48bb78; animation: fadeInUp 0.3s ease-out;
}
.data-error { 
  margin-top: 12px; padding: 10px 14px; background: #fff5f5; border-radius: 8px; font-size: 13px; color: #c53030;
  border-left: 3px solid #f56565; animation: fadeInUp 0.3s ease-out;
}
.hint { color: #718096; font-size: 13px; line-height: 1.6; margin-bottom: 12px; }
.hint.form-help { background: #f0f5ff; padding: 10px 14px; border-radius: 8px; font-size: 12px; }
.hint.form-help code { background: #e2e8f0; padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.hint a { color: #3182ce; text-decoration: underline; }

.config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.job-status { margin-top: 16px; display: flex; align-items: center; gap: 8px; font-size: 14px; animation: fadeInUp 0.3s ease-out; }
.status-badge { padding: 3px 12px; border-radius: 14px; font-size: 12px; font-weight: 600; transition: all 0.3s ease; }
.status-badge.pending { background: #fefcbf; color: #975a16; }
.status-badge.running { background: #bee3f8; color: #2b6cb0; animation: statusBlink 1s ease infinite; }
.status-badge.done { background: #c6f6d5; color: #276749; }
.status-badge.failed { background: #fed7d7; color: #c53030; }

.done-actions { margin-top: 16px; animation: fadeInUp 0.4s ease-out; }
.loading { text-align: center; padding: 60px; color: #718096; animation: statusBlink 1.2s ease infinite; }
</style>
